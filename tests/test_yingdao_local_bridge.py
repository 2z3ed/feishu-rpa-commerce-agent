import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.bridge import yingdao_local_bridge as bridge_mod


def test_bridge_health():
    with TestClient(bridge_mod.app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "yingdao_local_bridge"


def test_bridge_run_response_shape(monkeypatch):
    def _fake_run(payload):
        return {
            "task_id": payload["task_id"],
            "confirm_task_id": payload["confirm_task_id"],
            "provider_id": payload["provider_id"],
            "capability": payload["capability"],
            "rpa_vendor": "yingdao",
            "operation_result": "write_adjust_inventory",
            "verify_passed": True,
            "verify_reason": "ok",
            "failure_layer": "",
            "status": "done",
            "raw_result_path": "/tmp/yingdao/result.json",
            "evidence_paths": ["/tmp/yingdao/shot.png"],
        }

    monkeypatch.setattr(bridge_mod, "run_bridge_job", _fake_run)
    req = {
        "task_id": "TASK-P7-BRIDGE-1",
        "confirm_task_id": "TASK-P7-CFM-1",
        "provider_id": "odoo",
        "capability": "warehouse.adjust_inventory",
        "sku": "A001",
        "delta": 5,
        "old_inventory": 100,
        "target_inventory": 105,
        "environment": "local_poc",
        "force_verify_fail": False,
    }
    with TestClient(bridge_mod.app) as client:
        resp = client.post("/run", data=json.dumps(req), headers={"Content-Type": "application/json"})
    assert resp.status_code == 200
    out = resp.json()
    for k in (
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
    ):
        assert k in out


def test_bridge_run_result_file_timeout(monkeypatch):
    def _fake_run(payload):  # noqa: ARG001
        raise bridge_mod.BridgeJobError(
            failure_layer="bridge_result_timeout",
            message="result_file_timeout task_id=TASK-P7-BRIDGE-TIMEOUT",
        )

    monkeypatch.setattr(bridge_mod, "run_bridge_job", _fake_run)
    req = {
        "task_id": "TASK-P7-BRIDGE-TIMEOUT",
        "confirm_task_id": "TASK-P7-CFM-TIMEOUT",
        "provider_id": "odoo",
        "capability": "warehouse.adjust_inventory",
        "sku": "A001",
        "delta": 5,
        "old_inventory": 100,
        "target_inventory": 105,
        "environment": "local_poc",
    }
    with TestClient(bridge_mod.app) as client:
        resp = client.post("/run", data=json.dumps(req), headers={"Content-Type": "application/json"})
    assert resp.status_code == 500
    assert "bridge_result_timeout" in str(resp.json().get("detail") or "")


def test_bridge_run_invalid_result_json(monkeypatch):
    def _bad_load(task_id: str, output_dir: Path):  # noqa: ARG001
        raise bridge_mod.BridgeJobError(
            failure_layer="bridge_result_invalid_json",
            message="result_invalid_json",
        )

    monkeypatch.setattr(bridge_mod, "_wait_and_load_bridge_output", _bad_load)
    try:
        bridge_mod.run_bridge_job({"task_id": "TASK-P7-BRIDGE-JSON"})
        assert False, "expected BridgeJobError"
    except bridge_mod.BridgeJobError as exc:
        assert exc.failure_layer == "bridge_result_invalid_json"


def test_bridge_run_missing_result_fields(monkeypatch):
    def _fake_wait(task_id: str, output_dir: Path):  # noqa: ARG001
        return {
            "task_id": "TASK-P7-BRIDGE-MISS",
            "confirm_task_id": "TASK-P7-CFM-MISS",
            "provider_id": "odoo",
        }

    monkeypatch.setattr(bridge_mod, "_wait_and_load_bridge_output", _fake_wait)
    try:
        bridge_mod.run_bridge_job({"task_id": "TASK-P7-BRIDGE-MISS"})
        assert False, "expected BridgeJobError"
    except bridge_mod.BridgeJobError as exc:
        assert exc.failure_layer == "bridge_result_missing_fields"


def test_bridge_input_write_failed(monkeypatch):
    def _bad_write(payload, input_dir):  # noqa: ARG001
        raise bridge_mod.BridgeJobError(
            failure_layer="bridge_input_write_failed",
            message="input_write_failed",
        )

    monkeypatch.setattr(bridge_mod, "_write_bridge_input", _bad_write)
    try:
        bridge_mod.run_bridge_job({"task_id": "TASK-P7-BRIDGE-WRITE"})
        assert False, "expected BridgeJobError"
    except bridge_mod.BridgeJobError as exc:
        assert exc.failure_layer == "bridge_input_write_failed"


def test_bridge_run_controlled_page_success(monkeypatch):
    old_mode = bridge_mod.settings.YINGDAO_BRIDGE_EXECUTION_MODE
    bridge_mod.settings.YINGDAO_BRIDGE_EXECUTION_MODE = "controlled_page"

    class _Resp:
        def __init__(self, data: str):
            self._data = data.encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return self._data

    def _fake_urlopen(req, timeout=30):  # noqa: ARG001
        url = req.full_url
        if "admin-like/catalog" in url:
            return _Resp("<html>ok</html>")
        if "inventory/adjust" in url:
            return _Resp('{"provider":"odoo","payload":{"qty_after":105}}')
        return _Resp("{}")

    monkeypatch.setattr(bridge_mod, "urlopen", _fake_urlopen)
    try:
        out = bridge_mod.run_bridge_job(
            {
                "task_id": "TASK-P71-LOCAL-BRIDGE-SUCCESS",
                "confirm_task_id": "TASK-P71-LOCAL-BRIDGE-CFM-SUCCESS",
                "provider_id": "odoo",
                "capability": "warehouse.adjust_inventory",
                "sku": "A001",
                "delta": 5,
                "old_inventory": 100,
                "target_inventory": 105,
            }
        )
    finally:
        bridge_mod.settings.YINGDAO_BRIDGE_EXECUTION_MODE = old_mode

    assert out["operation_result"] == "write_adjust_inventory"
    assert out["verify_passed"] is True
    assert out["page_profile"] == "internal_inventory_adjust_v1"
    assert out["page_steps"] == ["open_page", "locate_sku", "input_delta_target_inventory", "submit", "read_page_echo"]


def test_bridge_run_controlled_page_element_missing(monkeypatch):
    old_mode = bridge_mod.settings.YINGDAO_BRIDGE_EXECUTION_MODE
    bridge_mod.settings.YINGDAO_BRIDGE_EXECUTION_MODE = "controlled_page"

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b"<html>ok</html>"

    monkeypatch.setattr(bridge_mod, "urlopen", lambda req, timeout=30: _Resp())  # noqa: ARG005
    try:
        out = bridge_mod.run_bridge_job(
            {
                "task_id": "TASK-P71-LOCAL-BRIDGE-PFAIL",
                "confirm_task_id": "TASK-P71-LOCAL-BRIDGE-CFM-PFAIL",
                "provider_id": "odoo",
                "capability": "warehouse.adjust_inventory",
                "sku": "A001",
                "delta": 5,
                "old_inventory": 100,
                "target_inventory": 105,
                "page_failure_mode": "element_missing",
            }
        )
    finally:
        bridge_mod.settings.YINGDAO_BRIDGE_EXECUTION_MODE = old_mode

    assert out["operation_result"] == "write_adjust_inventory_bridge_page_failed"
    assert out["failure_layer"] == "bridge_page_failed"
    assert out["verify_passed"] is False
    assert out["page_failure_code"] == "element_missing"
