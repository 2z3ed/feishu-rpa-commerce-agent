"""Confirm-phase execution for product.update_price via RPA (local_fake or browser_real)."""
from __future__ import annotations

from pathlib import Path

from app.core.config import settings
from app.core.logging import logger
from app.repositories.product_repo import product_repo
from app.utils.task_logger import log_step
from app.rpa.local_fake_runner import LocalFakeRpaRunner
from app.rpa.schema import RpaExecutionInput, RpaRunner
from app.rpa.target_readiness import RpaTargetReadinessResult, evaluate_rpa_target_readiness, norm_rpa_target_profile

INTENT_PRODUCT_UPDATE_PRICE = "product.update_price"


def _readiness_fail_meta(rr: RpaTargetReadinessResult, *, flow: str, evidence_dir: str) -> dict:
    vm = str(settings.RPA_UPDATE_PRICE_VERIFY_MODE or "basic")
    common = {
        "rpa_readiness_failed": True,
        "rpa_target_profile": rr.profile,
        "readiness_details": rr.to_dict(),
        "evidence_dir": evidence_dir,
        "evidence_count": 0,
        "evidence_paths": [],
        "verify_mode": vm,
        "platform": "woo",
        "rpa_runner": settings.RPA_RUNNER_NAME or "browser_real",
    }
    if flow == "rpa":
        common.update(
            {
                "execution_mode": "rpa",
                "selected_backend": "rpa_browser_real",
                "final_backend": "rpa_browser_real",
                "execution_backend": "rpa_browser_real",
            }
        )
        return common
    common.update(
        {
            "execution_mode": "api_then_rpa_verify",
            "selected_backend": "api_then_rpa_verify",
            "final_backend": "api_then_rpa_verify",
            "execution_backend": "api_then_rpa_verify",
            "sku": "",
            "old_price": None,
            "target_price": None,
            "api_result": None,
            "api_price_after_update": None,
            "page_status": "skipped",
            "page_message": "",
            "operation_result": "readiness_failed",
            "verify_passed": False,
            "verify_reason": rr.not_ready_reason or "readiness_failed",
            "rpa_verification_skipped": True,
            "rpa_backend_segment": "none",
        }
    )
    return common


def _maybe_browser_rpa_preflight(confirm_task_id: str, *, flow: str, evidence_dir: str) -> dict | None:
    if (settings.RPA_RUNNER_TYPE or "").lower().strip() != "browser_real":
        return None
    profile = norm_rpa_target_profile(getattr(settings, "RPA_TARGET_PROFILE", None))
    log_step(
        confirm_task_id,
        "profile_selected",
        "success",
        f"profile={profile} flow={flow}",
    )
    rr = evaluate_rpa_target_readiness(settings)
    chk = (
        f"ready={rr.ready} missing_config={','.join(rr.missing_config_fields)} "
        f"missing_session={rr.missing_session} reason={rr.not_ready_reason}"
    )[:900]
    log_step(confirm_task_id, "readiness_checked", "processing", chk)
    if not rr.ready:
        log_step(
            confirm_task_id,
            "readiness_failed",
            "failed",
            (rr.human_error_message() or rr.not_ready_reason)[:900],
        )
        return {
            "error": rr.human_error_message(),
            "error_code": "rpa_target_readiness_failed",
            "evidence_paths": [],
            "_rpa_meta": _readiness_fail_meta(rr, flow=flow, evidence_dir=evidence_dir),
        }
    log_step(confirm_task_id, "readiness_succeeded", "success", "ok")
    return None


def _rpa_observability_meta(
    *,
    runner: RpaRunner,
    evidence_dir: str,
    evidence_paths: list[str],
    verify_mode: str,
    platform: str,
    rpa_backend: str,
) -> dict:
    """Same shape for success / failure so ingress action_executed stays consistent."""
    runner_label = getattr(runner, "runner_name", None) or settings.RPA_RUNNER_NAME or "local_fake"
    return {
        "execution_mode": "rpa",
        "rpa_runner": runner_label,
        "verify_mode": verify_mode,
        "evidence_dir": evidence_dir,
        "evidence_count": len(evidence_paths),
        "evidence_paths": evidence_paths,
        "selected_backend": rpa_backend,
        "final_backend": rpa_backend,
        "execution_backend": rpa_backend,
        "platform": platform,
    }


