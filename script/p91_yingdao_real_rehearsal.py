#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import threading
import time
import uuid
from pathlib import Path
from urllib import request as urlrequest
from urllib.error import URLError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import settings
from script.p91_yingdao_real_executor import INBOX_DIR, OUTBOX_DIR, process_one
from app.services.feishu.idempotency import idempotency_service
from app.tasks.ingress_tasks import process_ingress_message

REAL_ROOT = Path("/mnt/z/yingdao_bridge")
RUNTIME_INCOMING = REAL_ROOT / "incoming"
RUNTIME_DONE = REAL_ROOT / "done"
RUNTIME_FAILED = REAL_ROOT / "failed"
RUNTIME_EVIDENCE = REAL_ROOT / "evidence"
NONPROD_DB = ROOT / "tools/nonprod_admin_stub/data/nonprod_stub.db"


def _new_run_id(prefix: str = "P92") -> str:
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
    for p in RUNTIME_EVIDENCE.glob(f"{run_id}*"):
        p.unlink(missing_ok=True)


def _clean_all_bridge_dirs() -> None:
    for d in (INBOX_DIR, OUTBOX_DIR, RUNTIME_INCOMING, RUNTIME_DONE, RUNTIME_FAILED):
        d.mkdir(parents=True, exist_ok=True)
        for p in d.glob("*.json"):
            p.unlink(missing_ok=True)


def _read_inventory(sku: str = "A001") -> int | None:
    if not NONPROD_DB.exists():
        return None
    con = sqlite3.connect(str(NONPROD_DB))
    try:
        row = con.execute("select inventory from inventory_items where sku=?", (sku,)).fetchone()
        return int(row[0]) if row else None
    finally:
        con.close()


def _reset_inventory(new_value: int, sku: str = "A001") -> tuple[int | None, int | None]:
    before = _read_inventory(sku)
    if NONPROD_DB.exists():
        con = sqlite3.connect(str(NONPROD_DB))
        try:
            con.execute("update inventory_items set inventory=? where sku=?", (int(new_value), sku))
            con.commit()
        finally:
            con.close()
    after = _read_inventory(sku)
    return before, after


def _simulate_runtime_worker(stop: threading.Event) -> None:
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
                "page_evidence_count": 1,
                "old_inventory": int(payload.get("old_inventory") or 100),
                "new_inventory": int(payload.get("target_inventory") or 105),
                "screenshot_paths": [str(RUNTIME_EVIDENCE / f"{run_id}-sim.png")],
            }
            (RUNTIME_EVIDENCE / f"{run_id}-sim.png").write_text("sim-evidence\n", encoding="utf-8")
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


def _enqueue_ingress_task(task_id: str, text: str, *, open_id: str, message_id: str, chat_id: str) -> None:
    # Use Celery worker path (主系统正式链路), not direct .run().
    process_ingress_message.delay(task_id, text, open_id, message_id, chat_id)


def _http_get_json(base_url: str, path: str, timeout_s: int = 10) -> tuple[int, dict | list]:
    url = base_url.rstrip("/") + path
    req = urlrequest.Request(url, headers={"accept": "application/json"})
    with urlrequest.urlopen(req, timeout=timeout_s) as resp:
        raw = resp.read().decode("utf-8")
        try:
            return resp.getcode(), json.loads(raw)
        except Exception:
            return resp.getcode(), {}


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="P92 rehearsal runner")
    p.add_argument("--mode", choices=["simulate", "real-runtime"], default="real-runtime")
    p.add_argument("--clean-all", action="store_true")
    p.add_argument("--sku", default="A001")
    p.add_argument("--old-inventory", type=int, default=100)
    p.add_argument("--delta", type=int, default=5)
    p.add_argument("--target-inventory", type=int, default=105)
    p.add_argument("--fail-mode", default="", help="session_invalid|entry_not_ready|...")
    p.add_argument("--run-id", default="")
    p.add_argument("--entry-url", default="http://127.0.0.1:18081/login")
    p.add_argument("--login-url", default="http://127.0.0.1:18081/login")
    p.add_argument("--session-mode", default="cookie")
    p.add_argument("--reset-db-inventory", type=int, default=None, help="reset A001 inventory before run")
    p.add_argument("--bridge-wait-timeout-s", type=int, default=60)
    return p


