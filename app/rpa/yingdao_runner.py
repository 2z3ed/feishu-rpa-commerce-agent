from __future__ import annotations

import json
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from http.cookiejar import CookieJar
from typing import Any

from app.bridge.yingdao_local_bridge import (
    build_yingdao_input_payload,
    read_yingdao_output_file,
    wait_for_yingdao_output,
    write_yingdao_input_file,
)
from app.core.config import settings


class YingdaoBridgeError(RuntimeError):
    def __init__(self, *, failure_layer: str, operation_result: str, verify_reason: str):
        super().__init__(verify_reason)
        self.failure_layer = failure_layer
        self.operation_result = operation_result
        self.verify_reason = verify_reason


_BRIDGE_REQUIRED_KEYS = (
    "task_id",
    "confirm_task_id",
    "provider_id",
    "capability",
    "rpa_vendor",
    "operation_result",
    "verify_passed",
    "verify_reason",
    "failure_layer",
    "status",
    "raw_result_path",
    "evidence_paths",
)


def _run_real_nonprod_stub_flow(payload: dict[str, Any], client: Any | None = None) -> dict[str, Any]:
    def _http_get(path: str, *, params: dict[str, Any] | None = None) -> str:
        if client is not None:
            resp = client.get(path, params=params)
            return resp.text
        base_url = str(settings.YINGDAO_REAL_NONPROD_PAGE_BASE_URL or "http://127.0.0.1:18081").rstrip("/")
        url = f"{base_url}{path}"
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        opener = urllib.request.build_opener()
        req = urllib.request.Request(url, method="GET")
        with opener.open(req, timeout=max(int(settings.YINGDAO_BRIDGE_TIMEOUT_S or 30), 1)) as resp:
            return resp.read().decode("utf-8", errors="ignore")

    def _http_post(path: str, *, data: dict[str, str]) -> str:
        if client is not None:
            resp = client.post(path, data=data)
            return resp.text
        base_url = str(settings.YINGDAO_REAL_NONPROD_PAGE_BASE_URL or "http://127.0.0.1:18081").rstrip("/")
        url = f"{base_url}{path}"
        opener = urllib.request.build_opener()
        body = urllib.parse.urlencode(data).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
        with opener.open(req, timeout=max(int(settings.YINGDAO_BRIDGE_TIMEOUT_S or 30), 1)) as resp:
            return resp.read().decode("utf-8", errors="ignore")

    task_id = str(payload.get("task_id") or "")
    task_id = str(payload.get("task_id") or "")
    confirm_task_id = str(payload.get("confirm_task_id") or "")
    provider_id = str(payload.get("provider_id") or "odoo")
    capability = str(payload.get("capability") or "warehouse.adjust_inventory")
    sku = str(payload.get("sku") or "A001").strip().upper()
    delta = int(payload.get("delta") or 0)
    target_inventory = int(payload.get("target_inventory") or 0)
    entry_url = str(settings.YINGDAO_REAL_NONPROD_PAGE_ENTRY_URL or "/login").strip()
    admin_url = str(settings.YINGDAO_REAL_NONPROD_PAGE_ADMIN_ENTRY_URL or "/admin").strip()
    page_steps = ["open_entry"]

    if not entry_url:
        return {
            "task_id": task_id,
            "confirm_task_id": confirm_task_id,
            "provider_id": provider_id,
            "capability": capability,
            "operation_result": "write_adjust_inventory_bridge_failed",
            "verify_passed": False,
            "verify_reason": "missing_real_nonprod_config",
            "failure_layer": "config",
            "status": "failed",
            "raw_result_path": "",
            "evidence_paths": [],
            "page_url": "",
            "page_profile": "real_nonprod_page",
            "page_steps": page_steps,
            "page_evidence_count": 0,
            "page_failure_code": "REAL_NONPROD_CONFIG_MISSING",
        }

    login_html = _http_get("/login")
    if not login_html:
        return {
            "task_id": task_id,
            "confirm_task_id": confirm_task_id,
            "provider_id": provider_id,
            "capability": capability,
            "operation_result": "write_adjust_inventory_bridge_failed",
            "verify_passed": False,
            "verify_reason": "page_entry_missing",
            "failure_layer": "page",
            "status": "failed",
            "raw_result_path": "",
            "evidence_paths": [],
            "page_url": entry_url,
            "page_profile": "real_nonprod_page",
            "page_steps": page_steps,
            "page_evidence_count": 0,
            "page_failure_code": "ENTRY_NOT_READY",
        }

    page_steps.append("ensure_session")
    login_resp = _http_post("/login", data={"username": "admin", "password": "admin123", "next": "/admin"})
    if "登录失败" in login_resp:
        return {
            "task_id": task_id,
            "confirm_task_id": confirm_task_id,
            "provider_id": provider_id,
            "capability": capability,
            "operation_result": "write_adjust_inventory_bridge_failed",
            "verify_passed": False,
            "verify_reason": "session_invalid",
            "failure_layer": "config",
            "status": "failed",
            "raw_result_path": "",
            "evidence_paths": [],
            "page_url": entry_url,
            "page_profile": "real_nonprod_page",
            "page_steps": page_steps,
            "page_evidence_count": 0,
            "page_failure_code": "SESSION_INVALID",
        }

    page_steps.append("search_sku")
    admin_html = _http_get("/admin")
    if "库存中心" not in admin_html:
        return {
            "task_id": task_id,
            "confirm_task_id": confirm_task_id,
            "provider_id": provider_id,
            "capability": capability,
            "operation_result": "write_adjust_inventory_bridge_failed",
            "verify_passed": False,
            "verify_reason": "entry_not_ready",
            "failure_layer": "page",
            "status": "failed",
            "raw_result_path": "",
            "evidence_paths": [],
            "page_url": admin_url,
            "page_profile": "real_nonprod_page",
            "page_steps": page_steps,
            "page_evidence_count": 0,
            "page_failure_code": "ENTRY_NOT_READY",
        }

    inventory_path = "/admin/inventory"
    inventory_html = _http_get(inventory_path, params={"sku": sku})
    if sku not in inventory_html:
        return {
            "task_id": task_id,
            "confirm_task_id": confirm_task_id,
            "provider_id": provider_id,
            "capability": capability,
            "operation_result": "write_adjust_inventory_bridge_page_failed",
            "verify_passed": False,
            "verify_reason": "element_missing",
            "failure_layer": "bridge_page_failed",
            "status": "failed",
            "raw_result_path": "",
            "evidence_paths": [],
            "page_url": inventory_url,
            "page_profile": "real_nonprod_page",
            "page_steps": page_steps,
            "page_evidence_count": 0,
            "page_failure_code": "ELEMENT_MISSING",
        }

    page_steps.append("open_editor")
    adjust_path = "/admin/inventory/adjust"
    adjust_html = _http_get(adjust_path, params={"sku": sku})
    if "库存调整" not in adjust_html:
        return {
            "task_id": task_id,
            "confirm_task_id": confirm_task_id,
            "provider_id": provider_id,
            "capability": capability,
            "operation_result": "write_adjust_inventory_bridge_page_failed",
            "verify_passed": False,
            "verify_reason": "element_missing",
            "failure_layer": "bridge_page_failed",
            "status": "failed",
            "raw_result_path": "",
            "evidence_paths": [],
            "page_url": adjust_url,
            "page_profile": "real_nonprod_page",
            "page_steps": page_steps,
            "page_evidence_count": 0,
            "page_failure_code": "ELEMENT_MISSING",
        }

    page_steps.extend(["input_inventory", "submit_change", "read_feedback", "verify_result"])
    new_inventory = target_inventory if target_inventory else 100 + delta
    submit_resp = _http_post(
        "/admin/inventory/adjust",
        data={"sku": sku, "delta": str(delta), "target_inventory": str(new_inventory)},
    )
    if "提交成功" not in submit_resp:
        return {
            "task_id": task_id,
            "confirm_task_id": confirm_task_id,
            "provider_id": provider_id,
            "capability": capability,
            "operation_result": "write_adjust_inventory_verify_failed",
            "verify_passed": False,
            "verify_reason": "verify_fail",
            "failure_layer": "verify_failed",
            "status": "failed",
            "raw_result_path": "",
            "evidence_paths": [],
            "page_url": adjust_url,
            "page_profile": "real_nonprod_page",
            "page_steps": page_steps,
            "page_evidence_count": 0,
            "page_failure_code": "VERIFY_FAIL",
        }

    verify_html = _http_get(inventory_path, params={"sku": sku})
    matched = str(new_inventory) in verify_html or f"new_inventory={new_inventory}" in verify_html
    return {
        "task_id": task_id,
        "confirm_task_id": confirm_task_id,
        "provider_id": provider_id,
        "capability": capability,
        "operation_result": "write_adjust_inventory" if matched else "write_adjust_inventory_verify_failed",
        "verify_passed": matched,
        "verify_reason": "ok" if matched else "verify_fail",
        "failure_layer": "" if matched else "verify_failed",
        "status": "done" if matched else "failed",
        "raw_result_path": "",
        "evidence_paths": [],
        "page_url": inventory_url,
        "page_profile": "real_nonprod_page",
        "page_steps": page_steps,
        "page_evidence_count": 0,
        "page_failure_code": "" if matched else "VERIFY_FAIL",
    }


