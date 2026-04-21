#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import settings
from app.rpa.yingdao_runner import run_yingdao_adjust_inventory
from script.p91_yingdao_real_executor import INBOX_DIR, OUTBOX_DIR, process_one

REAL_ROOT = Path("/mnt/z/yingdao_bridge")
RUNTIME_INCOMING = REAL_ROOT / "incoming"
RUNTIME_DONE = REAL_ROOT / "done"
RUNTIME_FAILED = REAL_ROOT / "failed"
RUNTIME_EVIDENCE = REAL_ROOT / "evidence"


def _new_run_id(prefix: str = "P91") -> str:
    return f"{prefix}-{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}"


def _clean_for_run(run_id: str) -> None:
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    for d in (RUNTIME_INCOMING, RUNTIME_DONE, RUNTIME_FAILED, RUNTIME_EVIDENCE):
        d.mkdir(parents=True, exist_ok=True)

    for p in INBOX_DIR.glob(f"{run_id}*.json"):
        p.unlink(missing_ok=True)
    for p in OUTBOX_DIR.glob(f"{run_id}*.json"):
        p.unlink(missing_ok=True)
    for p in RUNTIME_INCOMING.glob(f"{run_id}*.json"):
        p.unlink(missing_ok=True)
    for p in RUNTIME_DONE.glob(f"{run_id}*.json"):
        p.unlink(missing_ok=True)
    for p in RUNTIME_FAILED.glob(f"{run_id}*.json"):
        p.unlink(missing_ok=True)


def _clean_all_bridge_dirs() -> None:
    for d in (INBOX_DIR, OUTBOX_DIR, RUNTIME_INCOMING, RUNTIME_DONE, RUNTIME_FAILED):
        d.mkdir(parents=True, exist_ok=True)
        for p in d.glob("*.json"):
            p.unlink(missing_ok=True)


def _simulate_runtime_worker(stop: threading.Event) -> None:
    """Simulate runtime: consume incoming and write done."""
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
                "old_inventory": int(payload.get("old_inventory") or 100),
                "new_inventory": int(payload.get("target_inventory") or 105),
                "screenshot_paths": [],
            }
            (RUNTIME_DONE / f"{run_id}.done.json").write_text(
                json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        time.sleep(0.1)


def _bridge_executor_worker(stop: threading.Event) -> None:
    seen: set[str] = set()
    while not stop.is_set():
        for fp in sorted(INBOX_DIR.glob("*.input.json")):
            if fp.name in seen:
                continue
            process_one(fp)
            seen.add(fp.name)
        time.sleep(0.05)


def _run_one(run_id: str) -> dict:
    _clean_for_run(run_id)
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
            "entry_url": "http://127.0.0.1:18081/login",
            "login_url": "http://127.0.0.1:18081/login",
            "session_mode": "cookie",
            "selectors": {},
            "evidence_dir": str(RUNTIME_EVIDENCE),
            "run_id": run_id,
        }
    )


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="P91 rehearsal runner")
    p.add_argument(
        "--mode",
        choices=["simulate", "real-runtime"],
        default="real-runtime",
        help="simulate: start simulated runtime worker; real-runtime: no simulation worker",
    )
    p.add_argument(
        "--clean-all",
        action="store_true",
        help="clean stale *.json in incoming/done/failed/outbox/inbox before run",
    )
    return p


def main() -> int:
    args = _build_parser().parse_args()

    if args.clean_all:
        _clean_all_bridge_dirs()

    run_id = _new_run_id("P91")

    old_mode = settings.YINGDAO_BRIDGE_EXECUTION_MODE
    settings.YINGDAO_BRIDGE_EXECUTION_MODE = "real_nonprod_page"

    stop_executor = threading.Event()
    t_executor = threading.Thread(target=_bridge_executor_worker, args=(stop_executor,), daemon=True)

    stop_runtime: threading.Event | None = None
    t_runtime: threading.Thread | None = None

    # Important split:
    # - simulate mode: start simulate runtime worker
    # - real-runtime mode: DO NOT start simulate runtime worker
    if args.mode == "simulate":
        stop_runtime = threading.Event()
        t_runtime = threading.Thread(target=_simulate_runtime_worker, args=(stop_runtime,), daemon=True)

    t_executor.start()
    if t_runtime is not None:
        t_runtime.start()

    incoming_path = RUNTIME_INCOMING / f"{run_id}.input.json"
    done_path = RUNTIME_DONE / f"{run_id}.done.json"
    failed_path = RUNTIME_FAILED / f"{run_id}.failed.json"
    outbox_path = OUTBOX_DIR / f"{run_id}.output.json"

    try:
        out = _run_one(run_id)
        print(
            json.dumps(
                {
                    "mode": args.mode,
                    "run_id": run_id,
                    "incoming_path": str(incoming_path),
                    "done_path": str(done_path),
                    "failed_path": str(failed_path),
                    "outbox_path": str(outbox_path),
                    "task_id": out.get("task_id"),
                    "rpa_vendor": out.get("rpa_vendor"),
                    "execution_backend": out.get("execution_backend"),
                    "executor_mode": out.get("executor_mode"),
                    "rpa_runtime": out.get("rpa_runtime"),
                    "operation_result": out.get("operation_result"),
                    "verify_passed": out.get("verify_passed"),
                    "page_steps": out.get("page_steps"),
                    "raw_result_path": out.get("raw_result_path"),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0 if out.get("operation_result") else 2
    finally:
        stop_executor.set()
        t_executor.join(timeout=2)
        if stop_runtime is not None:
            stop_runtime.set()
        if t_runtime is not None:
            t_runtime.join(timeout=2)
        settings.YINGDAO_BRIDGE_EXECUTION_MODE = old_mode


if __name__ == "__main__":
    raise SystemExit(main())
