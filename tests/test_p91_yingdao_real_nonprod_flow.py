from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from app.core.config import settings
from app.rpa.yingdao_runner import run_yingdao_adjust_inventory
from script.p91_yingdao_real_executor import INBOX_DIR, OUTBOX_DIR, process_one

REAL_ROOT = Path("/mnt/z/yingdao_bridge")
RUNTIME_INCOMING = REAL_ROOT / "incoming"
RUNTIME_DONE = REAL_ROOT / "done"
RUNTIME_FAILED = REAL_ROOT / "failed"


def _runtime_worker(stop: threading.Event) -> None:
    seen: set[str] = set()
    while not stop.is_set():
        for fp in sorted(RUNTIME_INCOMING.glob("*.input.json")):
            if fp.name in seen:
                continue
            seen.add(fp.name)
            payload = json.loads(fp.read_text(encoding="utf-8") or "{}")
            run_id = str(payload.get("run_id") or fp.stem.replace(".input", ""))
            out = {
                "run_id": run_id,
                "operation_result": "write_adjust_inventory",
                "verify_passed": True,
                "verify_reason": "ok",
                "page_failure_code": "",
                "failure_layer": "",
                "page_steps": [
                    "open_entry",
                    "ensure_session",
                    "search_sku",
                    "open_editor",
                    "input_inventory",
                    "submit_change",
                    "read_feedback",
                    "verify_result",
                ],
                "page_evidence_count": 0,
                "old_inventory": 100,
                "new_inventory": 105,
                "screenshot_paths": [],
            }
            (RUNTIME_DONE / f"{run_id}.done.json").write_text(
                json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        time.sleep(0.05)


def _executor_worker(stop: threading.Event) -> None:
    seen: set[str] = set()
    while not stop.is_set():
        for fp in sorted(INBOX_DIR.glob("*.input.json")):
            if fp.name in seen:
                continue
            process_one(fp)
            seen.add(fp.name)
        time.sleep(0.05)


def _clean(run_id: str) -> None:
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_INCOMING.mkdir(parents=True, exist_ok=True)
    RUNTIME_DONE.mkdir(parents=True, exist_ok=True)
    RUNTIME_FAILED.mkdir(parents=True, exist_ok=True)
    for d in (INBOX_DIR, OUTBOX_DIR, RUNTIME_INCOMING, RUNTIME_DONE, RUNTIME_FAILED):
        for p in d.glob(f"{run_id}*.json"):
            p.unlink(missing_ok=True)


def test_p91_real_executor_entry_wired_to_runtime_dirs():
    old_mode = settings.YINGDAO_BRIDGE_EXECUTION_MODE
    settings.YINGDAO_BRIDGE_EXECUTION_MODE = "real_nonprod_page"
    stop_rt = threading.Event()
    stop_ex = threading.Event()
    t_rt = threading.Thread(target=_runtime_worker, args=(stop_rt,), daemon=True)
    t_ex = threading.Thread(target=_executor_worker, args=(stop_ex,), daemon=True)
    t_rt.start()
    t_ex.start()
    try:
        run_id = "P91-T-ENTRY"
        _clean(run_id)
        out = run_yingdao_adjust_inventory(
            {
                "task_id": run_id,
                "confirm_task_id": f"CFM-{run_id}",
                "provider_id": "odoo",
                "capability": "warehouse.adjust_inventory",
                "sku": "A001",
                "warehouse": "MAIN",
                "delta": 5,
                "target_inventory": 105,
                "entry_url": "http://127.0.0.1:18081/login",
                "login_url": "http://127.0.0.1:18081/login",
                "session_mode": "cookie",
                "selectors": {},
                "evidence_dir": "/mnt/z/yingdao_bridge/evidence",
                "run_id": run_id,
            }
        )
        assert out["rpa_vendor"] == "yingdao"
        assert out["execution_backend"] == "yingdao_runtime_file_trigger"
        assert out["executor_mode"] == "real"
        assert out["rpa_runtime"] == "shadowbot"
        assert out["verify_passed"] is True
        assert out["new_inventory"] == 105
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
        stop_rt.set()
        stop_ex.set()
        t_rt.join(timeout=2)
        t_ex.join(timeout=2)
        settings.YINGDAO_BRIDGE_EXECUTION_MODE = old_mode
