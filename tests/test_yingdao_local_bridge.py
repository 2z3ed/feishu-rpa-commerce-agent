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
