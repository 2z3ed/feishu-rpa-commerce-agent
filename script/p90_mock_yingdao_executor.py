#!/usr/bin/env python3
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

INBOX_DIR = Path("tmp/yingdao_bridge/inbox")
OUTBOX_DIR = Path("tmp/yingdao_bridge/outbox")


def _load_input(fp: Path) -> dict[str, Any]:
    return json.loads(fp.read_text(encoding="utf-8") or "{}")


def _derive_new_inventory(payload: dict[str, Any]) -> tuple[int, int]:
    old_inventory = int(payload.get("old_inventory") or 100)
    target_inventory_raw = payload.get("target_inventory")
    if target_inventory_raw not in {None, "", 0, "0"}:
        new_inventory = int(target_inventory_raw)
    else:
        delta = int(payload.get("delta") or 0)
        new_inventory = old_inventory + delta
    return old_inventory, new_inventory


def _success_result(payload: dict[str, Any]) -> dict[str, Any]:
    old_inventory, new_inventory = _derive_new_inventory(payload)
    run_id = str(payload.get("run_id") or "")
    return {
        "run_id": run_id,
        "operation_result": "write_adjust_inventory",
        "verify_passed": True,
        "verify_reason": "",
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
        "old_inventory": old_inventory,
        "new_inventory": new_inventory,
        "screenshot_paths": [],
    }


def _failure_result(payload: dict[str, Any], fail_mode: str) -> dict[str, Any]:
    old_inventory, new_inventory = _derive_new_inventory(payload)
    run_id = str(payload.get("run_id") or "")
    if fail_mode == "session_invalid":
        return {
            "run_id": run_id,
            "operation_result": "write_adjust_inventory_bridge_failed",
            "verify_passed": False,
            "verify_reason": "session_invalid",
            "page_failure_code": "SESSION_INVALID",
            "failure_layer": "config",
            "page_steps": ["open_entry", "ensure_session"],
            "page_evidence_count": 0,
            "old_inventory": old_inventory,
            "new_inventory": old_inventory,
            "screenshot_paths": [],
        }
    if fail_mode == "entry_not_ready":
        return {
            "run_id": run_id,
            "operation_result": "write_adjust_inventory_bridge_failed",
            "verify_passed": False,
            "verify_reason": "entry_not_ready",
            "page_failure_code": "ENTRY_NOT_READY",
            "failure_layer": "page",
            "page_steps": ["open_entry", "ensure_session", "search_sku"],
            "page_evidence_count": 0,
            "old_inventory": old_inventory,
            "new_inventory": old_inventory,
            "screenshot_paths": [],
        }
    return _success_result(payload)


def _write_output(run_id: str, result: dict[str, Any]) -> Path:
    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    fp = OUTBOX_DIR / f"{run_id}.output.json"
    fp.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return fp


def process_one(input_fp: Path) -> Path:
    payload = _load_input(input_fp)
    run_id = str(payload.get("run_id") or input_fp.stem.replace(".input", ""))
    fail_mode = str(payload.get("fail_mode") or "").strip().lower()
    if fail_mode in {"session_invalid", "entry_not_ready"}:
        result = _failure_result(payload, fail_mode)
    else:
        result = _success_result(payload)
    result["run_id"] = run_id
    return _write_output(run_id, result)


def main() -> int:
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    processed = 0
    for fp in sorted(INBOX_DIR.glob("*.input.json")):
        process_one(fp)
        processed += 1
    print(f"processed={processed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
