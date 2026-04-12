"""Confirm-phase execution for product.update_price via RPA (dev fake runner)."""
from __future__ import annotations

from pathlib import Path

from app.core.config import settings
from app.core.logging import logger
from app.repositories.product_repo import product_repo
from app.rpa.local_fake_runner import LocalFakeRpaRunner
from app.rpa.schema import RpaExecutionInput, RpaRunner

INTENT_PRODUCT_UPDATE_PRICE = "product.update_price"


def _rpa_observability_meta(
    *,
    runner: RpaRunner,
    evidence_dir: str,
    evidence_paths: list[str],
    verify_mode: str,
    platform: str,
) -> dict:
    """Same shape for success / failure so ingress action_executed stays consistent."""
    return {
        "execution_mode": "rpa",
        "rpa_runner": settings.RPA_RUNNER_NAME or getattr(runner, "runner_name", "local_fake"),
        "verify_mode": verify_mode,
        "evidence_dir": evidence_dir,
        "evidence_count": len(evidence_paths),
        "evidence_paths": evidence_paths,
        "selected_backend": "rpa_local_fake",
        "final_backend": "rpa_local_fake",
        "execution_backend": "rpa_local_fake",
        "platform": platform,
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
    """Single factory for the dev-stage runner (swap for Playwright later)."""
    ff = settings.RPA_FAKE_RUNNER_FORCE_FAILURE if force_failure is None else force_failure
    return LocalFakeRpaRunner(
        runner_name=settings.RPA_RUNNER_NAME or "local_fake",
        force_failure=bool(ff),
    )


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
    inp = RpaExecutionInput(
        task_id=confirm_task_id,
        trace_id=trace_id or confirm_task_id,
        intent=INTENT_PRODUCT_UPDATE_PRICE,
        platform=platform,
        params={"sku": sku, "target_price": target_price},
        timeout_s=int(settings.RPA_UPDATE_PRICE_TIMEOUT_S or 180),
        evidence_dir=evidence_dir,
        verify_mode=vm,  # type: ignore[arg-type]
        dry_run=bool(settings.RPA_UPDATE_PRICE_DRY_RUN),
    )
    stub_api_then_rpa_verify_placeholder()
    runner = get_update_price_runner()
    out = runner.run(inp)
    vm_str = str(vm)

    if not out.success:
        fail_meta = _rpa_observability_meta(
            runner=runner,
            evidence_dir=evidence_dir,
            evidence_paths=list(out.evidence_paths or []),
            verify_mode=vm_str,
            platform=platform,
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
    )
    legacy["_rpa_meta"] = meta
    legacy["rpa_evidence_paths"] = out.evidence_paths
    return legacy, None


# --- api_then_rpa_verify: minimal stub (disabled by default) -----------------

def is_api_then_rpa_verify_enabled() -> bool:
    return bool(getattr(settings, "RPA_API_THEN_RPA_VERIFY_ENABLED", False))


def stub_api_then_rpa_verify_placeholder() -> None:
    """Reserved hook: call API then RPA verify; off unless RPA_API_THEN_RPA_VERIFY_ENABLED."""
    if not is_api_then_rpa_verify_enabled():
        return
    logger.info("api_then_rpa_verify stub is enabled but not implemented in this phase")
