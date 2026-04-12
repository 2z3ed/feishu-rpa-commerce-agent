"""
Local fake RPA runner for product.update_price (sandbox HTML / dev only).

Writes minimal PNG evidence files; does not open a real browser.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.core.logging import logger
from app.rpa.schema import RpaExecutionInput, RpaExecutionOutput, RpaRunner

# Minimal valid 1x1 PNG (placeholder screenshot)
_MIN_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _write_png(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_MIN_PNG)


def _safe_write_evidence(evidence_dir: Path, name: str) -> str | None:
    try:
        p = evidence_dir / name
        _write_png(p)
        return str(p.resolve())
    except OSError as exc:
        logger.warning("RPA evidence write skipped: %s", exc)
        return None


class LocalFakeRpaRunner(RpaRunner):
    """Dev-only fake runner: evidence PNGs + optional forced failure (tests)."""

    rpa_backend_obs_id = "rpa_local_fake"

    def __init__(self, *, runner_name: str = "local_fake", force_failure: bool = False):
        self.runner_name = runner_name
        self.force_failure = force_failure

    def run(self, inp: RpaExecutionInput) -> RpaExecutionOutput:
        sku = (inp.params.get("sku") or "").strip().upper()
        target_price = inp.params.get("target_price")
        evidence_dir = Path(inp.evidence_dir)
        paths: list[str] = []

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

        for name in ("01_enter_target.png", "02_before_action.png"):
            p = _safe_write_evidence(evidence_dir, name)
            if p:
                paths.append(p)

        if self.force_failure:
            p = _safe_write_evidence(evidence_dir, "99_failure.png")
            if p:
                paths.append(p)
            return RpaExecutionOutput(
                success=False,
                result_summary="RPA fake runner forced failure (dev)",
                parsed_result={"sku": sku, "target_price": target_price},
                evidence_paths=paths,
                error_code="rpa_fake_forced_failure",
                error_message="LocalFakeRpaRunner: force_failure enabled",
            )

        if not sku:
            p = _safe_write_evidence(evidence_dir, "99_failure.png")
            if p:
                paths.append(p)
            return RpaExecutionOutput(
                success=False,
                result_summary="RPA fake: missing sku in params",
                parsed_result={},
                evidence_paths=paths,
                error_code="rpa_invalid_params",
                error_message="params.sku is required",
            )

        if inp.params.get("_list_detail_verify_only"):
            p_rb = _safe_write_evidence(evidence_dir, "04_detail_readback_stub.png")
            if p_rb:
                paths.append(p_rb)
            try:
                cp = float(inp.params.get("current_price"))
            except (TypeError, ValueError):
                cp = 0.0
            try:
                tp = float(inp.params.get("target_price"))
            except (TypeError, ValueError):
                tp = 0.0
            return RpaExecutionOutput(
                success=True,
                result_summary=f"Local fake list_detail verify readback stub {sku}",
                parsed_result={
                    "page_sku": sku,
                    "page_current_price": cp,
                    "page_new_price_field": tp,
                    "page_status": "loaded",
                    "page_message": "local_fake_readonly_verify",
                    "operation_result": "readonly_verify",
                    "sku": sku,
                    "old_price": cp,
                    "new_price": tp,
                    "target_price": tp,
                    "platform": inp.platform,
                    "dry_run": inp.dry_run,
                    "verify_mode": inp.verify_mode,
                },
                evidence_paths=paths,
                error_code=None,
                error_message=None,
            )

        p_after = _safe_write_evidence(evidence_dir, "03_after_action.png")
        if p_after:
            paths.append(p_after)

        summary = (
            f"Local fake RPA completed for {sku} -> {target_price} "
            f"(verify_mode={inp.verify_mode}, dry_run={inp.dry_run})"
        )
        return RpaExecutionOutput(
            success=True,
            result_summary=summary,
            parsed_result={
                "sku": sku,
                "target_price": target_price,
                "platform": inp.platform,
                "dry_run": inp.dry_run,
                "verify_mode": inp.verify_mode,
            },
            evidence_paths=paths,
            error_code=None,
            error_message=None,
        )