def run_yingdao_adjust_inventory(payload: dict[str, Any]) -> dict[str, Any]:
    """Call local Yingdao bridge and return normalized result."""
    execution_mode = str(settings.YINGDAO_BRIDGE_EXECUTION_MODE or "").strip().lower()
    if execution_mode == "real_nonprod_page":
        run_id = str(payload.get("run_id") or payload.get("task_id") or "").strip()
        if not run_id:
            run_id = str(payload.get("confirm_task_id") or "").strip() or "run-unknown"
        bridge_payload = build_yingdao_input_payload(
            run_id=run_id,
            action="warehouse.adjust_inventory",
            sku=str(payload.get("sku") or "").strip().upper(),
            warehouse=str(payload.get("warehouse") or "MAIN").strip(),
            delta=int(payload.get("delta") or 0),
            target_inventory=int(payload.get("target_inventory") or 0),
            entry_url=str(payload.get("entry_url") or settings.YINGDAO_REAL_NONPROD_PAGE_ENTRY_URL or "").strip(),
            login_url=str(payload.get("login_url") or settings.YINGDAO_REAL_NONPROD_PAGE_ENTRY_URL or "").strip(),
            session_mode=str(payload.get("session_mode") or settings.YINGDAO_REAL_NONPROD_PAGE_SESSION_MODE or "cookie").strip(),
            selectors=dict(payload.get("selectors") or {
                "search_input_selector": settings.YINGDAO_REAL_NONPROD_PAGE_SEARCH_INPUT_SELECTOR,
                "search_button_selector": settings.YINGDAO_REAL_NONPROD_PAGE_SEARCH_BUTTON_SELECTOR,
                "result_row_selector": settings.YINGDAO_REAL_NONPROD_PAGE_RESULT_ROW_SELECTOR,
                "editor_entry_selector": settings.YINGDAO_REAL_NONPROD_PAGE_EDITOR_ENTRY_SELECTOR,
                "editor_container_selector": settings.YINGDAO_REAL_NONPROD_PAGE_EDITOR_CONTAINER_SELECTOR,
                "inventory_input_selector": settings.YINGDAO_REAL_NONPROD_PAGE_INVENTORY_INPUT_SELECTOR,
                "submit_button_selector": settings.YINGDAO_REAL_NONPROD_PAGE_SUBMIT_BUTTON_SELECTOR,
                "success_toast_selector": settings.YINGDAO_REAL_NONPROD_PAGE_SUCCESS_TOAST_SELECTOR,
                "error_toast_selector": settings.YINGDAO_REAL_NONPROD_PAGE_ERROR_TOAST_SELECTOR,
                "verify_field_selector": settings.YINGDAO_REAL_NONPROD_PAGE_VERIFY_FIELD_SELECTOR,
            }),
            evidence_dir=str(payload.get("evidence_dir") or "tmp/evidence"),
            fail_mode=str(payload.get("fail_mode") or payload.get("page_failure_mode") or "").strip(),
        )
        write_yingdao_input_file(bridge_payload)
        out = wait_for_yingdao_output(run_id)
        _ = read_yingdao_output_file(run_id)
        return {
            "task_id": str(payload.get("task_id") or run_id),
            "confirm_task_id": str(payload.get("confirm_task_id") or ""),
            "provider_id": str(payload.get("provider_id") or "odoo"),
            "capability": str(payload.get("capability") or "warehouse.adjust_inventory"),
            "rpa_vendor": "yingdao",
            "execution_backend": "yingdao_runtime_file_trigger",
            "executor_mode": "real",
            "rpa_runtime": "shadowbot",
            "operation_result": str(out.get("operation_result") or "write_adjust_inventory_bridge_failed"),
            "verify_passed": bool(out.get("verify_passed")),
            "verify_reason": str(out.get("verify_reason") or ""),
            "failure_layer": str(out.get("failure_layer") or ""),
            "status": "done" if out.get("verify_passed") else "failed",
            "raw_result_path": str((Path("tmp/yingdao_bridge/outbox") / f"{run_id}.output.json").as_posix()),
            "evidence_paths": [],
            "page_url": str(payload.get("entry_url") or settings.YINGDAO_REAL_NONPROD_PAGE_ENTRY_URL or ""),
            "page_profile": "real_nonprod_page",
            "page_steps": list(out.get("page_steps") or []),
            "page_evidence_count": int(out.get("page_evidence_count") or 0),
            "page_failure_code": str(out.get("page_failure_code") or ""),
            "old_inventory": int(out.get("old_inventory") or payload.get("old_inventory") or 0),
            "new_inventory": int(out.get("new_inventory") or payload.get("target_inventory") or 0),
            "screenshot_paths": list(out.get("screenshot_paths") or []),
        }
    base_url = str(settings.YINGDAO_BRIDGE_BASE_URL or "http://127.0.0.1:17891").rstrip("/")
    req = urllib.request.Request(
        f"{base_url}/run",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
