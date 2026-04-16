from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.core.config import settings


class BridgeRunRequest(BaseModel):
    task_id: str
    confirm_task_id: str
    provider_id: str
    capability: str
    sku: str
    delta: int
    old_inventory: int
    target_inventory: int
    environment: str
    force_verify_fail: bool = False


class BridgeRunResponse(BaseModel):
    task_id: str
    confirm_task_id: str
    provider_id: str
    capability: str
    rpa_vendor: str
    operation_result: str
    verify_passed: bool
    verify_reason: str
    failure_layer: str
    status: str
    raw_result_path: str
    evidence_paths: list[str]


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _write_bridge_input(payload: dict[str, Any], input_dir: Path) -> Path:
    _ensure_dir(input_dir)
    task_id = str(payload.get("task_id") or "unknown")
    fp = input_dir / f"{task_id}.input.json"
    fp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return fp


def _wait_and_load_bridge_output(task_id: str, output_dir: Path) -> dict[str, Any]:
    _ensure_dir(output_dir)
    timeout_s = max(int(settings.YINGDAO_BRIDGE_WAIT_TIMEOUT_S or 20), 1)
    poll_ms = max(int(settings.YINGDAO_BRIDGE_POLL_INTERVAL_MS or 200), 50)
    done_fp = output_dir / f"{task_id}.done.json"
    fail_fp = output_dir / f"{task_id}.failed.json"
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if done_fp.exists():
            return json.loads(done_fp.read_text(encoding="utf-8") or "{}")
        if fail_fp.exists():
            return json.loads(fail_fp.read_text(encoding="utf-8") or "{}")
        time.sleep(poll_ms / 1000.0)
    raise TimeoutError(f"bridge_wait_timeout task_id={task_id}")


def run_bridge_job(payload: dict[str, Any]) -> dict[str, Any]:
    task_id = str(payload.get("task_id") or "").strip()
    if not task_id:
        raise ValueError("missing_task_id")
    input_dir = Path(settings.YINGDAO_BRIDGE_INPUT_DIR or "tmp/yingdao_bridge/inbox")
    output_dir = Path(settings.YINGDAO_BRIDGE_OUTPUT_DIR or "tmp/yingdao_bridge/outbox")
    _write_bridge_input(payload, input_dir=input_dir)
    out = _wait_and_load_bridge_output(task_id, output_dir=output_dir)
    if not isinstance(out, dict):
        raise ValueError("invalid_bridge_output")
    return out


def _normalize_bridge_output(req: BridgeRunRequest, out: dict[str, Any]) -> BridgeRunResponse:
    return BridgeRunResponse(
        task_id=str(out.get("task_id") or req.task_id),
        confirm_task_id=str(out.get("confirm_task_id") or req.confirm_task_id),
        provider_id=str(out.get("provider_id") or req.provider_id),
        capability=str(out.get("capability") or req.capability),
        rpa_vendor="yingdao",
        operation_result=str(out.get("operation_result") or ""),
        verify_passed=bool(out.get("verify_passed", False)),
        verify_reason=str(out.get("verify_reason") or ""),
        failure_layer=str(out.get("failure_layer") or ""),
        status=str(out.get("status") or "failed"),
        raw_result_path=str(out.get("raw_result_path") or ""),
        evidence_paths=[str(x) for x in (out.get("evidence_paths") or [])],
    )


app = FastAPI(title="yingdao-local-bridge", version="0.1.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "yingdao_local_bridge"}


@app.post("/run", response_model=BridgeRunResponse)
def run(req: BridgeRunRequest):
    try:
        out = run_bridge_job(req.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"bridge_run_failed:{exc}") from exc
    return _normalize_bridge_output(req, out)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.bridge.yingdao_local_bridge:app", host="127.0.0.1", port=17891)
