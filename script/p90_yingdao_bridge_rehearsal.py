#!/usr/bin/env python3
from __future__ import annotations

import threading
import time

from app.core.config import settings
from app.rpa.yingdao_runner import run_yingdao_adjust_inventory
from script.p90_mock_yingdao_executor import INBOX_DIR, process_one


def _run_once(run_id: str, fail_mode: str = "") -> dict:
    stop = threading.Event()
    inbox_fp = INBOX_DIR / f"{run_id}.input.json"

    def worker() -> None:
        while not stop.is_set():
            if inbox_fp.exists():
                process_one(inbox_fp)
                return
            time.sleep(0.02)

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    try:
        return run_yingdao_adjust_inventory(
            {
                "task_id": run_id,
                "confirm_task_id": f"CFM-{run_id}",
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
                "evidence_dir": "tmp/evidence",
                "fail_mode": fail_mode,
                "run_id": run_id,
            }
        )
    finally:
        stop.set()
        t.join(timeout=2)


def main() -> int:
    old_mode = settings.YINGDAO_BRIDGE_EXECUTION_MODE
    old_wait = settings.YINGDAO_BRIDGE_WAIT_TIMEOUT_S
    old_poll = settings.YINGDAO_BRIDGE_POLL_INTERVAL_MS
    settings.YINGDAO_BRIDGE_EXECUTION_MODE = "real_nonprod_page"
    settings.YINGDAO_BRIDGE_WAIT_TIMEOUT_S = 5
    settings.YINGDAO_BRIDGE_POLL_INTERVAL_MS = 50
    try:
        ok = _run_once("P90-REHEARSAL-SUCCESS")
        print("SUCCESS", ok["operation_result"], ok["verify_passed"], ok["verify_reason"], ok["page_failure_code"], ok["old_inventory"], ok["new_inventory"], ok["page_steps"])
        fail = _run_once("P90-REHEARSAL-FAIL", fail_mode="session_invalid")
        print("FAIL", fail["operation_result"], fail["verify_passed"], fail["verify_reason"], fail["page_failure_code"], fail["old_inventory"], fail["new_inventory"], fail["page_steps"])
        return 0 if ok.get("verify_passed") and not fail.get("verify_passed") else 2
    finally:
        settings.YINGDAO_BRIDGE_EXECUTION_MODE = old_mode
        settings.YINGDAO_BRIDGE_WAIT_TIMEOUT_S = old_wait
        settings.YINGDAO_BRIDGE_POLL_INTERVAL_MS = old_poll


if __name__ == "__main__":
    raise SystemExit(main())
