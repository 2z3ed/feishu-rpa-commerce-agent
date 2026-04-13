from __future__ import annotations

from pathlib import Path
from urllib.parse import quote, urljoin

from app.core.config import settings
from app.rpa.schema import RpaExecutionOutput

ERROR_HOME_LOAD_FAILED = "rpa_real_admin_home_load_failed"
ERROR_CATALOG_LOAD_FAILED = "rpa_real_admin_catalog_load_failed"
ERROR_CATALOG_SKU_NOT_FOUND = "rpa_real_admin_catalog_sku_not_found"
ERROR_DETAIL_LOAD_FAILED = "rpa_real_admin_detail_load_failed"
ERROR_DETAIL_SELECTOR_MISSING = "rpa_real_admin_detail_selector_missing"
ERROR_DETAIL_SKU_MISMATCH = "rpa_real_admin_detail_sku_mismatch"


def build_real_admin_target_urls(*, sku: str) -> tuple[str, str, str]:
    sku_u = (sku or "").strip().upper()
    base = (settings.RPA_REAL_ADMIN_BASE_URL or "").strip().rstrip("/")
    home_path = (settings.RPA_REAL_ADMIN_HOME_PATH or "").strip()
    catalog_path = (settings.RPA_REAL_ADMIN_CATALOG_PATH or "").strip()
    detail_tmpl = (settings.RPA_REAL_ADMIN_DETAIL_PATH_TEMPLATE or "").strip()
    sku_param = (settings.RPA_REAL_ADMIN_SKU_SEARCH_PARAM or "").strip()

    home_url = _real_admin_abs_url(base, home_path)
    cat_rel = _real_admin_catalog_with_sku_query(catalog_path, sku_param, sku_u)
    catalog_url = _real_admin_abs_url(base, cat_rel)
    try:
        detail_rel = detail_tmpl.format(sku=sku_u)
    except KeyError:
        detail_rel = detail_tmpl.replace("{sku}", quote(sku_u, safe=""))
    detail_url = _real_admin_abs_url(base, detail_rel)
    return home_url, catalog_url, detail_url


def parse_real_admin_readback(page, *, sku: str, requested_target_price: float) -> dict:
    sku_u = (sku or "").strip().upper()
    price_sel = (settings.RPA_REAL_ADMIN_DETAIL_PRICE_SELECTOR or "").strip()
    sku_sel = (settings.RPA_REAL_ADMIN_DETAIL_SKU_SELECTOR or "").strip()
    status_sel = (settings.RPA_REAL_ADMIN_DETAIL_STATUS_SELECTOR or "").strip()
    msg_sel = (settings.RPA_REAL_ADMIN_DETAIL_MESSAGE_SELECTOR or "").strip()
    new_price_sel = (settings.RPA_REAL_ADMIN_DETAIL_NEW_PRICE_SELECTOR or "").strip()
    name_sel = (settings.RPA_REAL_ADMIN_DETAIL_PRODUCT_NAME_SELECTOR or "").strip()

    raw_price = ""
    try:
        pl = page.locator(price_sel).first
        raw_price = (pl.inner_text(timeout=3000) or "").strip()
        if not raw_price:
            raw_price = (pl.input_value(timeout=3000) or "").strip()
    except Exception:
        raw_price = ""
    page_cur = _parse_float_loose(raw_price)
    if page_cur is None:
        page_cur = float("nan")

    page_disp = ""
    if sku_sel:
        try:
            page_disp = (page.locator(sku_sel).first.inner_text(timeout=3000) or "").strip().upper()
        except Exception:
            page_disp = ""

    product_name = None
    if name_sel:
        try:
            nm = (page.locator(name_sel).first.inner_text(timeout=3000) or "").strip()
            product_name = nm or None
        except Exception:
            product_name = None

    url_u = (page.url or "").upper()
    target_hit = page_disp == sku_u if page_disp else sku_u in url_u

    page_status = "loaded"
    if status_sel:
        try:
            page_status = (page.locator(status_sel).first.inner_text(timeout=3000) or "").strip() or "loaded"
        except Exception:
            page_status = "unknown"

    page_message = ""
    if msg_sel:
        try:
            page_message = (page.locator(msg_sel).first.inner_text(timeout=3000) or "").strip()
        except Exception:
            page_message = ""
    if not page_message:
        page_message = "real_admin_readback_ok" if target_hit else "real_admin_readback_sku_uncertain"

    page_new_field = float(requested_target_price)
    if new_price_sel:
        try:
            raw_n = (page.locator(new_price_sel).first.input_value(timeout=3000) or "").strip()
            if not raw_n:
                raw_n = (page.locator(new_price_sel).first.inner_text(timeout=3000) or "").strip()
            parsed_n = _parse_float_loose(raw_n)
            if parsed_n is not None:
                page_new_field = parsed_n
        except Exception:
            page_new_field = float(requested_target_price)

    return {
        "sku": sku_u,
        "product_name": product_name,
        "page_sku": page_disp or sku_u,
        "page_current_price": page_cur,
        "page_new_price_field": page_new_field,
        "page_status": page_status,
        "page_message": page_message,
        "target_sku_hit": target_hit,
    }


