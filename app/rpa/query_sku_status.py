from __future__ import annotations

from app.core.config import settings
from app.rpa.confirm_update_price import build_evidence_dir, get_update_price_runner
from app.rpa.schema import RpaExecutionInput
from app.rpa.target_readiness import evaluate_rpa_target_readiness, norm_rpa_target_profile
from app.repositories.product_repo import product_repo
from app.utils.task_logger import log_step


def run_query_sku_status_real_admin_readonly(*, task_id: str, trace_id: str, sku: str) -> tuple[dict | None, dict | None]:
    def _log(step: str, status: str, detail: str) -> None:
        if task_id:
            log_step(task_id, step, status, detail)

    profile = norm_rpa_target_profile(getattr(settings, "RPA_TARGET_PROFILE", None))
    _log("profile_selected", "success", f"profile={profile} flow=query_readonly")
    if profile != "real_admin_prepared":
        return None, {
            "error": "query readonly bridge requires RPA_TARGET_PROFILE=real_admin_prepared",
            "error_code": "rpa_query_profile_not_supported",
        }

    rr = evaluate_rpa_target_readiness(settings)
    chk = (
        f"ready={rr.ready} missing_config={','.join(rr.missing_config_fields)} "
        f"missing_session={rr.missing_session} reason={rr.not_ready_reason}"
    )[:900]
    _log("readiness_checked", "processing", chk)
    if not rr.ready:
        _log("readiness_failed", "failed", (rr.human_error_message() or rr.not_ready_reason)[:900])
        return None, {
            "error": rr.human_error_message(),
            "error_code": "rpa_target_readiness_failed",
            "_rpa_meta": {
                "execution_mode": "rpa",
                "execution_backend": "rpa_browser_real",
                "selected_backend": "rpa_browser_real",
                "final_backend": "rpa_browser_real",
                "rpa_runner": settings.RPA_RUNNER_NAME or "browser_real",
                "verify_mode": "basic",
                "evidence_count": 0,
                "readiness_details": rr.to_dict(),
                "platform": "woo",
            },
        }
    _log("readiness_succeeded", "success", "ok")

    current = product_repo.query_sku_status(sku, "mock")
    cur_price = float(current["price"]) if current else 0.0
    evidence_dir = build_evidence_dir(task_id)
    inp = RpaExecutionInput(
        task_id=task_id,
        trace_id=trace_id or task_id,
        intent="product.query_sku_status",
        platform="woo",
        params={"sku": sku, "current_price": cur_price, "target_price": cur_price},
        timeout_s=int(settings.RPA_UPDATE_PRICE_TIMEOUT_S or 180),
        evidence_dir=evidence_dir,
        verify_mode="basic",
        dry_run=True,
    )
    _log("readonly_read_started", "processing", f"sku={sku.strip().upper()} profile={profile}")
    runner = get_update_price_runner(force_failure=False)
    out = runner.run(inp)
    meta = {
        "execution_mode": "rpa",
        "execution_backend": "rpa_browser_real",
        "selected_backend": "rpa_browser_real",
        "final_backend": "rpa_browser_real",
        "rpa_runner": getattr(runner, "runner_name", None) or settings.RPA_RUNNER_NAME or "browser_real",
        "verify_mode": "basic",
        "evidence_count": len(out.evidence_paths or []),
        "evidence_paths": list(out.evidence_paths or []),
        "platform": "woo",
    }
    if not out.success:
        failure_layer = str((out.parsed_result or {}).get("failure_layer") or "unknown_exception")
        _log(
            "readonly_read_failed",
            "failed",
            f"failure_layer={failure_layer} error_code={out.error_code} msg={(out.error_message or '')[:400]}",
        )
        return None, {
            "error": out.error_message or "readonly query failed",
            "error_code": out.error_code or "rpa_query_read_failed",
            "_rpa_meta": meta,
            "parsed_result": out.parsed_result,
        }

    _log("readonly_read_succeeded", "success", f"evidence_count={len(out.evidence_paths or [])}")
    pr = out.parsed_result or {}
    price = pr.get("page_current_price")
    try:
        q_price = float(price)
        if q_price != q_price:
            q_price = 0.0
    except (TypeError, ValueError):
        q_price = 0.0
    query_result = {
        "sku": pr.get("sku") or sku.strip().upper(),
        "product_name": pr.get("product_name") or (current or {}).get("product_name") or "",
        "status": pr.get("page_status") or ((current or {}).get("status") or "unknown"),
        "inventory": (current or {}).get("inventory", 0),
        "price": q_price,
        "platform": "woo",
        "page_status": pr.get("page_status"),
        "page_message": pr.get("page_message"),
        "target_sku_hit": bool(pr.get("target_sku_hit")),
        "detail_loaded": bool(pr.get("detail_loaded")),
        "read_source": pr.get("read_source") or "browser_real",
        "profile": pr.get("profile") or "real_admin_prepared",
        "evidence_count": int(pr.get("evidence_count", len(out.evidence_paths or []))),
    }
    return {"query_result": query_result, "_rpa_meta": meta}, None
