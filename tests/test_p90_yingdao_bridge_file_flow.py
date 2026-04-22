from __future__ import annotations

import threading
import time
from pathlib import Path

from app.core.config import settings
from app.rpa.yingdao_runner import run_yingdao_adjust_inventory
from script.p90_mock_yingdao_executor import INBOX_DIR, OUTBOX_DIR, process_one


def _clean_bridge_dirs(run_id: str) -> None:
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    for fp in INBOX_DIR.glob(f"{run_id}*.json"):
        fp.unlink(missing_ok=True)
    for fp in OUTBOX_DIR.glob(f"{run_id}*.json"):
        fp.unlink(missing_ok=True)


def _executor_worker(stop: threading.Event) -> None:
    seen: set[str] = set()
    while not stop.is_set():
        for fp in sorted(INBOX_DIR.glob("*.input.json")):
            if fp.name in seen:
                continue
            process_one(fp)
            seen.add(fp.name)
        time.sleep(0.02)


def test_runner_bridge_executor_success_and_failure(tmp_path):
    old_mode = settings.YINGDAO_BRIDGE_EXECUTION_MODE
    old_wait = settings.YINGDAO_BRIDGE_WAIT_TIMEOUT_S
    old_poll = settings.YINGDAO_BRIDGE_POLL_INTERVAL_MS
    settings.YINGDAO_BRIDGE_EXECUTION_MODE = "real_nonprod_page"
    settings.YINGDAO_BRIDGE_WAIT_TIMEOUT_S = 5
    settings.YINGDAO_BRIDGE_POLL_INTERVAL_MS = 50
    try:
        success_run_id = "P90-SUCCESS"
        _clean_bridge_dirs(success_run_id)
        stop = threading.Event()
        t = threading.Thread(target=_executor_worker, args=(stop,), daemon=True)
        t.start()
        out = run_yingdao_adjust_inventory(
            {
                "task_id": success_run_id,
                "confirm_task_id": "CFM-SUCCESS",
                "provider_id": "odoo",
                "capability": "warehouse.adjust_inventory",
                "sku": "A001",
                "warehouse": "MAIN",
                "delta": 5,
                "target_inventory": 105,
                "entry_url": "http://stub/login",
                "login_url": "http://stub/login",
                "session_mode": "cookie",
                "selectors": {},
                "evidence_dir": str(tmp_path / "evidence"),
                "fail_mode": "",
                "run_id": success_run_id,
            }
        )
        stop.set()
        t.join(timeout=2)
        assert out["verify_passed"] is True
        assert out["operation_result"] == "write_adjust_inventory"
        assert out["page_steps"]
        assert out["new_inventory"] == 105

        failure_run_id = "P90-FAIL"
        _clean_bridge_dirs(failure_run_id)
        stop2 = threading.Event()
        t2 = threading.Thread(target=_executor_worker, args=(stop2,), daemon=True)
        t2.start()
        out2 = run_yingdao_adjust_inventory(
            {
                "task_id": failure_run_id,
                "confirm_task_id": "CFM-FAIL",
                "provider_id": "odoo",
                "capability": "warehouse.adjust_inventory",
                "sku": "A001",
                "warehouse": "MAIN",
                "delta": 5,
                "target_inventory": 105,
                "entry_url": "http://stub/login",
                "login_url": "http://stub/login",
                "session_mode": "cookie",
                "selectors": {},
                "evidence_dir": str(tmp_path / "evidence"),
                "fail_mode": "session_invalid",
                "run_id": failure_run_id,
            }
        )
        stop2.set()
        t2.join(timeout=2)
        assert out2["verify_passed"] is False
        assert out2["verify_reason"] == "session_invalid"
        assert out2["page_failure_code"] == "SESSION_INVALID"
        assert out2["failure_layer"] == "config"
    finally:
        settings.YINGDAO_BRIDGE_EXECUTION_MODE = old_mode
        settings.YINGDAO_BRIDGE_WAIT_TIMEOUT_S = old_wait
        settings.YINGDAO_BRIDGE_POLL_INTERVAL_MS = old_poll
