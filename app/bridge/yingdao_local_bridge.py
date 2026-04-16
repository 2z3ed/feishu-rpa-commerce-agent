from __future__ import annotations

import json
import socket
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

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
    page_url: str = ""
    page_profile: str = ""
    page_steps: list[str] = []
    page_evidence_count: int = 0
    page_failure_code: str = ""


class BridgeJobError(RuntimeError):
    def __init__(self, *, failure_layer: str, message: str):
        super().__init__(message)
        self.failure_layer = failure_layer
        self.message = message


_BRIDGE_RESULT_REQUIRED_KEYS = (
    "task_id",
    "confirm_task_id",
    "provider_id",
    "capability",
    "operation_result",
    "verify_passed",
    "verify_reason",
    "failure_layer",
    "status",
    "raw_result_path",
    "evidence_paths",
)


def _base_controlled_page_url() -> str:
    return str(settings.YINGDAO_CONTROLLED_PAGE_BASE_URL or "http://127.0.0.1:8000").rstrip("/")


def _normalize_page_failure_mode(raw: str) -> str:
    val = str(raw or "").strip().lower()
    if val in {"page_timeout", "element_missing"}:
        return val
    return ""


def _run_controlled_page_job(payload: dict[str, Any]) -> dict[str, Any]:
    task_id = str(payload.get("task_id") or "")
    confirm_task_id = str(payload.get("confirm_task_id") or "")
    provider_id = str(payload.get("provider_id") or "odoo")
    capability = str(payload.get("capability") or "warehouse.adjust_inventory")
    sku = str(payload.get("sku") or "").strip().upper()
    delta = int(payload.get("delta") or 0)
    old_inventory = int(payload.get("old_inventory") or 0)
    target_inventory = int(payload.get("target_inventory") or max(0, old_inventory + delta))
    force_verify_fail = bool(payload.get("force_verify_fail", False))
    page_failure_mode = _normalize_page_failure_mode(payload.get("page_failure_mode"))
    page_profile = str(payload.get("page_profile") or settings.YINGDAO_CONTROLLED_PAGE_PROFILE or "internal_inventory_adjust_v1")
    page_steps: list[str] = []
    base_url = _base_controlled_page_url()
    page_url = f"{base_url}/api/v1/internal/rpa-sandbox/admin-like/catalog?{urlencode({'sku': sku})}"

    if page_failure_mode == "page_timeout":
        raise BridgeJobError(failure_layer="bridge_result_timeout", message="page_timeout")

    # Step 1: open controlled page.
    page_steps.append("open_page")
    try:
        req = Request(page_url, method="GET")
        with urlopen(req, timeout=max(int(settings.YINGDAO_BRIDGE_TIMEOUT_S or 30), 1)) as resp:
            _ = (resp.read() or b"").decode("utf-8", errors="ignore")
    except (TimeoutError, socket.timeout) as exc:
        raise BridgeJobError(failure_layer="bridge_result_timeout", message="page_open_timeout") from exc
    except (URLError, HTTPError) as exc:
        raise BridgeJobError(failure_layer="bridge_result_timeout", message=f"page_open_failed:{exc}") from exc

    # Step 2: locate sku.
    page_steps.append("locate_sku")
    if page_failure_mode == "element_missing":
        return {
            "task_id": task_id,
            "confirm_task_id": confirm_task_id,
            "provider_id": provider_id,
            "capability": capability,
            "operation_result": "write_adjust_inventory_bridge_page_failed",
            "verify_passed": False,
            "verify_reason": "page_element_missing:sku_locator",
            "failure_layer": "bridge_page_failed",
            "status": "failed",
            "raw_result_path": "",
            "evidence_paths": [],
            "page_url": page_url,
            "page_profile": page_profile,
            "page_steps": page_steps,
            "page_evidence_count": 0,
            "page_failure_code": "element_missing",
        }

    # Step 3/4: input + submit by calling internal sandbox adjust endpoint.
    page_steps.append("input_delta_target_inventory")
    page_steps.append("submit")
    adjust_url = f"{base_url}/api/v1/internal/sandbox/provider/odoo/inventory/adjust?{urlencode({'sku': sku, 'delta': delta})}"
    try:
        req = Request(adjust_url, data=b"", method="POST")
        with urlopen(req, timeout=max(int(settings.YINGDAO_BRIDGE_TIMEOUT_S or 30), 1)) as resp:
            adjust_raw = (resp.read() or b"{}").decode("utf-8", errors="ignore")
            adjust_obj = json.loads(adjust_raw or "{}")
    except (TimeoutError, socket.timeout) as exc:
        raise BridgeJobError(failure_layer="bridge_result_timeout", message="page_submit_timeout") from exc
    except (URLError, HTTPError) as exc:
        raise BridgeJobError(failure_layer="bridge_result_timeout", message=f"page_submit_failed:{exc}") from exc
    except Exception as exc:
        raise BridgeJobError(failure_layer="bridge_result_invalid_json", message=f"page_submit_invalid_json:{exc}") from exc

    page_steps.append("read_page_echo")
    payload_obj = (adjust_obj or {}).get("payload") if isinstance(adjust_obj, dict) else {}
    post_inventory = int((payload_obj or {}).get("qty_after") or old_inventory)
    verify_passed = (post_inventory == target_inventory) and (not force_verify_fail)
    verify_reason = "ok" if verify_passed else f"post_inventory_mismatch expected={target_inventory} got={post_inventory}"
    if force_verify_fail:
        verify_reason = f"forced_verify_failure expected={target_inventory} got={post_inventory}"
    return {
        "task_id": task_id,
        "confirm_task_id": confirm_task_id,
        "provider_id": provider_id,
        "capability": capability,
        "operation_result": "write_adjust_inventory" if verify_passed else "write_adjust_inventory_verify_failed",
        "verify_passed": verify_passed,
        "verify_reason": verify_reason,
        "failure_layer": "" if verify_passed else "verify_failed",
        "status": "done" if verify_passed else "failed",
        "raw_result_path": "",
        "evidence_paths": [],
        "post_inventory": post_inventory,
        "page_url": page_url,
        "page_profile": page_profile,
        "page_steps": page_steps,
        "page_evidence_count": 0,
        "page_failure_code": "",
    }