def _api_then_rpa_verify_meta(
    *,
    runner: RpaRunner | None,
    evidence_dir: str,
    evidence_paths: list[str],
    verify_mode: str,
    platform: str,
    sku: str,
    old_price: float | None,
    target_price: float | None,
    api_result: dict | None,
    api_price_after_update: float | None,
    page_status: str,
    page_message: str,
    operation_result: str,
    verify_passed: bool,
    verify_reason: str,
    rpa_verification_skipped: bool,
) -> dict:
    runner_label = (
        getattr(runner, "runner_name", None) or settings.RPA_RUNNER_NAME or "local_fake"
        if runner
        else "none"
    )
    rpa_backend = getattr(runner, "rpa_backend_obs_id", "rpa_local_fake") if runner else "none"
    return {
        "execution_mode": "api_then_rpa_verify",
        "rpa_runner": runner_label,
        "verify_mode": verify_mode,
        "evidence_dir": evidence_dir,
        "evidence_count": len(evidence_paths),
        "evidence_paths": evidence_paths,
        "selected_backend": "api_then_rpa_verify",
        "final_backend": "api_then_rpa_verify",
        "execution_backend": "api_then_rpa_verify",
        "platform": platform,
        "sku": sku,
        "old_price": old_price,
        "target_price": target_price,
        "api_result": api_result,
        "api_price_after_update": api_price_after_update,
        "page_status": page_status,
        "page_message": page_message,
        "operation_result": operation_result,
        "verify_passed": verify_passed,
        "verify_reason": verify_reason,
        "rpa_verification_skipped": rpa_verification_skipped,
        "rpa_backend_segment": rpa_backend,
    }


def _evidence_root() -> Path:
    base = (settings.RPA_EVIDENCE_BASE_DIR or "data/rpa_evidence").strip()
    return Path(base).resolve()


def build_evidence_dir(confirm_task_id: str) -> str:
    """Real filesystem path for this confirm run; must exist before runner."""
    p = _evidence_root() / confirm_task_id
    try:
        p.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.warning("evidence_dir mkdir failed (will still try runner): %s", exc)
    return str(p.resolve())


def get_update_price_runner(*, force_failure: bool | None = None) -> RpaRunner:
    """local_fake (default) | browser_real (Playwright + internal HTML sandbox)."""
    rtype = (settings.RPA_RUNNER_TYPE or "local_fake").lower().strip()
    if rtype == "browser_real":
        from app.rpa.browser_playwright_runner import PlaywrightUpdatePriceRunner

        ff = settings.RPA_BROWSER_FORCE_FAILURE if force_failure is None else force_failure
        name = settings.RPA_RUNNER_NAME or "browser_real"
        if name.strip() == "local_fake":
            name = "browser_real"
        return PlaywrightUpdatePriceRunner(runner_name=name, force_failure=bool(ff))
    ff = settings.RPA_FAKE_RUNNER_FORCE_FAILURE if force_failure is None else force_failure
    return LocalFakeRpaRunner(
        runner_name=settings.RPA_RUNNER_NAME or "local_fake",
        force_failure=bool(ff),
    )


def _compare_api_page_readback(
    sku_expected: str,
    api_price_after: float,
    target_price: float,
    pr: dict,
) -> tuple[bool, str]:
    ps = (pr.get("page_sku") or pr.get("sku") or "").strip().upper()
    if ps != sku_expected:
        return False, f"sku_mismatch expected={sku_expected} page={ps!r}"
    try:
        pc = float(pr.get("page_current_price", pr.get("old_price")))
    except (TypeError, ValueError):
        return False, "page_current_price_unparseable"
    if abs(pc - api_price_after) > 0.009:
        return False, f"price_mismatch api_after={api_price_after} page_current={pc}"
    try:
        pn = float(pr.get("page_new_price_field", pr.get("new_price", target_price)))
    except (TypeError, ValueError):
        return False, "page_new_price_unparseable"
    if abs(pn - float(target_price)) > 0.009:
        return False, f"target_field_mismatch expected={target_price} page_field={pn}"
    return True, "ok"


