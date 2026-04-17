from fastapi.testclient import TestClient

from tools.nonprod_admin_stub.app import app as stub_app, init_db
from app.rpa.yingdao_runner import run_yingdao_adjust_inventory
from app.core.config import settings


def test_real_nonprod_runner_happy_path():
    client = TestClient(stub_app)
    init_db()
    old_mode = settings.YINGDAO_BRIDGE_EXECUTION_MODE
    old_fail = stub_app.FAIL_MODE
    settings.YINGDAO_BRIDGE_EXECUTION_MODE = "real_nonprod_page"
    stub_app.FAIL_MODE = ""
    try:
        out = run_yingdao_adjust_inventory(
            {
                "task_id": "TASK-P83-RUN",
                "confirm_task_id": "TASK-P83-CFM-RUN",
                "provider_id": "odoo",
                "capability": "warehouse.adjust_inventory",
                "sku": "A001",
                "delta": 5,
                "old_inventory": 100,
                "target_inventory": 105,
                "client": client,
            }
        )
        assert out["verify_passed"] is True
        assert out["operation_result"] == "write_adjust_inventory"
        assert out["page_steps"] == [
            "open_entry",
            "ensure_session",
            "search_sku",
            "open_editor",
            "input_inventory",
            "submit_change",
            "read_feedback",
            "verify_result",
        ]
    finally:
        settings.YINGDAO_BRIDGE_EXECUTION_MODE = old_mode
        stub_app.FAIL_MODE = old_fail


def test_session_invalid_and_entry_not_ready_are_still_reproducible():
    client = TestClient(stub_app)
    init_db()
    old_mode = settings.YINGDAO_BRIDGE_EXECUTION_MODE
    old_fail = stub_app.FAIL_MODE
    settings.YINGDAO_BRIDGE_EXECUTION_MODE = "real_nonprod_page"
    try:
        stub_app.FAIL_MODE = "session_invalid"
        out = run_yingdao_adjust_inventory({"task_id": "T", "confirm_task_id": "C", "provider_id": "odoo", "capability": "warehouse.adjust_inventory", "sku": "A001", "delta": 1, "old_inventory": 100, "target_inventory": 101, "client": client})
        assert out["verify_passed"] is False
        assert out["page_failure_code"] == "SESSION_INVALID"
        stub_app.FAIL_MODE = "entry_not_ready"
        out = run_yingdao_adjust_inventory({"task_id": "T2", "confirm_task_id": "C2", "provider_id": "odoo", "capability": "warehouse.adjust_inventory", "sku": "A001", "delta": 1, "old_inventory": 100, "target_inventory": 101, "client": client})
        assert out["verify_passed"] is False
        assert out["page_failure_code"] == "ENTRY_NOT_READY"
    finally:
        settings.YINGDAO_BRIDGE_EXECUTION_MODE = old_mode
        stub_app.FAIL_MODE = old_fail