def _ensure_dir(p: Path) -> None:
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        raise BridgeJobError(failure_layer="bridge_input_write_failed", message=f"ensure_dir_failed:{exc}") from exc


def _write_bridge_input(payload: dict[str, Any], input_dir: Path) -> Path:
    _ensure_dir(input_dir)
    task_id = str(payload.get("task_id") or "unknown")
    fp = input_dir / f"{task_id}.input.json"
    try:
        fp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except Exception as exc:
        raise BridgeJobError(failure_layer="bridge_input_write_failed", message=f"input_write_failed:{exc}") from exc
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
            try:
                return json.loads(done_fp.read_text(encoding="utf-8") or "{}")
            except Exception as exc:
                raise BridgeJobError(
                    failure_layer="bridge_result_invalid_json",
                    message=f"result_invalid_json:{exc}",
                ) from exc
        if fail_fp.exists():
            try:
                return json.loads(fail_fp.read_text(encoding="utf-8") or "{}")
            except Exception as exc:
                raise BridgeJobError(
                    failure_layer="bridge_result_invalid_json",
                    message=f"result_invalid_json:{exc}",
                ) from exc
        time.sleep(poll_ms / 1000.0)
    raise BridgeJobError(
        failure_layer="bridge_result_timeout",
        message=f"result_file_timeout task_id={task_id}",
    )


def run_bridge_job(payload: dict[str, Any]) -> dict[str, Any]:
    task_id = str(payload.get("task_id") or "").strip()
    if not task_id:
        raise ValueError("missing_task_id")
    execution_mode = str(settings.YINGDAO_BRIDGE_EXECUTION_MODE or "file_exchange").strip().lower()
    if execution_mode == "controlled_page":
        out = _run_controlled_page_job(payload)
    else:
        input_dir = Path(settings.YINGDAO_BRIDGE_INPUT_DIR or "tmp/yingdao_bridge/inbox")
        output_dir = Path(settings.YINGDAO_BRIDGE_OUTPUT_DIR or "tmp/yingdao_bridge/outbox")
        _write_bridge_input(payload, input_dir=input_dir)
        out = _wait_and_load_bridge_output(task_id, output_dir=output_dir)
    if not isinstance(out, dict):
        raise BridgeJobError(
            failure_layer="bridge_result_invalid_shape",
            message="result_not_object",
        )
    missing = [k for k in _BRIDGE_RESULT_REQUIRED_KEYS if k not in out]
    if missing:
        raise BridgeJobError(
            failure_layer="bridge_result_missing_fields",
            message=f"result_missing_fields:{','.join(missing)}",
        )
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
        page_url=str(out.get("page_url") or ""),
        page_profile=str(out.get("page_profile") or ""),
        page_steps=[str(x) for x in (out.get("page_steps") or [])],
        page_evidence_count=int(out.get("page_evidence_count") or 0),
        page_failure_code=str(out.get("page_failure_code") or ""),
    )


app = FastAPI(title="yingdao-local-bridge", version="0.1.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "yingdao_local_bridge"}


@app.post("/run", response_model=BridgeRunResponse)
def run(req: BridgeRunRequest):
    try:
        out = run_bridge_job(req.model_dump())
    except BridgeJobError as exc:
        raise HTTPException(status_code=500, detail=f"{exc.failure_layer}:{exc.message}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"bridge_run_failed:{exc}") from exc
    return _normalize_bridge_output(req, out)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.bridge.yingdao_local_bridge:app", host="127.0.0.1", port=17891)
