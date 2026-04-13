"""
Playwright-based RPA runner for product.update_price (internal sandbox / admin-like / list_detail;
plus P4.2 real_admin_prepared: config-driven home→catalog→detail read-only readback — no production write).

Requires: pip install playwright && playwright install chromium

Targets:
- sandbox: /internal/rpa-sandbox/update-price (minimal)
- admin_like: hub → workbench /admin-like/update-price
- list_detail: hub → catalog → product-detail → save
- real_admin_prepared: external/mirror URLs from RPA_REAL_ADMIN_* + CSS selectors (read-only)
"""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlencode

from app.core.config import settings
from app.core.logging import logger
from app.rpa.schema import RpaExecutionInput, RpaExecutionOutput, RpaRunner
from app.rpa.real_admin_readonly import run_real_admin_readonly_flow
from app.rpa.target_readiness import evaluate_rpa_target_readiness, norm_rpa_target_profile

_ADMIN_FAILURE_MODES = frozenset({"none", "sku_missing", "save_error", "save_disabled"})
_LIST_DETAIL_FAILURE_MODES = frozenset(
    {"none", "sku_missing_in_list", "detail_page_not_found", "save_button_disabled", "save_error"}
)


def _screenshot(page, path: Path) -> str | None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(path), full_page=True)
        return str(path.resolve())
    except OSError as exc:
        logger.warning("RPA screenshot failed: %s", exc)
        return None


def _norm_admin_failure_mode(raw: str) -> str:
    v = (raw or "none").lower().strip()
    return v if v in _ADMIN_FAILURE_MODES else "none"


def _norm_list_detail_failure_mode(raw: str) -> str:
    v = (raw or "none").lower().strip()
    return v if v in _LIST_DETAIL_FAILURE_MODES else "none"


def _base_sandbox() -> str:
    return (settings.RPA_SANDBOX_BASE_URL or "http://127.0.0.1:8000").rstrip("/")


def _base_admin_like() -> str:
    alt = (settings.RPA_ADMIN_LIKE_BASE_URL or "").strip()
    return alt.rstrip("/") if alt else _base_sandbox()


def _base_list_detail() -> str:
    alt = (settings.RPA_LIST_DETAIL_BASE_URL or "").strip()
    return alt.rstrip("/") if alt else _base_sandbox()


def _merge_header_json(*blobs: str) -> dict[str, str]:
    merged: dict[str, str] = {}
    for blob in blobs:
        raw = (blob or "").strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("RPA: invalid JSON in headers blob, skipped")
            continue
        if isinstance(data, dict):
            for k, v in data.items():
                merged[str(k)] = str(v)
    return merged


def _playwright_context_options() -> dict:
    headers = _merge_header_json(
        settings.RPA_BROWSER_EXTRA_HTTP_HEADERS_JSON,
        settings.RPA_REAL_ADMIN_SESSION_HEADERS_JSON,
    )
    cookie = (settings.RPA_REAL_ADMIN_SESSION_COOKIE or "").strip()
    if cookie:
        headers["Cookie"] = cookie
    if not headers:
        return {}
    return {"extra_http_headers": headers}


def _inject_browser_storage(page) -> None:
    raw = (settings.RPA_BROWSER_STORAGE_INIT_JSON or "").strip()
    if not raw:
        return
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("RPA_BROWSER_STORAGE_INIT_JSON is not valid JSON")
        return
    if not isinstance(data, dict):
        return
    loc = data.get("localStorage")
    if isinstance(loc, dict):
        for key, val in loc.items():
            page.evaluate(
                "([k, v]) => { localStorage.setItem(k, v); }",
                [str(key), str(val)],
            )
    sess = data.get("sessionStorage")
    if isinstance(sess, dict):
        for key, val in sess.items():
            page.evaluate(
                "([k, v]) => { sessionStorage.setItem(k, v); }",
                [str(key), str(val)],
            )


def _enriched_pr(
    inp: RpaExecutionInput,
    *,
    sku: str,
    old_price: float,
    new_price: float,
    page_status: str,
    page_message: str,
    operation_result: str,
) -> dict:
    """Stable fields for future api_then_rpa_verify."""
    return {
        "sku": sku,
        "old_price": old_price,
        "new_price": new_price,
        "target_price": new_price,
        "page_status": page_status,
        "page_message": page_message,
        "operation_result": operation_result,
        "platform": inp.platform,
        "dry_run": inp.dry_run,
        "verify_mode": inp.verify_mode,
    }


