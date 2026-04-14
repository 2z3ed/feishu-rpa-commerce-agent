from __future__ import annotations

from pathlib import Path
from urllib.parse import quote, unquote, urljoin

from app.core.config import settings
from app.rpa.schema import RpaExecutionOutput
from app.utils.task_logger import log_step

ERROR_HOME_LOAD_FAILED = "rpa_real_admin_home_load_failed"
ERROR_CATALOG_LOAD_FAILED = "rpa_real_admin_catalog_load_failed"
ERROR_CATALOG_SKU_NOT_FOUND = "rpa_real_admin_catalog_sku_not_found"
ERROR_DETAIL_LOAD_FAILED = "rpa_real_admin_detail_load_failed"
ERROR_DETAIL_SELECTOR_MISSING = "rpa_real_admin_detail_selector_missing"
ERROR_DETAIL_SKU_MISMATCH = "rpa_real_admin_detail_sku_mismatch"
ERROR_READINESS_NOT_READY = "rpa_real_admin_readiness_not_ready"
ERROR_READBACK_UNSTABLE = "rpa_real_admin_readback_unstable"

# P4.5 write-flow failure taxonomy (real_admin_prepared only)
ERROR_DETAIL_INPUT_NOT_FOUND = "rpa_real_admin_detail_input_not_found"
ERROR_DETAIL_SAVE_BUTTON_NOT_FOUND = "rpa_real_admin_detail_save_button_not_found"
ERROR_DETAIL_SAVE_BUTTON_DISABLED = "rpa_real_admin_detail_save_button_disabled"
ERROR_DETAIL_SUBMIT_FAILED = "rpa_real_admin_detail_submit_failed"
ERROR_DETAIL_SAVE_RESULT_TIMEOUT = "rpa_real_admin_detail_save_result_timeout"
ERROR_DETAIL_SAVE_RESULT_ERROR = "rpa_real_admin_detail_save_result_error"
ERROR_DETAIL_SUBMIT_NO_EFFECT = "rpa_real_admin_detail_submit_no_effect"
ERROR_DETAIL_POST_SAVE_PRICE_MISMATCH = "rpa_real_admin_detail_post_save_price_mismatch"
ERROR_DETAIL_POST_SAVE_READBACK_MISSING = "rpa_real_admin_detail_post_save_readback_missing"


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
    if price_sel:
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

    page_disp_norm = _normalize_sku_token(page_disp)
    sku_norm = _normalize_sku_token(sku_u)
    url_u = unquote((page.url or "")).upper()
    target_hit = page_disp_norm == sku_norm if page_disp_norm else sku_norm in _normalize_sku_token(url_u)

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

    def _log(step: str, status: str, detail: str) -> None:
        _ = (step, status, detail)
        return

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
            "failure_layer": "",
        }

    def _stabilize_common_fields(parsed: dict, *, success: bool) -> dict:
        stable = dict(parsed or {})
        stable["page_status"] = str(stable.get("page_status") or "unknown")
        stable["page_message"] = str(stable.get("page_message") or "")
        stable["detail_loaded"] = bool(stable.get("detail_loaded"))
        stable["target_sku_hit"] = bool(stable.get("target_sku_hit"))
        stable["read_source"] = str(stable.get("read_source") or read_source or "browser_real")
        stable["evidence_count"] = int(stable.get("evidence_count") or 0)
        if not stable["page_message"]:
            stable["page_message"] = (
                "real_admin_readback_ok"
                if success and stable["target_sku_hit"] and stable["detail_loaded"]
                else "real_admin_readback_incomplete"
            )
        return stable

    def fail(
        *,
        summary: str,
        code: str,
        message: str,
        failure_layer: str = "unknown_exception",
        extra: dict | None = None,
    ) -> RpaExecutionOutput:
        p99 = _screenshot(page, evidence_dir / "99_failure.png")
        if p99:
            evidence_paths.append(p99)
        pr = _base_parsed(False)
        pr["failure_layer"] = failure_layer
        if extra:
            pr.update(extra)
        pr["evidence_count"] = len(evidence_paths)
        pr = _stabilize_common_fields(pr, success=False)
        return RpaExecutionOutput(
            success=False,
            result_summary=f"[{failure_layer}] {summary}",
            parsed_result=pr,
            evidence_paths=evidence_paths,
            error_code=code,
            error_message=f"[{failure_layer}] {message}",
        )

    page.goto("about:blank", wait_until="domcontentloaded")
    p0 = _screenshot(page, evidence_dir / "00_context_prepared.png")
    if p0:
        evidence_paths.append(p0)
    _log("rpa_execution_started", "processing", f"profile=real_admin_prepared sku={sku_u}")

    rr_status = str((readiness_snapshot or {}).get("status", "")).strip().lower()
    if rr_status and rr_status != "ready":
        taxonomy_layer = (
            "session_unavailable"
            if any(token in rr_status for token in ("session", "cookie", "token", "auth", "missing"))
            else "readiness_not_ready"
        )
        return fail(
            summary=f"readiness not ready: {rr_status}",
            code=ERROR_READINESS_NOT_READY,
            message=f"RPA readiness not ready: {rr_status}",
            failure_layer=taxonomy_layer,
            extra={"page_message": f"{taxonomy_layer}:{rr_status}"},
        )

    home_url, catalog_url, detail_url = build_real_admin_target_urls(sku=sku_u)
    try:
        resp = page.goto(home_url, wait_until="domcontentloaded", timeout=timeout_ms)
        page.wait_for_load_state("networkidle", timeout=timeout_ms)
    except Exception as exc:
        return fail(
            summary=f"home navigation failed: {exc}",
            code=ERROR_HOME_LOAD_FAILED,
            message=str(exc),
            failure_layer="page_load_failed:home",
        )
    if resp is not None and resp.status >= 400:
        return fail(
            summary=f"home HTTP {resp.status}",
            code=ERROR_HOME_LOAD_FAILED,
            message=f"home 页面打不开：HTTP {resp.status}",
            failure_layer="page_load_failed:home",
        )
    p1 = _screenshot(page, evidence_dir / "01_home_loaded.png")
    if p1:
        evidence_paths.append(p1)

    try:
        cresp = page.goto(catalog_url, wait_until="domcontentloaded", timeout=timeout_ms)
        page.wait_for_load_state("networkidle", timeout=timeout_ms)
    except Exception as exc:
        return fail(
            summary=f"catalog navigation failed: {exc}",
            code=ERROR_CATALOG_LOAD_FAILED,
            message=str(exc),
            failure_layer="page_load_failed:catalog",
        )
    if cresp is not None and cresp.status >= 400:
        return fail(
            summary=f"catalog HTTP {cresp.status}",
            code=ERROR_CATALOG_LOAD_FAILED,
            message=f"catalog 页面打不开：HTTP {cresp.status}",
            failure_layer="page_load_failed:catalog",
        )
    try:
        page.wait_for_timeout(400)
        if empty_sel and page.locator(empty_sel).first.is_visible():
            return fail(
                summary="catalog SKU search empty",
                code=ERROR_CATALOG_SKU_NOT_FOUND,
                message="SKU 搜索无结果（目录空态选择器可见）",
                failure_layer="sku_not_hit",
                extra={"page_message": "catalog_sku_not_found"},
            )
    except Exception as exc:
        return fail(
            summary=f"catalog empty-state check failed: {exc}",
            code=ERROR_CATALOG_LOAD_FAILED,
            message=str(exc),
            failure_layer="selector_or_page_structure_abnormal",
        )
    p2 = _screenshot(page, evidence_dir / "02_catalog_loaded.png")
    if p2:
        evidence_paths.append(p2)

    try:
        dresp = page.goto(detail_url, wait_until="domcontentloaded", timeout=timeout_ms)
        page.wait_for_load_state("networkidle", timeout=timeout_ms)
    except Exception as exc:
        return fail(
            summary=f"detail navigation failed: {exc}",
            code=ERROR_DETAIL_LOAD_FAILED,
            message=str(exc),
            failure_layer="page_load_failed:detail",
        )
    if dresp is not None and dresp.status >= 400:
        return fail(
            summary=f"detail HTTP {dresp.status}",
            code=ERROR_DETAIL_LOAD_FAILED,
            message=f"detail 页面打不开：HTTP {dresp.status}",
            failure_layer="page_load_failed:detail",
        )
    try:
        page.locator(price_sel).first.wait_for(state="visible", timeout=timeout_ms)
    except Exception as exc:
        return fail(
            summary=f"detail price selector missing: {price_sel!r}",
            code=ERROR_DETAIL_SELECTOR_MISSING,
            message=f"detail 关键选择器缺失或不可见：{price_sel!r} ({exc})",
            failure_layer="detail_not_loaded",
            extra={"detail_loaded": False, "page_message": "detail_selector_missing"},
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
            failure_layer="sku_not_hit",
            extra={
                "detail_loaded": True,
                "page_sku": rb["page_sku"],
                "page_current_price": rb["page_current_price"],
                "page_status": rb["page_status"],
                "page_message": rb["page_message"],
            },
        )
    if rb["page_current_price"] != rb["page_current_price"]:
        return fail(
            summary="detail readback current price is not parseable",
            code=ERROR_READBACK_UNSTABLE,
            message="detail 读回当前价不可解析，readback 不稳定",
            failure_layer="readback_unstable",
            extra={
                "detail_loaded": True,
                "page_sku": rb["page_sku"],
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
    pr_ok = _stabilize_common_fields(pr_ok, success=True)

    return RpaExecutionOutput(
        success=True,
        result_summary=f"Playwright real_admin_prepared readback OK: {sku_u} page_price={rb['page_current_price']}",
        parsed_result=pr_ok,
        evidence_paths=evidence_paths,
        error_code=None,
        error_message=None,
    )


def run_real_admin_update_price_flow(
    *,
    page,
    evidence_dir: Path,
    evidence_paths: list[str],
    task_id: str,
    sku: str,
    readiness_snapshot: dict,
    timeout_ms: int,
    requested_target_price: float,
    requested_current_price: float,
    verify_mode: str,
    dry_run: bool,
    platform: str,
    read_source: str,
) -> RpaExecutionOutput:
    """
    P4.5: real_admin_prepared write flow via browser_real.

    Contract: extend readonly parsed_result with write fields (input/save/result/readback/compare).
    """
    sku_u = (sku or "").strip().upper()
    empty_sel = (settings.RPA_REAL_ADMIN_CATALOG_EMPTY_SELECTOR or "").strip()
    price_sel = (settings.RPA_REAL_ADMIN_DETAIL_PRICE_SELECTOR or "").strip()
    sku_sel = (settings.RPA_REAL_ADMIN_DETAIL_SKU_SELECTOR or "").strip()
    status_sel = (settings.RPA_REAL_ADMIN_DETAIL_STATUS_SELECTOR or "").strip()
    msg_sel = (settings.RPA_REAL_ADMIN_DETAIL_MESSAGE_SELECTOR or "").strip()
    new_price_sel = (settings.RPA_REAL_ADMIN_DETAIL_NEW_PRICE_SELECTOR or "").strip()
    name_sel = (settings.RPA_REAL_ADMIN_DETAIL_PRODUCT_NAME_SELECTOR or "").strip()
    save_btn_sel = (settings.RPA_REAL_ADMIN_DETAIL_SAVE_BUTTON_SELECTOR or "").strip()
    save_res_sel = (settings.RPA_REAL_ADMIN_DETAIL_SAVE_RESULT_SELECTOR or "").strip()

    profile = "real_admin_prepared"
    operation_result = "write_update_price"
    tol = float(getattr(settings, "RPA_REAL_ADMIN_PRICE_COMPARE_TOLERANCE", 0.009) or 0.009)

    def _log(step: str, status: str, detail: str) -> None:
        if not task_id:
            return
        try:
            log_step(task_id, step, status, detail)
        except Exception:
            return

    def _base_parsed(success: bool) -> dict:
        return {
            "sku": sku_u,
            "product_name": None,
            "old_price": requested_current_price,
            "new_price": requested_target_price,
            "target_price": requested_target_price,
            "page_current_price": requested_current_price,
            "page_current_price_after_save": None,
            "post_save_price": None,
            "page_new_price_field": requested_target_price,
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
            "failure_layer": "",
            # --- write contract ---
            "input_price": None,
            "submit_attempted": False,
            "submit_result": "skipped" if dry_run else "unknown",
            "save_result_text": "",
            "verify_passed": False,
            "verify_reason": "",
            "verify_error_code": None,
            "compare_tolerance": tol,
        }

    def fail(
        *,
        summary: str,
        code: str,
        message: str,
        failure_layer: str = "unknown_exception",
        extra: dict | None = None,
    ) -> RpaExecutionOutput:
        p99 = _screenshot(page, evidence_dir / "99_failure.png")
        if p99:
            evidence_paths.append(p99)
        pr = _base_parsed(False)
        pr["failure_layer"] = failure_layer
        if extra:
            pr.update(extra)
        pr["evidence_count"] = len(evidence_paths)
        return RpaExecutionOutput(
            success=False,
            result_summary=f"[{failure_layer}] {summary}",
            parsed_result=pr,
            evidence_paths=evidence_paths,
            error_code=code,
            error_message=f"[{failure_layer}] {message}",
        )

    page.goto("about:blank", wait_until="domcontentloaded")
    p0 = _screenshot(page, evidence_dir / "00_context_prepared.png")
    if p0:
        evidence_paths.append(p0)

    home_url, catalog_url, detail_url = build_real_admin_target_urls(sku=sku_u)
    try:
        resp = page.goto(home_url, wait_until="domcontentloaded", timeout=timeout_ms)
    except Exception as exc:
        return fail(
            summary=f"home navigation failed: {exc}",
            code=ERROR_HOME_LOAD_FAILED,
            message=str(exc),
            failure_layer="unknown_exception",
        )
    if resp is not None and resp.status >= 400:
        return fail(
            summary=f"home HTTP {resp.status}",
            code=ERROR_HOME_LOAD_FAILED,
            message=f"home 页面打不开：HTTP {resp.status}",
            failure_layer="unknown_exception",
        )
    p1 = _screenshot(page, evidence_dir / "01_home_loaded.png")
    if p1:
        evidence_paths.append(p1)

    try:
        cresp = page.goto(catalog_url, wait_until="domcontentloaded", timeout=timeout_ms)
    except Exception as exc:
        return fail(
            summary=f"catalog navigation failed: {exc}",
            code=ERROR_CATALOG_LOAD_FAILED,
            message=str(exc),
            failure_layer="unknown_exception",
        )
    if cresp is not None and cresp.status >= 400:
        return fail(
            summary=f"catalog HTTP {cresp.status}",
            code=ERROR_CATALOG_LOAD_FAILED,
            message=f"catalog 页面打不开：HTTP {cresp.status}",
            failure_layer="unknown_exception",
        )
    try:
        page.wait_for_timeout(400)
        if empty_sel and page.locator(empty_sel).first.is_visible():
            return fail(
                summary="catalog SKU search empty",
                code=ERROR_CATALOG_SKU_NOT_FOUND,
                message="SKU 搜索无结果（目录空态选择器可见）",
                failure_layer="sku_not_hit",
                extra={"page_message": "catalog_sku_not_found"},
            )
    except Exception as exc:
        return fail(
            summary=f"catalog empty-state check failed: {exc}",
            code=ERROR_CATALOG_LOAD_FAILED,
            message=str(exc),
            failure_layer="unknown_exception",
        )
    p2 = _screenshot(page, evidence_dir / "02_catalog_loaded.png")
    if p2:
        evidence_paths.append(p2)

    try:
        dresp = page.goto(detail_url, wait_until="domcontentloaded", timeout=timeout_ms)
    except Exception as exc:
        return fail(
            summary=f"detail navigation failed: {exc}",
            code=ERROR_DETAIL_LOAD_FAILED,
            message=str(exc),
            failure_layer="unknown_exception",
        )
    if dresp is not None and dresp.status >= 400:
        return fail(
            summary=f"detail HTTP {dresp.status}",
            code=ERROR_DETAIL_LOAD_FAILED,
            message=f"detail 页面打不开：HTTP {dresp.status}",
            failure_layer="unknown_exception",
        )
    try:
        page.locator(price_sel).first.wait_for(state="visible", timeout=timeout_ms)
    except Exception as exc:
        return fail(
            summary=f"detail price selector missing: {price_sel!r}",
            code=ERROR_DETAIL_SELECTOR_MISSING,
            message=f"detail 关键选择器缺失或不可见：{price_sel!r} ({exc})",
            failure_layer="current_price_read_failed",
            extra={"detail_loaded": True, "page_message": "detail_selector_missing"},
        )

    p3 = _screenshot(page, evidence_dir / "03_detail_before_edit.png")
    if p3:
        evidence_paths.append(p3)

    rb0 = parse_real_admin_readback(page, sku=sku_u, requested_target_price=float(requested_target_price))
    if not rb0["target_sku_hit"]:
        return fail(
            summary="detail SKU mismatch vs expected",
            code=ERROR_DETAIL_SKU_MISMATCH,
            message=f"页面未命中目标 SKU：期望 {sku_u}，页面/URL 未对齐",
            failure_layer="sku_not_hit",
            extra={
                "detail_loaded": True,
                "page_sku": rb0["page_sku"],
                "page_current_price": rb0["page_current_price"],
                "page_status": rb0["page_status"],
                "page_message": rb0["page_message"],
            },
        )
    _log("detail_before_edit", "success", f"evidence=03_detail_before_edit.png old_price={rb0.get('page_current_price')}")

    # --- locate input ---
    if not new_price_sel:
        return fail(
            summary="new price selector not configured",
            code=ERROR_DETAIL_INPUT_NOT_FOUND,
            message="未配置新价格输入框选择器：RPA_REAL_ADMIN_DETAIL_NEW_PRICE_SELECTOR",
            failure_layer="new_price_fill_failed",
            extra={"detail_loaded": True, "page_message": "new_price_selector_missing"},
        )
    try:
        ip = page.locator(new_price_sel).first
        ip.wait_for(state="visible", timeout=timeout_ms)
    except Exception as exc:
        return fail(
            summary=f"detail input not found: {new_price_sel!r}",
            code=ERROR_DETAIL_INPUT_NOT_FOUND,
            message=f"detail 新价格输入框缺失或不可见：{new_price_sel!r} ({exc})",
            failure_layer="edit_mode_not_entered",
            extra={"detail_loaded": True, "page_message": "detail_input_missing"},
        )

    # input value
    input_price = float(requested_target_price)
    try:
        ip.fill(str(input_price), timeout=timeout_ms)
    except Exception as exc:
        return fail(
            summary=f"fill target price failed: {exc}",
            code=ERROR_DETAIL_INPUT_NOT_FOUND,
            message=str(exc),
            failure_layer="new_price_fill_failed",
            extra={"detail_loaded": True, "page_message": "detail_input_fill_failed"},
        )
    p4 = _screenshot(page, evidence_dir / "04_after_input.png")
    if p4:
        evidence_paths.append(p4)
    _log("detail_after_input", "success", f"evidence=04_after_input.png input_price={input_price}")

    # --- locate save button ---
    if not save_btn_sel:
        return fail(
            summary="save button selector not configured",
            code=ERROR_DETAIL_SAVE_BUTTON_NOT_FOUND,
            message="未配置保存按钮选择器：RPA_REAL_ADMIN_DETAIL_SAVE_BUTTON_SELECTOR",
            failure_layer="save_button_unavailable",
            extra={"detail_loaded": True, "page_message": "save_button_selector_missing", "input_price": input_price},
        )
    try:
        sb = page.locator(save_btn_sel).first
        sb.wait_for(state="visible", timeout=timeout_ms)
    except Exception as exc:
        return fail(
            summary=f"save button not found: {save_btn_sel!r}",
            code=ERROR_DETAIL_SAVE_BUTTON_NOT_FOUND,
            message=f"detail 保存按钮缺失或不可见：{save_btn_sel!r} ({exc})",
            failure_layer="save_button_unavailable",
            extra={"detail_loaded": True, "page_message": "save_button_missing", "input_price": input_price},
        )

    try:
        if not sb.is_enabled():
            return fail(
                summary="save button disabled",
                code=ERROR_DETAIL_SAVE_BUTTON_DISABLED,
                message="detail 保存按钮不可用（disabled）",
                failure_layer="save_button_unavailable",
                extra={"detail_loaded": True, "page_message": "save_button_disabled", "input_price": input_price},
            )
    except Exception as exc:
        return fail(
            summary=f"save button state check failed: {exc}",
            code=ERROR_DETAIL_SAVE_BUTTON_DISABLED,
            message=str(exc),
            failure_layer="save_button_unavailable",
            extra={"detail_loaded": True, "page_message": "save_button_state_unknown", "input_price": input_price},
        )

    p5 = _screenshot(page, evidence_dir / "05_before_submit.png")
    if p5:
        evidence_paths.append(p5)
    _log("detail_before_submit", "success", "evidence=05_before_submit.png")

    if dry_run:
        pr_skip = _base_parsed(False)
        pr_skip.update(rb0)
        pr_skip.update(
            {
                "detail_loaded": True,
                "input_price": input_price,
                "submit_attempted": False,
                "submit_result": "skipped",
                "page_message": "dry_run_skip_submit",
                "verify_passed": False,
                "verify_reason": "dry_run_skipped",
                "verify_error_code": "rpa_real_admin_write_dry_run_not_allowed",
            }
        )
        pr_skip["evidence_count"] = len(evidence_paths)
        return RpaExecutionOutput(
            success=False,
            result_summary=f"real_admin_prepared dry-run is not allowed for write flow: {sku_u}",
            parsed_result=pr_skip,
            evidence_paths=evidence_paths,
            error_code="rpa_real_admin_write_dry_run_not_allowed",
            error_message="real_admin_prepared 写链不允许 dry_run（必须真实提交并写后读回核验）",
        )

    # submit
    try:
        sb.click(timeout=timeout_ms)
    except Exception as exc:
        return fail(
            summary=f"submit click failed: {exc}",
            code=ERROR_DETAIL_SUBMIT_FAILED,
            message=str(exc),
            failure_layer="save_feedback_failed",
            extra={
                "detail_loaded": True,
                "page_message": "submit_click_failed",
                "input_price": input_price,
                "submit_attempted": True,
                "submit_result": "click_failed",
            },
        )

    p6 = _screenshot(page, evidence_dir / "06_after_submit.png")
    if p6:
        evidence_paths.append(p6)
    _log("detail_after_submit", "success", "evidence=06_after_submit.png")

    # wait result
    if not save_res_sel:
        return fail(
            summary="save result selector not configured",
            code=ERROR_DETAIL_SAVE_RESULT_TIMEOUT,
            message="未配置保存结果选择器：RPA_REAL_ADMIN_DETAIL_SAVE_RESULT_SELECTOR",
            failure_layer="save_feedback_failed",
            extra={
                "detail_loaded": True,
                "page_message": "save_result_selector_missing",
                "input_price": input_price,
                "submit_attempted": True,
                "submit_result": "submitted",
                "verify_passed": False,
                "verify_reason": "save_result_timeout",
                "verify_error_code": ERROR_DETAIL_SAVE_RESULT_TIMEOUT,
            },
        )
    try:
        page.locator(save_res_sel).first.wait_for(state="visible", timeout=timeout_ms)
    except Exception as exc:
        return fail(
            summary=f"save result timeout: {exc}",
            code=ERROR_DETAIL_SAVE_RESULT_TIMEOUT,
            message=f"保存结果超时：{save_res_sel!r} ({exc})",
            failure_layer="save_feedback_failed",
            extra={
                "detail_loaded": True,
                "page_message": "save_result_timeout",
                "input_price": input_price,
                "submit_attempted": True,
                "submit_result": "submitted",
                "verify_passed": False,
                "verify_reason": "save_result_timeout",
                "verify_error_code": ERROR_DETAIL_SAVE_RESULT_TIMEOUT,
            },
        )

    res_el = page.locator(save_res_sel).first
    save_text = ""
    save_status = ""
    try:
        save_text = (res_el.inner_text(timeout=3000) or "").strip()
    except Exception:
        save_text = ""
    try:
        save_status = (res_el.get_attribute("data-status") or "").strip().lower()
    except Exception:
        save_status = ""

    p7 = _screenshot(page, evidence_dir / "07_post_save_readback.png")
    if p7:
        evidence_paths.append(p7)
    _log("detail_post_save_readback", "processing", "evidence=07_post_save_readback.png")

    if save_status in ("error", "failed", "fail"):
        return fail(
            summary=f"save result reported error: {save_text[:200]}",
            code=ERROR_DETAIL_SAVE_RESULT_ERROR,
            message=save_text or "保存结果返回 error",
            failure_layer="save_feedback_failed",
            extra={
                "detail_loaded": True,
                "page_message": "save_result_error",
                "input_price": input_price,
                "submit_attempted": True,
                "submit_result": "failed",
                "save_result_text": save_text,
                "verify_passed": False,
                "verify_reason": "save_result_error",
                "verify_error_code": ERROR_DETAIL_SAVE_RESULT_ERROR,
            },
        )
    if save_status not in ("success", "ok"):
        return fail(
            summary="submit completed but no success status",
            code=ERROR_DETAIL_SUBMIT_NO_EFFECT,
            message="点击保存后未获得可判定的成功状态（保存结果区无 success/ok）",
            failure_layer="save_feedback_failed",
            extra={
                "detail_loaded": True,
                "page_message": "submit_no_effect",
                "input_price": input_price,
                "submit_attempted": True,
                "submit_result": "no_effect",
                "save_result_text": save_text,
                "verify_passed": False,
                "verify_reason": "submit_no_effect",
                "verify_error_code": ERROR_DETAIL_SUBMIT_NO_EFFECT,
            },
        )

    # readback current price after save
    raw_after = ""
    try:
        pl_after = page.locator(price_sel).first
        raw_after = (pl_after.inner_text(timeout=3000) or "").strip()
        if not raw_after:
            raw_after = (pl_after.input_value(timeout=3000) or "").strip()
    except Exception as exc:
        return fail(
            summary=f"post-save readback missing: {exc}",
            code=ERROR_DETAIL_POST_SAVE_READBACK_MISSING,
            message="保存后读回当前价失败（选择器缺失或不可读）",
            failure_layer="post_write_verify_mismatch",
            extra={
                "detail_loaded": True,
                "page_message": "post_save_readback_missing",
                "input_price": input_price,
                "submit_attempted": True,
                "submit_result": "success",
                "save_result_text": save_text,
                "verify_passed": False,
                "verify_reason": "post_save_readback_missing",
                "verify_error_code": ERROR_DETAIL_POST_SAVE_READBACK_MISSING,
            },
        )
    after_price = _parse_float_loose(raw_after)
    if after_price is None:
        return fail(
            summary="post-save current price unparseable",
            code=ERROR_DETAIL_POST_SAVE_READBACK_MISSING,
            message=f"保存后当前价不可解析：{raw_after!r}",
            failure_layer="post_write_verify_mismatch",
            extra={
                "detail_loaded": True,
                "page_message": "post_save_readback_unparseable",
                "input_price": input_price,
                "submit_attempted": True,
                "submit_result": "success",
                "save_result_text": save_text,
                "verify_passed": False,
                "verify_reason": "post_save_readback_missing",
                "verify_error_code": ERROR_DETAIL_POST_SAVE_READBACK_MISSING,
            },
        )

    # product name (best-effort)
    product_name = None
    if name_sel:
        try:
            nm = (page.locator(name_sel).first.inner_text(timeout=3000) or "").strip()
            product_name = nm or None
        except Exception:
            product_name = None

    page_disp = ""
    if sku_sel:
        try:
            page_disp = (page.locator(sku_sel).first.inner_text(timeout=3000) or "").strip().upper()
        except Exception:
            page_disp = ""
    if not page_disp:
        page_disp = sku_u

    # status/message (best-effort)
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
        page_message = save_text or "saved"

    # compare
    expected = float(requested_target_price)
    verify_passed = abs(float(after_price) - expected) <= tol
    if not verify_passed:
        return fail(
            summary=f"post-save price mismatch expected={expected} got={after_price}",
            code=ERROR_DETAIL_POST_SAVE_PRICE_MISMATCH,
            message=f"保存后价格不一致：期望 {expected}，读回 {after_price}",
            failure_layer="post_write_verify_mismatch",
            extra={
                "detail_loaded": True,
                "product_name": product_name,
                "page_sku": page_disp,
                "page_current_price": rb0.get("page_current_price"),
                "page_current_price_after_save": after_price,
                "post_save_price": after_price,
                "page_status": page_status,
                "page_message": page_message,
                "target_sku_hit": True,
                "input_price": input_price,
                "submit_attempted": True,
                "submit_result": "success",
                "save_result_text": save_text,
                "verify_passed": False,
                "verify_reason": "post_save_price_mismatch",
                "verify_error_code": ERROR_DETAIL_POST_SAVE_PRICE_MISMATCH,
            },
        )

    pr_ok = _base_parsed(True)
    pr_ok.update(
        {
            "product_name": product_name,
            "page_sku": page_disp,
            "page_current_price": rb0.get("page_current_price"),
            "page_new_price_field": input_price,
            "page_current_price_after_save": after_price,
            "post_save_price": after_price,
            "page_status": page_status,
            "page_message": page_message,
            "target_sku_hit": True,
            "detail_loaded": True,
            "old_price": rb0.get("page_current_price"),
            "new_price": expected,
            "target_price": expected,
            "input_price": input_price,
            "submit_attempted": True,
            "submit_result": "success",
            "save_result_text": save_text,
            "verify_passed": True,
            "verify_reason": "ok",
            "verify_error_code": None,
        }
    )
    pr_ok["evidence_count"] = len(evidence_paths)
    return RpaExecutionOutput(
        success=True,
        result_summary=f"Playwright real_admin_prepared write OK: {sku_u} -> {expected} (readback={after_price})",
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


def _normalize_sku_token(raw: str) -> str:
    import re

    return re.sub(r"[^A-Z0-9]+", "", (raw or "").upper())


def _screenshot(page, path: Path) -> str | None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(path), full_page=True)
        return str(path.resolve())
    except OSError:
        return None