def run_real_admin_readonly_flow(
    *,
    page,
    evidence_dir: Path,
    evidence_paths: list[str],
    sku: str,
    readiness_snapshot: dict,
    timeout_ms: int,
    requested_target_price: float,
    requested_current_price: float,
    verify_mode: str,
    dry_run: bool,
    platform: str,
    read_source: str,
    verify_only: bool,
) -> RpaExecutionOutput:
    sku_u = (sku or "").strip().upper()
    empty_sel = (settings.RPA_REAL_ADMIN_CATALOG_EMPTY_SELECTOR or "").strip()
    price_sel = (settings.RPA_REAL_ADMIN_DETAIL_PRICE_SELECTOR or "").strip()
    profile = "real_admin_prepared"
    operation_result = "readonly_verify" if verify_only else "readonly_readback"

    def _base_parsed(success: bool) -> dict:
        return {
            "sku": sku_u,
            "product_name": None,
            "old_price": requested_current_price,
            "new_price": requested_target_price,
            "target_price": requested_target_price,
            "page_current_price": requested_current_price,
            "page_status": "unknown",
            "page_message": "",
            "target_sku_hit": False,
            "detail_loaded": False,
            "read_source": read_source,
            "profile": profile,
            "rpa_target_profile": profile,
            "readiness": readiness_snapshot,
            "dry_run": bool(dry_run),
            "verify_mode": verify_mode,
            "platform": platform,
            "operation_result": operation_result,
            "session_readback_ok": bool(success),
            "evidence_count": len(evidence_paths),
        }

    def fail(*, summary: str, code: str, message: str, extra: dict | None = None) -> RpaExecutionOutput:
        p99 = _screenshot(page, evidence_dir / "99_failure.png")
        if p99:
            evidence_paths.append(p99)
        pr = _base_parsed(False)
        if extra:
            pr.update(extra)
        pr["evidence_count"] = len(evidence_paths)
        return RpaExecutionOutput(
            success=False,
            result_summary=summary,
            parsed_result=pr,
            evidence_paths=evidence_paths,
            error_code=code,
            error_message=message,
        )

    page.goto("about:blank", wait_until="domcontentloaded")
    p0 = _screenshot(page, evidence_dir / "00_context_prepared.png")
    if p0:
        evidence_paths.append(p0)

    home_url, catalog_url, detail_url = build_real_admin_target_urls(sku=sku_u)
    try:
        resp = page.goto(home_url, wait_until="domcontentloaded", timeout=timeout_ms)
    except Exception as exc:
        return fail(summary=f"home navigation failed: {exc}", code=ERROR_HOME_LOAD_FAILED, message=str(exc))
    if resp is not None and resp.status >= 400:
        return fail(
            summary=f"home HTTP {resp.status}",
            code=ERROR_HOME_LOAD_FAILED,
            message=f"home 页面打不开：HTTP {resp.status}",
        )
    p1 = _screenshot(page, evidence_dir / "01_home_loaded.png")
    if p1:
        evidence_paths.append(p1)

    try:
        cresp = page.goto(catalog_url, wait_until="domcontentloaded", timeout=timeout_ms)
    except Exception as exc:
        return fail(summary=f"catalog navigation failed: {exc}", code=ERROR_CATALOG_LOAD_FAILED, message=str(exc))
    if cresp is not None and cresp.status >= 400:
        return fail(
            summary=f"catalog HTTP {cresp.status}",
            code=ERROR_CATALOG_LOAD_FAILED,
            message=f"catalog 页面打不开：HTTP {cresp.status}",
        )
    try:
        page.wait_for_timeout(400)
        if empty_sel and page.locator(empty_sel).first.is_visible():
            return fail(
                summary="catalog SKU search empty",
                code=ERROR_CATALOG_SKU_NOT_FOUND,
                message="SKU 搜索无结果（目录空态选择器可见）",
                extra={"page_message": "catalog_sku_not_found"},
            )
    except Exception as exc:
        return fail(
            summary=f"catalog empty-state check failed: {exc}",
            code=ERROR_CATALOG_LOAD_FAILED,
            message=str(exc),
        )
    p2 = _screenshot(page, evidence_dir / "02_catalog_loaded.png")
    if p2:
        evidence_paths.append(p2)

    try:
        dresp = page.goto(detail_url, wait_until="domcontentloaded", timeout=timeout_ms)
    except Exception as exc:
        return fail(summary=f"detail navigation failed: {exc}", code=ERROR_DETAIL_LOAD_FAILED, message=str(exc))
    if dresp is not None and dresp.status >= 400:
        return fail(
            summary=f"detail HTTP {dresp.status}",
            code=ERROR_DETAIL_LOAD_FAILED,
            message=f"detail 页面打不开：HTTP {dresp.status}",
        )
    try:
        page.locator(price_sel).first.wait_for(state="visible", timeout=timeout_ms)
    except Exception as exc:
        return fail(
            summary=f"detail price selector missing: {price_sel!r}",
            code=ERROR_DETAIL_SELECTOR_MISSING,
            message=f"detail 关键选择器缺失或不可见：{price_sel!r} ({exc})",
            extra={"detail_loaded": True, "page_message": "detail_selector_missing"},
        )

    p3 = _screenshot(page, evidence_dir / "03_detail_readback.png")
    if p3:
        evidence_paths.append(p3)

    rb = parse_real_admin_readback(page, sku=sku_u, requested_target_price=float(requested_target_price))
    if not rb["target_sku_hit"]:
        return fail(
            summary="detail SKU mismatch vs expected",
            code=ERROR_DETAIL_SKU_MISMATCH,
            message=f"页面未命中目标 SKU：期望 {sku_u}，页面/URL 未对齐",
            extra={
                "detail_loaded": True,
                "page_sku": rb["page_sku"],
                "page_current_price": rb["page_current_price"],
                "page_status": rb["page_status"],
                "page_message": rb["page_message"],
            },
        )

    pr_ok = _base_parsed(True)
    pr_ok.update(rb)
    pr_ok["detail_loaded"] = True
    pr_ok["evidence_count"] = len(evidence_paths)
    old_enriched = rb["page_current_price"] if rb["page_current_price"] == rb["page_current_price"] else 0.0
    pr_ok["old_price"] = old_enriched
    pr_ok["new_price"] = rb["page_new_price_field"]

    return RpaExecutionOutput(
        success=True,
        result_summary=f"Playwright real_admin_prepared readback OK: {sku_u} page_price={rb['page_current_price']}",
        parsed_result=pr_ok,
        evidence_paths=evidence_paths,
        error_code=None,
        error_message=None,
    )


def _real_admin_abs_url(base: str, path_or_url: str) -> str:
    raw = (path_or_url or "").strip()
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    b = (base or "").strip().rstrip("/")
    if not raw.startswith("/"):
        raw = "/" + raw
    return urljoin(b + "/", raw.lstrip("/"))


def _real_admin_catalog_with_sku_query(catalog_path: str, param: str, sku: str) -> str:
    cp = (catalog_path or "").strip()
    sep = "&" if "?" in cp else "?"
    return f"{cp}{sep}{quote(str(param), safe='')}={quote(str(sku), safe='')}"


def _parse_float_loose(raw: str) -> float | None:
    import re

    s = (raw or "").strip().replace(",", "")
    m = re.search(r"[-+]?\d*\.?\d+", s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


def _screenshot(page, path: Path) -> str | None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(path), full_page=True)
        return str(path.resolve())
    except OSError:
        return None
