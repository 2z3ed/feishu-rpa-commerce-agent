import json

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