def run_confirm_update_price_rpa(
    *,
    confirm_task_id: str,
    trace_id: str,
    sku: str,
    target_price: float,
    platform: str = "woo",
) -> tuple[dict | None, dict | None]:
    """
    Run RPA for confirm flow. Returns (legacy_success_dict, None) or (None, error_dict).

    legacy_success_dict matches mock executor shape for DB / Feishu formatting.
    """
    evidence_dir = build_evidence_dir(confirm_task_id)
    vm = (settings.RPA_UPDATE_PRICE_VERIFY_MODE or "basic").lower().strip()
    if vm not in ("none", "basic", "strict"):
        vm = "basic"
    if pf := _maybe_browser_rpa_preflight(confirm_task_id, flow="rpa", evidence_dir=evidence_dir):
        return None, pf
    sku_u_pre = sku.strip().upper()
    pd0 = product_repo.query_sku_status(sku_u_pre, "mock")
    current_for_page = float(pd0["price"]) if pd0 else 0.0
    inp = RpaExecutionInput(
        task_id=confirm_task_id,
        trace_id=trace_id or confirm_task_id,
        intent=INTENT_PRODUCT_UPDATE_PRICE,
        platform=platform,
        params={
            "sku": sku,
            "target_price": target_price,
            "current_price": current_for_page,
        },
        timeout_s=int(settings.RPA_UPDATE_PRICE_TIMEOUT_S or 180),
        evidence_dir=evidence_dir,
        verify_mode=vm,  # type: ignore[arg-type]
        dry_run=bool(settings.RPA_UPDATE_PRICE_DRY_RUN),
    )
    runner = get_update_price_runner()
    backend_obs = getattr(runner, "rpa_backend_obs_id", "rpa_local_fake")
    out = runner.run(inp)
    vm_str = str(vm)
    readonly_real_admin = norm_rpa_target_profile(getattr(settings, "RPA_TARGET_PROFILE", None)) == "real_admin_prepared"

    if not out.success:
        fail_meta = _rpa_observability_meta(
            runner=runner,
            evidence_dir=evidence_dir,
            evidence_paths=list(out.evidence_paths or []),
            verify_mode=vm_str,
            platform=platform,
            rpa_backend=backend_obs,
        )
        return None, {
            "error": out.error_message or "RPA 执行失败",
            "error_code": out.error_code,
            "evidence_paths": out.evidence_paths,
            "_rpa_meta": fail_meta,
        }

    pr = out.parsed_result
    sku_u = (pr.get("sku") or sku).strip().upper()
    dry_run = bool(pr.get("dry_run", inp.dry_run))

    if readonly_real_admin:
        try:
            opc = float(pr.get("page_current_price", pr.get("old_price")))
            if opc != opc:
                opc = 0.0
        except (TypeError, ValueError):
            opc = 0.0
        legacy = {
            "sku": sku_u,
            "old_price": opc,
            "new_price": float(target_price),
            "status": "success",
            "platform": pr.get("platform", platform),
            "readonly_real_admin_navigation": True,
        }
        meta = _rpa_observability_meta(
            runner=runner,
            evidence_dir=evidence_dir,
            evidence_paths=list(out.evidence_paths or []),
            verify_mode=vm_str,
            platform=pr.get("platform", platform),
            rpa_backend=backend_obs,
        )
        legacy["_rpa_meta"] = meta
        legacy["rpa_evidence_paths"] = out.evidence_paths
        return legacy, None

    if dry_run:
        pd = product_repo.query_sku_status(sku_u, "mock")
        current = float(pd["price"]) if pd else 0.0
        legacy = {
            "sku": sku_u,
            "old_price": current,
            "new_price": float(target_price),
            "status": "success",
            "platform": pr.get("platform", platform),
        }
    else:
        legacy = product_repo.update_price(sku_u, float(target_price), pr.get("platform", platform))
        if not legacy:
            sku_meta = _rpa_observability_meta(
                runner=runner,
                evidence_dir=evidence_dir,
                evidence_paths=list(out.evidence_paths or []),
                verify_mode=vm_str,
                platform=pr.get("platform", platform),
                rpa_backend=backend_obs,
            )
            return None, {
                "error": f"SKU {sku_u} 不存在",
                "error_code": "sku_not_found",
                "evidence_paths": out.evidence_paths,
                "_rpa_meta": sku_meta,
            }

    meta = _rpa_observability_meta(
        runner=runner,
        evidence_dir=evidence_dir,
        evidence_paths=list(out.evidence_paths or []),
        verify_mode=str(inp.verify_mode),
        platform=pr.get("platform", platform),
        rpa_backend=backend_obs,
    )
    legacy["_rpa_meta"] = meta
    legacy["rpa_evidence_paths"] = out.evidence_paths
    return legacy, None