class PlaywrightUpdatePriceRunner(RpaRunner):
    """Opens internal pages in Chromium; real screenshots; obeys RpaExecutionOutput contract."""

    rpa_backend_obs_id = "rpa_browser_real"

    def __init__(self, *, runner_name: str = "browser_real", force_failure: bool = False):
        self.runner_name = runner_name
        self.force_failure = force_failure

    def run(self, inp: RpaExecutionInput) -> RpaExecutionOutput:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return RpaExecutionOutput(
                success=False,
                result_summary="playwright package not installed",
                parsed_result={},
                evidence_paths=[],
                error_code="playwright_import_error",
                error_message="Install playwright and run: playwright install chromium",
            )

        evidence_dir = Path(inp.evidence_dir)
        paths: list[str] = []
        sku = (inp.params.get("sku") or "").strip().upper()
        target_price = inp.params.get("target_price")
        current_price = inp.params.get("current_price")

        meta_path = evidence_dir / "run_input.json"
        try:
            evidence_dir.mkdir(parents=True, exist_ok=True)
            meta_path.write_text(
                json.dumps(inp.model_dump(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            paths.append(str(meta_path.resolve()))
        except OSError as exc:
            logger.warning("RPA metadata write skipped: %s", exc)

        if not sku:
            _tiny_failure_png(evidence_dir, paths)
            return RpaExecutionOutput(
                success=False,
                result_summary="missing sku",
                parsed_result={},
                evidence_paths=paths,
                error_code="rpa_invalid_params",
                error_message="params.sku is required",
            )

        try:
            cp = float(current_price) if current_price is not None else 0.0
        except (TypeError, ValueError):
            cp = 0.0
        try:
            tp = float(target_price) if target_price is not None else 0.0
        except (TypeError, ValueError):
            tp = 0.0

        timeout_ms = max(1000, int((settings.RPA_BROWSER_TIMEOUT_S or 30) * 1000))
        target_env = (settings.RPA_TARGET_ENV or "sandbox").lower().strip()
        profile_gate = norm_rpa_target_profile(getattr(settings, "RPA_TARGET_PROFILE", None))
        verify_only = bool(inp.params.get("_list_detail_verify_only"))
        if verify_only and profile_gate != "real_admin_prepared" and target_env != "list_detail":
            return RpaExecutionOutput(
                success=False,
                result_summary="list_detail verify_only requires RPA_TARGET_ENV=list_detail",
                parsed_result={"sku": sku},
                evidence_paths=paths,
                error_code="rpa_verify_wrong_target_env",
                error_message=(
                    "api_then_rpa_verify 页面核验需 RPA_TARGET_ENV=list_detail（browser_real），"
                    "或 RPA_TARGET_PROFILE=real_admin_prepared 走真实后台只读核验"
                ),
            )

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=bool(settings.RPA_BROWSER_HEADLESS))
                try:
                    ctx_opts = _playwright_context_options()
                    context = browser.new_context(**ctx_opts)
                    page = context.new_page()
                    _inject_browser_storage(page)
                    page.set_default_timeout(timeout_ms)
                    profile = norm_rpa_target_profile(getattr(settings, "RPA_TARGET_PROFILE", None))
                    if profile == "real_admin_prepared":
                        rr = evaluate_rpa_target_readiness(settings)
                        if not rr.ready:
                            _tiny_failure_png(evidence_dir, paths)
                            return RpaExecutionOutput(
                                success=False,
                                result_summary=rr.human_error_message(),
                                parsed_result={
                                    "sku": sku,
                                    "rpa_target_profile": profile,
                                    "readiness": rr.to_dict(),
                                },
                                evidence_paths=paths,
                                error_code="rpa_target_readiness_failed",
                                error_message=rr.human_error_message(),
                            )
                        return self._flow_real_admin_prepared_readonly(
                            page,
                            evidence_dir,
                            paths,
                            inp,
                            sku,
                            tp,
                            cp,
                            rr.to_dict(),
                            timeout_ms=timeout_ms,
                        )
                    if target_env == "list_detail":
                        return self._flow_list_detail(page, evidence_dir, paths, inp, sku, tp, cp)
                    if target_env == "admin_like":
                        return self._flow_admin_like(page, evidence_dir, paths, inp, sku, tp, cp)
                    return self._flow_sandbox(
                        page, evidence_dir, paths, inp, sku, tp, cp
                    )
                finally:
                    browser.close()
        except Exception as exc:
            logger.exception("Playwright RPA runner failed")
            return RpaExecutionOutput(
                success=False,
                result_summary=str(exc),
                parsed_result={"sku": sku, "target_price": target_price},
                evidence_paths=paths,
                error_code="rpa_browser_exception",
                error_message=str(exc),
            )

    def _flow_sandbox(
        self,
        page,
        evidence_dir: Path,
        paths: list[str],
        inp: RpaExecutionInput,
        sku: str,
        tp: float,
        cp: float,
    ) -> RpaExecutionOutput:
        base = _base_sandbox()
        ff = 1 if (self.force_failure or settings.RPA_BROWSER_FORCE_FAILURE) else 0
        q = urlencode(
            {
                "sku": sku,
                "current_price": f"{cp:.4f}",
                "target_price": f"{tp:.4f}",
                "force_fail": str(ff),
            }
        )
        url = f"{base}/api/v1/internal/rpa-sandbox/update-price?{q}"
        page.goto(url, wait_until="domcontentloaded")

        p1 = _screenshot(page, evidence_dir / "01_enter_target.png")
        if p1:
            paths.append(p1)

        page.fill("#target-price", str(tp))
        p2 = _screenshot(page, evidence_dir / "02_before_action.png")
        if p2:
            paths.append(p2)

        page.click("#submit-btn")
        page.wait_for_selector("#result[data-status='success'], #result[data-status='error']")

        loc = page.locator("#result")
        status = loc.get_attribute("data-status") or ""
        text = (loc.inner_text() or "").strip()

        if status == "error":
            p3 = _screenshot(page, evidence_dir / "99_failure.png")
            if p3:
                paths.append(p3)
            return RpaExecutionOutput(
                success=False,
                result_summary=text or "sandbox reported error",
                parsed_result={
                    "sku": sku,
                    "target_price": tp,
                    "platform": inp.platform,
                    "dry_run": inp.dry_run,
                },
                evidence_paths=paths,
                error_code="rpa_browser_sandbox_error",
                error_message=text or "Browser sandbox returned error",
            )

        p3 = _screenshot(page, evidence_dir / "03_after_action.png")
        if p3:
            paths.append(p3)

        new_p = loc.get_attribute("data-new-price")
        old_p = loc.get_attribute("data-old-price")
        try:
            new_f = float(new_p) if new_p is not None else tp
        except (TypeError, ValueError):
            new_f = tp
        try:
            old_f = float(old_p) if old_p is not None else cp
        except (TypeError, ValueError):
            old_f = cp

        return RpaExecutionOutput(
            success=True,
            result_summary=f"Playwright sandbox OK: {sku} {old_f} -> {new_f}",
            parsed_result={
                "sku": sku,
                "target_price": new_f,
                "old_price": old_f,
                "platform": inp.platform,
                "dry_run": inp.dry_run,
                "verify_mode": inp.verify_mode,
            },
            evidence_paths=paths,
            error_code=None,
            error_message=None,
        )

    def _flow_admin_like(
        self,
        page,
        evidence_dir: Path,
        paths: list[str],
        inp: RpaExecutionInput,
        sku: str,
        tp: float,
        cp: float,
    ) -> RpaExecutionOutput:
        base = _base_admin_like()
        fm = _norm_admin_failure_mode(settings.RPA_ADMIN_LIKE_FORCE_FAILURE_MODE)
        q = urlencode(
            {
                "sku": sku,
                "current_price": f"{cp:.4f}",
                "target_price": f"{tp:.4f}",
                "failure_mode": fm,
            }
        )
        hub = f"{base}/api/v1/internal/rpa-sandbox/admin-like?{q}"
        page.goto(hub, wait_until="domcontentloaded")
        p1 = _screenshot(page, evidence_dir / "01_enter_backend.png")
        if p1:
            paths.append(p1)

        page.click('[data-testid="nav-to-update-price"]')
        page.wait_for_selector('[data-testid="admin-update-root"]')
        p2 = _screenshot(page, evidence_dir / "02_after_navigation.png")
        if p2:
            paths.append(p2)

        page.locator("#sku-search").fill(sku)
        page.click('[data-testid="locate-sku"]')

        if fm == "sku_missing":
            page.wait_for_selector('#global-error[data-status="error"]')
            gtxt = (page.locator("#global-error").inner_text() or "").strip()
            p99 = _screenshot(page, evidence_dir / "99_failure.png")
            if p99:
                paths.append(p99)
            return RpaExecutionOutput(
                success=False,
                result_summary=gtxt or "sku_missing",
                parsed_result={"sku": sku, "target_price": tp, "platform": inp.platform, "dry_run": inp.dry_run},
                evidence_paths=paths,
                error_code="rpa_admin_sku_missing",
                error_message=gtxt or "商品未找到（受控 sku_missing）",
            )

        page.wait_for_selector('#product-card[data-visible="1"]')
        p3 = _screenshot(page, evidence_dir / "03_product_located.png")
        if p3:
            paths.append(p3)

        page.locator("#new-price").fill(str(tp))
        p4 = _screenshot(page, evidence_dir / "04_before_save.png")
        if p4:
            paths.append(p4)

        save_btn = page.locator("#save-price")
        if fm == "save_disabled":
            p99 = _screenshot(page, evidence_dir / "99_failure.png")
            if p99:
                paths.append(p99)
            return RpaExecutionOutput(
                success=False,
                result_summary="保存按钮不可用（save_disabled）",
                parsed_result={"sku": sku, "target_price": tp, "platform": inp.platform, "dry_run": inp.dry_run},
                evidence_paths=paths,
                error_code="rpa_admin_save_disabled",
                error_message="保存按钮不可用（受控 save_disabled）",
            )

        save_btn.click()
        page.wait_for_selector("#result[data-status='success'], #result[data-status='error']")
        loc = page.locator("#result")
        status = loc.get_attribute("data-status") or ""
        text = (loc.inner_text() or "").strip()

        if status == "error":
            p99 = _screenshot(page, evidence_dir / "99_failure.png")
            if p99:
                paths.append(p99)
            return RpaExecutionOutput(
                success=False,
                result_summary=text or "save failed",
                parsed_result={"sku": sku, "target_price": tp, "platform": inp.platform, "dry_run": inp.dry_run},
                evidence_paths=paths,
                error_code="rpa_admin_save_error",
                error_message=text or "保存失败（受控 save_error）",
            )

        p5 = _screenshot(page, evidence_dir / "05_after_save.png")
        if p5:
            paths.append(p5)

        new_p = loc.get_attribute("data-new-price")
        old_p = loc.get_attribute("data-old-price")
        try:
            new_f = float(new_p) if new_p is not None else tp
        except (TypeError, ValueError):
            new_f = tp
        try:
            old_f = float(old_p) if old_p is not None else cp
        except (TypeError, ValueError):
            old_f = cp

        ok_msg = (loc.inner_text() or "").strip()
        return RpaExecutionOutput(
            success=True,
            result_summary=f"Playwright admin_like OK: {sku} {old_f} -> {new_f}",
            parsed_result=_enriched_pr(
                inp,
                sku=sku,
                old_price=old_f,
                new_price=new_f,
                page_status="success",
                page_message=ok_msg,
                operation_result="saved",
            ),
            evidence_paths=paths,
            error_code=None,
            error_message=None,
        )

    def _flow_list_detail(
        self,
        page,
        evidence_dir: Path,
        paths: list[str],
        inp: RpaExecutionInput,
        sku: str,
        tp: float,
        cp: float,
    ) -> RpaExecutionOutput:
        base = _base_list_detail()
        fm = _norm_list_detail_failure_mode(settings.RPA_LIST_DETAIL_FORCE_FAILURE_MODE)
        q = urlencode(
            {
                "sku": sku,
                "current_price": f"{cp:.4f}",
                "target_price": f"{tp:.4f}",
                "failure_mode": fm,
            }
        )
        hub = f"{base}/api/v1/internal/rpa-sandbox/admin-like?{q}"
        page.goto(hub, wait_until="domcontentloaded")
        p1 = _screenshot(page, evidence_dir / "01_enter_backend.png")
        if p1:
            paths.append(p1)

        page.click('[data-testid="nav-to-catalog"]')
        page.wait_for_selector('[data-testid="catalog-root"]')
        page.wait_for_load_state("domcontentloaded")

        page.locator("#catalog-search").fill(sku)
        page.click('[data-testid="catalog-search-btn"]')
        page.wait_for_selector(
            '#list-empty[data-visible="1"], #catalog-table-wrap[data-visible="1"]',
            timeout=max(3000, int((settings.RPA_BROWSER_TIMEOUT_S or 30) * 1000)),
        )

        if page.locator('#list-empty[data-visible="1"]').is_visible():
            etxt = (page.locator("#list-empty").inner_text() or "").strip()
            p99 = _screenshot(page, evidence_dir / "99_failure.png")
            if p99:
                paths.append(p99)
            return RpaExecutionOutput(
                success=False,
                result_summary=etxt or "list empty",
                parsed_result=_enriched_pr(
                    inp,
                    sku=sku,
                    old_price=cp,
                    new_price=tp,
                    page_status="error",
                    page_message=etxt,
                    operation_result="list_search_failed",
                ),
                evidence_paths=paths,
                error_code="rpa_list_sku_missing_in_list",
                error_message=etxt or "列表无匹配商品",
            )

        p2 = _screenshot(page, evidence_dir / "02_list_after_search.png")
        if p2:
            paths.append(p2)
        page.wait_for_timeout(250)
        p3 = _screenshot(page, evidence_dir / "03_product_row_ready.png")
        if p3:
            paths.append(p3)

        self._click_open_detail_with_retry(page)

        page.wait_for_selector(
            '[data-testid="detail-product-root"], [data-testid="detail-not-found"]',
            timeout=max(5000, int((settings.RPA_BROWSER_TIMEOUT_S or 30) * 1000)),
        )
        if page.locator('[data-testid="detail-not-found"]').is_visible():
            msg = (page.locator('[data-testid="detail-error-msg"]').inner_text() or "").strip()
            p99 = _screenshot(page, evidence_dir / "99_failure.png")
            if p99:
                paths.append(p99)
            return RpaExecutionOutput(
                success=False,
                result_summary=msg or "detail not found",
                parsed_result=_enriched_pr(
                    inp,
                    sku=sku,
                    old_price=cp,
                    new_price=tp,
                    page_status="error",
                    page_message=msg,
                    operation_result="detail_not_found",
                ),
                evidence_paths=paths,
                error_code="rpa_list_detail_page_not_found",
                error_message=msg or "详情页无法打开（受控 detail_page_not_found）",
            )

        page.wait_for_selector('[data-testid="detail-product-root"]')
        verify_only = bool(inp.params.get("_list_detail_verify_only"))
        if verify_only:
            p4r = _screenshot(page, evidence_dir / "04_detail_readback.png")
            if p4r:
                paths.append(p4r)
            sku_disp = (page.locator('[data-testid="detail-sku-display"]').inner_text() or "").strip().upper()
            cur_txt = (page.locator('[data-testid="detail-current-price"]').inner_text() or "").strip()
            try:
                page_cur = float(cur_txt)
            except (TypeError, ValueError):
                page_cur = float("nan")
            new_raw = page.locator('[data-testid="detail-new-price"]').input_value() or "0"
            try:
                page_new_field = float(new_raw)
            except (TypeError, ValueError):
                page_new_field = float("nan")
            res_el = page.locator("#detail-result")
            dstatus = res_el.get_attribute("data-status") or ""
            dpage = res_el.get_attribute("data-page-status") or ""
            msg = (res_el.inner_text() or "").strip()
            page_st = dpage or dstatus or "loaded"
            op_res = "readonly_verify"
            pr_verify = _enriched_pr(
                inp,
                sku=sku_disp or sku,
                old_price=page_cur,
                new_price=page_new_field,
                page_status=page_st,
                page_message=msg or "detail_loaded",
                operation_result=op_res,
            )
            pr_verify["page_sku"] = sku_disp or sku
            pr_verify["page_current_price"] = page_cur
            pr_verify["page_new_price_field"] = page_new_field
            return RpaExecutionOutput(
                success=True,
                result_summary=f"Playwright list_detail verify readback OK: {sku_disp or sku} page_price={page_cur}",
                parsed_result=pr_verify,
                evidence_paths=paths,
                error_code=None,
                error_message=None,
            )

        p4 = _screenshot(page, evidence_dir / "04_detail_before_save.png")
        if p4:
            paths.append(p4)

        page.locator('[data-testid="detail-new-price"]').fill(str(tp))
        save_btn = page.locator('[data-testid="detail-save-btn"]')

        if fm == "save_button_disabled":
            p99 = _screenshot(page, evidence_dir / "99_failure.png")
            if p99:
                paths.append(p99)
            return RpaExecutionOutput(
                success=False,
                result_summary="保存按钮不可用（save_button_disabled）",
                parsed_result=_enriched_pr(
                    inp,
                    sku=sku,
                    old_price=cp,
                    new_price=tp,
                    page_status="blocked",
                    page_message="save disabled",
                    operation_result="save_blocked",
                ),
                evidence_paths=paths,
                error_code="rpa_list_save_button_disabled",
                error_message="详情页保存不可用（受控 save_button_disabled）",
            )

        self._click_save_with_retry(page, save_btn)

        page.wait_for_selector(
            '#detail-result[data-status="success"], #detail-result[data-status="error"]',
            timeout=max(5000, int((settings.RPA_BROWSER_TIMEOUT_S or 30) * 1000)),
        )
        res = page.locator("#detail-result")
        status = res.get_attribute("data-status") or ""
        text = (res.inner_text() or "").strip()

        if status == "error":
            p99 = _screenshot(page, evidence_dir / "99_failure.png")
            if p99:
                paths.append(p99)
            return RpaExecutionOutput(
                success=False,
                result_summary=text or "save error",
                parsed_result=_enriched_pr(
                    inp,
                    sku=sku,
                    old_price=cp,
                    new_price=tp,
                    page_status="error",
                    page_message=text,
                    operation_result="save_failed",
                ),
                evidence_paths=paths,
                error_code="rpa_list_save_error",
                error_message=text or "保存失败（受控 save_error）",
            )

        p5 = _screenshot(page, evidence_dir / "05_after_save.png")
        if p5:
            paths.append(p5)

        new_p = res.get_attribute("data-new-price")
        old_p = res.get_attribute("data-old-price")
        try:
            new_f = float(new_p) if new_p is not None else tp
        except (TypeError, ValueError):
            new_f = tp
        try:
            old_f = float(old_p) if old_p is not None else cp
        except (TypeError, ValueError):
            old_f = cp

        return RpaExecutionOutput(
            success=True,
            result_summary=f"Playwright list_detail OK: {sku} {old_f} -> {new_f}",
            parsed_result=_enriched_pr(
                inp,
                sku=sku,
                old_price=old_f,
                new_price=new_f,
                page_status="success",
                page_message=text,
                operation_result=res.get_attribute("data-operation-result") or "saved",
            ),
            evidence_paths=paths,
            error_code=None,
            error_message=None,
        )

    @staticmethod
    def _click_open_detail_with_retry(page) -> None:
        link = page.locator('[data-testid="open-product-detail"]').first
        last_exc: Exception | None = None
        for attempt in range(2):
            try:
                link.click(timeout=8000)
                return
            except Exception as exc:
                last_exc = exc
                page.wait_for_timeout(400)
        raise last_exc if last_exc else RuntimeError("open detail click failed")

    @staticmethod
    def _click_save_with_retry(page, save_btn) -> None:
        last_exc: Exception | None = None
        for attempt in range(2):
            try:
                save_btn.click(timeout=8000)
                return
            except Exception as exc:
                last_exc = exc
                page.wait_for_timeout(400)
                save_btn = page.locator('[data-testid="detail-save-btn"]')
        raise last_exc if last_exc else RuntimeError("save click failed")

    def _flow_real_admin_prepared_readonly(
        self,
        page,
        evidence_dir: Path,
        paths: list[str],
        inp: RpaExecutionInput,
        sku: str,
        tp: float,
        cp: float,
        readiness_snapshot: dict,
        *,
        timeout_ms: int,
    ) -> RpaExecutionOutput:
        """P4.3: shared real_admin readonly flow (used by confirm/query)."""
        verify_only = bool(inp.params.get("_list_detail_verify_only"))
        return run_real_admin_readonly_flow(
            page=page,
            evidence_dir=evidence_dir,
            evidence_paths=paths,
            sku=sku,
            readiness_snapshot=readiness_snapshot,
            timeout_ms=timeout_ms,
            requested_target_price=float(tp),
            requested_current_price=float(cp),
            verify_mode=str(inp.verify_mode),
            dry_run=bool(inp.dry_run),
            platform=inp.platform,
            read_source="browser_real",
            verify_only=verify_only,
        )


def _tiny_failure_png(evidence_dir: Path, paths: list[str]) -> None:
    p = evidence_dir / "99_failure.png"
    try:
        p.write_bytes(
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb"
            b"\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        paths.append(str(p.resolve()))
    except OSError:
        pass