def main() -> int:
    args = _build_parser().parse_args()

    if args.clean_all:
        _clean_all_bridge_dirs()

    run_id = args.run_id.strip() or _new_run_id("P92")

    old_mode = settings.YINGDAO_BRIDGE_EXECUTION_MODE
    old_wait_timeout = settings.YINGDAO_BRIDGE_WAIT_TIMEOUT_S
    old_confirm_backend = settings.ODOO_ADJUST_INVENTORY_CONFIRM_EXECUTION_BACKEND
    settings.YINGDAO_BRIDGE_EXECUTION_MODE = "real_nonprod_page"
    settings.YINGDAO_BRIDGE_WAIT_TIMEOUT_S = max(int(args.bridge_wait_timeout_s), 1)
    settings.ODOO_ADJUST_INVENTORY_CONFIRM_EXECUTION_BACKEND = "yingdao_bridge"

    stop_executor = threading.Event()
    t_executor = threading.Thread(target=_bridge_executor_worker, args=(stop_executor,), daemon=True)

    stop_runtime: threading.Event | None = None
    t_runtime: threading.Thread | None = None
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
        before_reset = _read_inventory(args.sku)
        after_reset = before_reset
        if args.reset_db_inventory is not None:
            before_reset, after_reset = _reset_inventory(args.reset_db_inventory, args.sku)

        # Bridge file exchange uses run_id=confirm_task_id (see execute_action.py).
        # Keep original run_id for human-readable grouping, but clean both patterns.
        _clean_for_run(run_id)

        # Create orig + confirm tasks via idempotency + Celery ingress.
        ts = int(time.time())
        orig_task_id = f"TASK-P9B-ODOO-ADJ-ORIG-{run_id}"
        confirm_task_id = f"TASK-P9B-ODOO-ADJ-CFM-{run_id}"
        _clean_for_run(confirm_task_id)
        cmd_orig = f"调整 Odoo SKU {args.sku} 库存 {('+' if int(args.delta) > 0 else '')}{int(args.delta)}"
        cmd_confirm = f"确认执行 {orig_task_id}"

        # 1) idempotency create orig record (deterministic task_id)
        idempotency_service._generate_task_id = lambda: orig_task_id  # type: ignore[attr-defined]
        msg_id_1 = f"manual-p9b-orig-{uuid.uuid4().hex}"
        payload_1 = {
            "message_id": msg_id_1,
            "chat_id": "cli-manual-p9b",
            "open_id": "manual-user",
            "text": cmd_orig,
            "create_time": ts,
        }
        is_dup, _existing, new_id = idempotency_service.check_and_create(message_id=msg_id_1, raw_payload=payload_1)
        if is_dup or new_id != orig_task_id:
            raise SystemExit(f"[p9b_acceptance_failed] orig task_id mismatch dup={is_dup} got={new_id}")
        _enqueue_ingress_task(orig_task_id, cmd_orig, open_id=payload_1["open_id"], message_id=msg_id_1, chat_id=payload_1["chat_id"])

        # 2) idempotency create confirm record
        idempotency_service._generate_task_id = lambda: confirm_task_id  # type: ignore[attr-defined]
        msg_id_2 = f"manual-p9b-cfm-{uuid.uuid4().hex}"
        payload_2 = {
            "message_id": msg_id_2,
            "chat_id": "cli-manual-p9b",
            "open_id": "manual-user",
            "text": cmd_confirm,
            "create_time": ts,
        }
        is_dup2, _existing2, new_id2 = idempotency_service.check_and_create(message_id=msg_id_2, raw_payload=payload_2)
        if is_dup2 or new_id2 != confirm_task_id:
            raise SystemExit(f"[p9b_acceptance_failed] confirm task_id mismatch dup={is_dup2} got={new_id2}")
        _enqueue_ingress_task(confirm_task_id, cmd_confirm, open_id=payload_2["open_id"], message_id=msg_id_2, chat_id=payload_2["chat_id"])

        # Poll API for observable evidence.
        base_url = "http://127.0.0.1:8000"
        deadline = time.time() + 180.0
        last_err: str = ""
        out: dict = {}
        while time.time() < deadline:
            try:
                _, t_orig = _http_get_json(base_url, f"/api/v1/tasks/{orig_task_id}")
                _, t_cfm = _http_get_json(base_url, f"/api/v1/tasks/{confirm_task_id}")
                _, steps_cfm = _http_get_json(base_url, f"/api/v1/tasks/{confirm_task_id}/steps")
                status_cfm = (t_cfm or {}).get("status")
                if status_cfm in {"succeeded", "failed"}:
                    # Extract latest action_executed detail for validation
                    steps = steps_cfm if isinstance(steps_cfm, list) else []
                    action_steps = [s for s in steps if (s or {}).get("step_code") == "action_executed"]
                    detail = (action_steps[-1].get("detail") if action_steps else "") or ""
                    must = [
                        "rpa_vendor=",
                        f"run_id={confirm_task_id}",
                        "operation_result=",
                        "verify_passed=",
                        "verify_reason=",
                        "page_failure_code=",
                        "failure_layer=",
                        "page_steps=",
                        "page_evidence_count=",
                        "screenshot_paths=",
                    ]
                    for m in must:
                        if m not in detail:
                            raise RuntimeError(f"action_executed.detail missing: {m}")
                    out = {
                        "task_id": confirm_task_id,
                        "confirm_task_id": confirm_task_id,
                        "target_task_id": orig_task_id,
                        "operation_result": (t_cfm or {}).get("result_summary") or "",
                        "verify_passed": "verify_passed=true" in detail.lower(),
                        "verify_reason": "",
                        "page_failure_code": "",
                        "failure_layer": "",
                        "page_steps": "",
                        "page_evidence_count": "",
                        "screenshot_paths": "",
                        "raw_result_path": "",
                    }
                    break
                time.sleep(0.5)
            except (URLError, Exception) as e:
                last_err = str(e)
                time.sleep(0.5)
        if not out:
            raise SystemExit(f"[p9b_acceptance_failed] tasks not observable via API: {last_err}")

        after_run = _read_inventory(args.sku)
        evidence_files = sorted(str(p) for p in RUNTIME_EVIDENCE.glob(f"{confirm_task_id}*"))
        print(
            json.dumps(
                {
                    "mode": args.mode,
                    "run_id": run_id,
                    "db_inventory": {
                        "before_reset": before_reset,
                        "after_reset": after_reset,
                        "after_run": after_run,
                    },
                    "incoming_path": str(incoming_path),
                    "done_path": str(done_path),
                    "failed_path": str(failed_path),
                    "outbox_path": str(outbox_path),
                    "orig_task_id": orig_task_id,
                    "confirm_task_id": confirm_task_id,
                    "api_task_orig": f"/api/v1/tasks/{orig_task_id}",
                    "api_task_confirm": f"/api/v1/tasks/{confirm_task_id}",
                    "api_steps_confirm": f"/api/v1/tasks/{confirm_task_id}/steps",
                    "evidence_files": evidence_files,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        # Baseline check: inventory must match target (100 -> 105 by default).
        if after_run != int(args.target_inventory):
            raise SystemExit(f"[p9b_acceptance_failed] inventory mismatch got={after_run} expected={int(args.target_inventory)}")
        return 0
    finally:
        stop_executor.set()
        t_executor.join(timeout=2)
        if stop_runtime is not None:
            stop_runtime.set()
        if t_runtime is not None:
            t_runtime.join(timeout=2)
        settings.YINGDAO_BRIDGE_EXECUTION_MODE = old_mode
        settings.YINGDAO_BRIDGE_WAIT_TIMEOUT_S = old_wait_timeout
        settings.ODOO_ADJUST_INVENTORY_CONFIRM_EXECUTION_BACKEND = old_confirm_backend


if __name__ == "__main__":
    raise SystemExit(main())