def run_confirm_update_price_api_then_rpa_verify(
    *,
    confirm_task_id: str,
    trace_id: str,
    sku: str,
    target_price: float,
    platform: str = "woo",
) -> tuple[dict | None, dict | None]:
    """
    P3.4: mock_repo API write first, then RPA readback on list_detail (no second write).
    """
    evidence_dir = build_evidence_dir(confirm_task_id)
    vm = (settings.RPA_UPDATE_PRICE_VERIFY_MODE or "basic").lower().strip()
    if vm not in ("none", "basic", "strict"):
        vm = "basic"
    if pf := _maybe_browser_rpa_preflight(
        confirm_task_id, flow="api_then_rpa_verify", evidence_dir=evidence_dir
    ):
        sku_u0 = sku.strip().upper()
        pf["_rpa_meta"]["sku"] = sku_u0
        pf["_rpa_meta"]["target_price"] = float(target_price)
        return None, pf
    sku_u = sku.strip().upper()
    tp_f = float(target_price)

    log_step(
        confirm_task_id,
        "api_execution_started",
        "processing",
        f"target_task_id=via_confirm sku={sku_u} target_price={tp_f}",
    )
    api_legacy = product_repo.update_price(sku_u, tp_f, platform)
    if not api_legacy:
        log_step(
            confirm_task_id,
            "api_execution_failed",
            "failed",
            f"sku={sku_u} error=api_update_sku_not_found",
        )
        log_step(
            confirm_task_id,
            "verification_result_recorded",
            "failed",
            "verify_passed=false reason=api_failed",
        )
        meta = _api_then_rpa_verify_meta(
            runner=None,
            evidence_dir=evidence_dir,
            evidence_paths=[],
            verify_mode=str(vm),
            platform=platform,
            sku=sku_u,
            old_price=None,
            target_price=tp_f,
            api_result=None,
            api_price_after_update=None,
            page_status="skipped",
            page_message="",
            operation_result="api_failed",
            verify_passed=False,
            verify_reason="api_update_sku_not_found",
            rpa_verification_skipped=True,
        )
        return None, {
            "error": f"SKU {sku_u} 不存在（API 段）",
            "error_code": "api_update_sku_not_found",
            "evidence_paths": [],
            "_rpa_meta": meta,
        }

    log_step(
        confirm_task_id,
        "api_execution_succeeded",
        "success",
        f"sku={sku_u} new_price={api_legacy.get('new_price')}",
    )
    api_price_after = float(api_legacy["new_price"])
    old_from_api = float(api_legacy["old_price"])
    display_cp = api_price_after
    if bool(getattr(settings, "RPA_API_THEN_RPA_VERIFY_FORCE_PAGE_MISMATCH", False)):
        display_cp = api_price_after + 100.0

    inp = RpaExecutionInput(
        task_id=confirm_task_id,
        trace_id=trace_id or confirm_task_id,
        intent=INTENT_PRODUCT_UPDATE_PRICE,
        platform=platform,
        params={
            "sku": sku,
            "target_price": tp_f,
            "current_price": display_cp,
            "_list_detail_verify_only": True,
        },
        timeout_s=int(settings.RPA_UPDATE_PRICE_TIMEOUT_S or 180),
        evidence_dir=evidence_dir,
        verify_mode=vm,  # type: ignore[arg-type]
        dry_run=False,
    )
    log_step(
        confirm_task_id,
        "rpa_verification_started",
        "processing",
        f"sku={sku_u} list_detail_verify_only=1",
    )
    runner = get_update_price_runner()
    out = runner.run(inp)

    if not out.success:
        log_step(
            confirm_task_id,
            "rpa_verification_failed",
            "failed",
            f"error_code={out.error_code} msg={(out.error_message or '')[:400]}",
        )
        if out.evidence_paths:
            log_step(
                confirm_task_id,
                "evidence_collected",
                "success",
                f"count={len(out.evidence_paths)}",
            )
        log_step(
            confirm_task_id,
            "verification_result_recorded",
            "failed",
            "verify_passed=false reason=rpa_navigation",
        )
        meta = _api_then_rpa_verify_meta(
            runner=runner,
            evidence_dir=evidence_dir,
            evidence_paths=list(out.evidence_paths or []),
            verify_mode=str(vm),
            platform=platform,
            sku=sku_u,
            old_price=old_from_api,
            target_price=tp_f,
            api_result=dict(api_legacy),
            api_price_after_update=api_price_after,
            page_status="error",
            page_message=str(out.error_message or ""),
            operation_result="rpa_navigation_failed",
            verify_passed=False,
            verify_reason=str(out.error_code or "rpa_failed"),
            rpa_verification_skipped=False,
        )
        return None, {
            "error": out.error_message or "RPA 页面核验失败",
            "error_code": out.error_code,
            "evidence_paths": out.evidence_paths,
            "_rpa_meta": meta,
        }

    pr = out.parsed_result
    ok, reason = _compare_api_page_readback(sku_u, api_price_after, tp_f, pr)
    page_status = str(pr.get("page_status") or "")
    page_message = str(pr.get("page_message") or "")
    operation_result = str(pr.get("operation_result") or "")

    if not ok:
        log_step(
            confirm_task_id,
            "rpa_verification_failed",
            "failed",
            f"compare_failed reason={reason[:400]}",
        )
        if out.evidence_paths:
            log_step(
                confirm_task_id,
                "evidence_collected",
                "success",
                f"count={len(out.evidence_paths)}",
            )
        log_step(
            confirm_task_id,
            "verification_result_recorded",
            "failed",
            f"verify_passed=false reason={reason[:200]}",
        )
        meta = _api_then_rpa_verify_meta(
            runner=runner,
            evidence_dir=evidence_dir,
            evidence_paths=list(out.evidence_paths or []),
            verify_mode=str(vm),
            platform=platform,
            sku=sku_u,
            old_price=old_from_api,
            target_price=tp_f,
            api_result=dict(api_legacy),
            api_price_after_update=api_price_after,
            page_status=page_status,
            page_message=page_message,
            operation_result=operation_result or "readonly_verify",
            verify_passed=False,
            verify_reason=reason,
            rpa_verification_skipped=False,
        )
        return None, {
            "error": f"页面核验未通过：{reason}",
            "error_code": "verify_compare_failed",
            "evidence_paths": out.evidence_paths,
            "_rpa_meta": meta,
        }

    legacy = {
        "sku": sku_u,
        "old_price": old_from_api,
        "new_price": api_price_after,
        "status": "success",
        "platform": platform,
        "verify_passed": True,
        "verify_reason": reason,
        "api_result": dict(api_legacy),
        "api_price_after_update": api_price_after,
        "page_status": page_status,
        "page_message": page_message,
        "operation_result": operation_result,
    }
    meta = _api_then_rpa_verify_meta(
        runner=runner,
        evidence_dir=evidence_dir,
        evidence_paths=list(out.evidence_paths or []),
        verify_mode=str(vm),
        platform=platform,
        sku=sku_u,
        old_price=old_from_api,
        target_price=tp_f,
        api_result=dict(api_legacy),
        api_price_after_update=api_price_after,
        page_status=page_status,
        page_message=page_message,
        operation_result=operation_result,
        verify_passed=True,
        verify_reason=reason,
        rpa_verification_skipped=False,
    )
    legacy["_rpa_meta"] = meta
    legacy["rpa_evidence_paths"] = out.evidence_paths
    log_step(
        confirm_task_id,
        "rpa_verification_succeeded",
        "success",
        f"sku={sku_u} api_price={api_price_after}",
    )
    if out.evidence_paths:
        log_step(
            confirm_task_id,
            "evidence_collected",
            "success",
            f"count={len(out.evidence_paths)}",
        )
    log_step(
        confirm_task_id,
        "verification_result_recorded",
        "success",
        "verify_passed=true",
    )
    return legacy, None


# --- legacy env flag (no-op; use PRODUCT_UPDATE_PRICE_CONFIRM_EXECUTION_BACKEND) ------------

def is_api_then_rpa_verify_enabled() -> bool:
    return bool(getattr(settings, "RPA_API_THEN_RPA_VERIFY_ENABLED", False))


def stub_api_then_rpa_verify_placeholder() -> None:
    """Deprecated: enable api_then_rpa_verify via PRODUCT_UPDATE_PRICE_CONFIRM_EXECUTION_BACKEND."""
    return
