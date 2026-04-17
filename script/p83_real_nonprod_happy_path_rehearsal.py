#!/usr/bin/env python3
from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import settings
from app.rpa.yingdao_runner import run_yingdao_adjust_inventory
from tools.nonprod_admin_stub.app import app as stub_app, init_db


def main() -> int:
    client = TestClient(stub_app)
    init_db()
    old_mode = settings.YINGDAO_BRIDGE_EXECUTION_MODE
    old_fail = stub_app.FAIL_MODE
    settings.YINGDAO_BRIDGE_EXECUTION_MODE = "real_nonprod_page"
    stub_app.FAIL_MODE = ""
    try:
        out = run_yingdao_adjust_inventory(
            {
                "task_id": "TASK-P83-REHEARSAL",
                "confirm_task_id": "TASK-P83-CFM-REHEARSAL",
                "provider_id": "odoo",
                "capability": "warehouse.adjust_inventory",
                "sku": "A001",
                "delta": 5,
                "old_inventory": 100,
                "target_inventory": 105,
                "client": client,
            }
        )
        print(out)
        return 0 if out.get("verify_passed") else 2
    finally:
        settings.YINGDAO_BRIDGE_EXECUTION_MODE = old_mode
        stub_app.FAIL_MODE = old_fail


if __name__ == "__main__":
    raise SystemExit(main())
