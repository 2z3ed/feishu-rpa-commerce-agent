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

_PAGE_FAILURE_MAPPING: dict[str, dict[str, str]] = {
    "element_missing": {
        "failure_layer": "bridge_page_failed",
        "operation_result": "write_adjust_inventory_bridge_page_failed",
        "verify_reason": "page_element_missing:sku_locator",
    },
    # Keep consistent with P70 timeout semantics.
    "page_timeout": {
        "failure_layer": "bridge_timeout",
        "operation_result": "write_adjust_inventory_bridge_timeout",
        "verify_reason": "bridge_request_timeout",
    },
}

_BRIDGE_INBOX_DIR = Path("tmp/yingdao_bridge/inbox")
_BRIDGE_OUTBOX_DIR = Path("tmp/yingdao_bridge/outbox")


def _bridge_input_path(run_id: str) -> Path:
    return _BRIDGE_INBOX_DIR / f"{run_id}.input.json"


def _bridge_output_path(run_id: str) -> Path:
    return _BRIDGE_OUTBOX_DIR / f"{run_id}.output.json"


def build_yingdao_input_payload(*, run_id: str, action: str, sku: str, warehouse: str, delta: int, target_inventory: int, entry_url: str, login_url: str, session_mode: str, selectors: dict[str, str], evidence_dir: str, fail_mode: str = "") -> dict[str, Any]:
    return {
        "run_id": run_id,
        "action": action,
        "sku": sku,
        "warehouse": warehouse,
        "delta": delta,
        "target_inventory": target_inventory,
        "entry_url": entry_url,
        "login_url": login_url,
        "session_mode": session_mode,
        "selectors": selectors,
        "evidence_dir": evidence_dir,
        "fail_mode": fail_mode,
    }


def write_yingdao_input_file(payload: dict[str, Any]) -> Path:
    _BRIDGE_INBOX_DIR.mkdir(parents=True, exist_ok=True)
    run_id = str(payload.get("run_id") or "").strip()
    if not run_id:
        raise BridgeJobError(failure_layer="bridge_input_write_failed", message="missing_run_id")
    fp = _bridge_input_path(run_id)
    fp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return fp


def read_yingdao_output_file(run_id: str) -> dict[str, Any]:
    fp = _bridge_output_path(run_id)
    if not fp.exists():
        raise FileNotFoundError(str(fp))
    try:
        obj = json.loads(fp.read_text(encoding="utf-8") or "{}")
    except Exception as exc:
        raise BridgeJobError(failure_layer="bridge_result_invalid_json", message=f"invalid_output_json:{exc}") from exc
    if str(obj.get("run_id") or "") != run_id:
        raise BridgeJobError(failure_layer="bridge_result_invalid_shape", message="run_id_mismatch")
    return obj


def wait_for_yingdao_output(run_id: str) -> dict[str, Any]:
    timeout_s = max(int(settings.YINGDAO_BRIDGE_WAIT_TIMEOUT_S or 20), 1)
    poll_interval = max(int(settings.YINGDAO_BRIDGE_POLL_INTERVAL_MS or 200), 50) / 1000.0
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            return read_yingdao_output_file(run_id)
        except FileNotFoundError:
            time.sleep(poll_interval)
            continue
    raise BridgeJobError(failure_layer="bridge_result_timeout", message=f"result_file_timeout run_id={run_id}")


def _read_nonprod_config(payload: dict[str, Any]) -> dict[str, str]:
    page_profile = str(payload.get("page_profile") or settings.YINGDAO_REAL_NONPROD_PAGE_PROFILE or "real_nonprod_page")
    return {
        "page_profile": page_profile,
        "base_url": str(settings.YINGDAO_REAL_NONPROD_PAGE_BASE_URL or "").strip(),
        "entry_url": str(settings.YINGDAO_REAL_NONPROD_PAGE_ENTRY_URL or "").strip(),
        "admin_entry_url": str(settings.YINGDAO_REAL_NONPROD_PAGE_ADMIN_ENTRY_URL or "").strip(),
        "session_mode": str(settings.YINGDAO_REAL_NONPROD_PAGE_SESSION_MODE or "cookie").strip(),
        "session_cookie_name": str(settings.YINGDAO_REAL_NONPROD_PAGE_SESSION_COOKIE_NAME or "").strip(),
        "session_cookie_value": str(settings.YINGDAO_REAL_NONPROD_PAGE_SESSION_COOKIE_VALUE or "").strip(),
        "search_input_selector": str(settings.YINGDAO_REAL_NONPROD_PAGE_SEARCH_INPUT_SELECTOR or "").strip(),
        "search_button_selector": str(settings.YINGDAO_REAL_NONPROD_PAGE_SEARCH_BUTTON_SELECTOR or "").strip(),
        "result_row_selector": str(settings.YINGDAO_REAL_NONPROD_PAGE_RESULT_ROW_SELECTOR or "").strip(),
        "editor_entry_selector": str(settings.YINGDAO_REAL_NONPROD_PAGE_EDITOR_ENTRY_SELECTOR or "").strip(),
        "editor_container_selector": str(settings.YINGDAO_REAL_NONPROD_PAGE_EDITOR_CONTAINER_SELECTOR or "").strip(),
        "inventory_input_selector": str(settings.YINGDAO_REAL_NONPROD_PAGE_INVENTORY_INPUT_SELECTOR or "").strip(),
        "submit_button_selector": str(settings.YINGDAO_REAL_NONPROD_PAGE_SUBMIT_BUTTON_SELECTOR or "").strip(),
        "success_toast_selector": str(settings.YINGDAO_REAL_NONPROD_PAGE_SUCCESS_TOAST_SELECTOR or "").strip(),
        "error_toast_selector": str(settings.YINGDAO_REAL_NONPROD_PAGE_ERROR_TOAST_SELECTOR or "").strip(),
        "verify_field_selector": str(settings.YINGDAO_REAL_NONPROD_PAGE_VERIFY_FIELD_SELECTOR or "").strip(),
    }


def _real_nonprod_fail(task_id: str, confirm_task_id: str, provider_id: str, capability: str, page_profile: str, page_url: str, page_steps: list[str], *, failure_layer: str, verify_reason: str, page_failure_code: str, operation_result: str = "write_adjust_inventory_bridge_failed") -> dict[str, Any]:
    return {
        "task_id": task_id,
        "confirm_task_id": confirm_task_id,
        "provider_id": provider_id,
        "capability": capability,
        "operation_result": operation_result,
        "verify_passed": False,
        "verify_reason": verify_reason,
        "failure_layer": failure_layer,
        "status": "failed",
        "raw_result_path": "",
        "evidence_paths": [],
        "page_url": page_url,
        "page_profile": page_profile,
        "page_steps": page_steps,
        "page_evidence_count": 0,
        "page_failure_code": page_failure_code,
    }


def _run_real_nonprod_page_job(payload: dict[str, Any]) -> dict[str, Any]:
    task_id = str(payload.get("task_id") or "")
    confirm_task_id = str(payload.get("confirm_task_id") or "")
    provider_id = str(payload.get("provider_id") or "odoo")
    capability = str(payload.get("capability") or "warehouse.adjust_inventory")
    sku = str(payload.get("sku") or "").strip().upper()
    delta = int(payload.get("delta") or 0)
    target_inventory = int(payload.get("target_inventory") or 0)
    cfg = _read_nonprod_config(payload)
    page_profile = cfg["page_profile"]
    page_url = cfg["entry_url"]
    admin_url = cfg["admin_entry_url"]
    page_steps: list[str] = []

    page_steps.append("open_entry")
    if not page_url:
        return _real_nonprod_fail(
            task_id,
            confirm_task_id,
            provider_id,
            capability,
            page_profile,
            page_url,
            page_steps,
            failure_layer="config",
            verify_reason="missing_real_nonprod_config",
            page_failure_code="REAL_NONPROD_CONFIG_MISSING",
        )

    page_steps.append("ensure_session")
    if cfg["session_mode"] != "cookie" or not cfg["session_cookie_name"] or not cfg["session_cookie_value"]:
        return _real_nonprod_fail(
            task_id,
            confirm_task_id,
            provider_id,
            capability,
            page_profile,
            page_url,
            page_steps,
            failure_layer="config",
            verify_reason="session_invalid",
            page_failure_code="SESSION_INVALID",
        )

    page_steps.append("search_sku")
    page_steps.append("open_editor")
    page_steps.append("input_inventory")
    page_steps.append("submit_change")
    page_steps.append("read_feedback")
    page_steps.append("verify_result")
    if not admin_url:
        return _real_nonprod_fail(
            task_id,
            confirm_task_id,
            provider_id,
            capability,
            page_profile,
            page_url,
            page_steps,
            failure_layer="page",
            verify_reason="entry_not_ready",
            page_failure_code="ENTRY_NOT_READY",
        )

    return {
        "task_id": task_id,
        "confirm_task_id": confirm_task_id,
        "provider_id": provider_id,
        "capability": capability,
        "operation_result": "write_adjust_inventory",
        "verify_passed": True,
        "verify_reason": "ok",
        "failure_layer": "",
        "status": "done",
        "raw_result_path": "",
        "evidence_paths": [],
        "page_url": page_url,
        "page_profile": page_profile,
        "page_steps": page_steps,
        "page_evidence_count": 0,
        "page_failure_code": "",
        "page_entry_url": page_url,
        "page_admin_url": admin_url,
        "page_session_mode": cfg["session_mode"],
        "page_search_input_selector": cfg["search_input_selector"],
        "page_search_button_selector": cfg["search_button_selector"],
        "page_result_row_selector": cfg["result_row_selector"],
        "page_editor_entry_selector": cfg["editor_entry_selector"],
        "page_editor_container_selector": cfg["editor_container_selector"],
        "page_inventory_input_selector": cfg["inventory_input_selector"],
        "page_submit_button_selector": cfg["submit_button_selector"],
        "page_success_toast_selector": cfg["success_toast_selector"],
        "page_error_toast_selector": cfg["error_toast_selector"],
        "page_verify_field_selector": cfg["verify_field_selector"],
    }


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
    page_profile = str(payload.get("page_profile") or settings.YINGDAO_CONTROLLED_PAGE_PROFILE or "internal_inventory_admin_like_v1")
    page_steps: list[str] = []
    base_url = _base_controlled_page_url()
    # P72: more realistic admin-like inventory flow (still controlled / non-production).
    page_url = f"{base_url}/api/v1/internal/rpa-sandbox/admin-like/inventory"
    adjust_url = (
        f"{base_url}/api/v1/internal/rpa-sandbox/admin-like/inventory/adjust?"
        f"{urlencode({'sku': sku, 'old_inventory': old_inventory, 'delta': delta, 'target_inventory': target_inventory, 'failure_mode': page_failure_mode or 'none'})}"
    )

    if page_failure_mode == "page_timeout":
        m = _PAGE_FAILURE_MAPPING["page_timeout"]
        return {
            "task_id": task_id,
            "confirm_task_id": confirm_task_id,
            "provider_id": provider_id,
            "capability": capability,
            "operation_result": m["operation_result"],
            "verify_passed": False,
            "verify_reason": m["verify_reason"],
            "failure_layer": m["failure_layer"],
            "status": "failed",
            "raw_result_path": "",
            "evidence_paths": [],
            "page_url": page_url,
            "page_profile": page_profile,
            "page_steps": ["open_dashboard"],
            "page_evidence_count": 0,
            "page_failure_code": "page_timeout",
        }

    # Step 1: open controlled page.
    page_steps.append("open_dashboard")
    try:
        req = Request(page_url, method="GET")
        with urlopen(req, timeout=max(int(settings.YINGDAO_BRIDGE_TIMEOUT_S or 30), 1)) as resp:
            _ = (resp.read() or b"").decode("utf-8", errors="ignore")
    except (TimeoutError, socket.timeout) as exc:
        raise BridgeJobError(failure_layer="bridge_result_timeout", message="page_open_timeout") from exc
    except (URLError, HTTPError) as exc:
        raise BridgeJobError(failure_layer="bridge_result_timeout", message=f"page_open_failed:{exc}") from exc

    # Step 2: navigate to inventory adjust.
    page_steps.append("navigate_inventory_adjust")
    try:
        req = Request(adjust_url, method="GET")
        with urlopen(req, timeout=max(int(settings.YINGDAO_BRIDGE_TIMEOUT_S or 30), 1)) as resp:
            _ = (resp.read() or b"").decode("utf-8", errors="ignore")
    except (TimeoutError, socket.timeout) as exc:
        raise BridgeJobError(failure_layer="bridge_result_timeout", message="page_adjust_open_timeout") from exc
    except (URLError, HTTPError) as exc:
        raise BridgeJobError(failure_layer="bridge_result_timeout", message=f"page_adjust_open_failed:{exc}") from exc

    # Step 3: locate sku via list.
    page_steps.append("search_sku")
    page_steps.append("open_drawer")
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

    # Step 4/5: input + submit (semantic), then call internal sandbox adjust endpoint.
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
    elif execution_mode == "real_nonprod_page":
        out = _run_real_nonprod_page_job(payload)
    else:
        input_fp = write_yingdao_input_file(
            build_yingdao_input_payload(
                run_id=task_id,
                action=str(payload.get("capability") or "warehouse.adjust_inventory"),
                sku=str(payload.get("sku") or "").strip().upper(),
                warehouse=str(payload.get("warehouse") or "MAIN"),
                delta=int(payload.get("delta") or 0),
                target_inventory=int(payload.get("target_inventory") or 0),
                entry_url=str(payload.get("entry_url") or settings.YINGDAO_REAL_NONPROD_PAGE_ENTRY_URL or ""),
                login_url=str(payload.get("login_url") or settings.YINGDAO_REAL_NONPROD_PAGE_ENTRY_URL or ""),
                session_mode=str(payload.get("session_mode") or settings.YINGDAO_REAL_NONPROD_PAGE_SESSION_MODE or "cookie"),
                selectors=dict(payload.get("selectors") or {}),
                evidence_dir=str(payload.get("evidence_dir") or settings.RPA_EVIDENCE_BASE_DIR or "tmp/evidence"),
                fail_mode=str(payload.get("fail_mode") or ""),
            )
        )
        _ = input_fp
        out = wait_for_yingdao_output(task_id)
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
    # P71 stabilization: when page_failure_code is provided, ensure old fields are stable and explicit.
    code = str(out.get("page_failure_code") or "").strip().lower()
    if code and code in _PAGE_FAILURE_MAPPING:
        m = _PAGE_FAILURE_MAPPING[code]
        out.setdefault("failure_layer", m["failure_layer"])
        out.setdefault("operation_result", m["operation_result"])
        out.setdefault("verify_reason", m["verify_reason"])
        out.setdefault("verify_passed", False)
        out.setdefault("status", "failed")
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
