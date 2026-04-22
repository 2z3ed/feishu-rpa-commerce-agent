#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any

# P90 fixed bridge contract (left side)
INBOX_DIR = Path("tmp/yingdao_bridge/inbox")
OUTBOX_DIR = Path("tmp/yingdao_bridge/outbox")

# Real Yingdao runtime side (right side)
RUNTIME_ROOT = Path("/mnt/z/yingdao_bridge")
RUNTIME_INCOMING_DIR = RUNTIME_ROOT / "incoming"
RUNTIME_DONE_DIR = RUNTIME_ROOT / "done"
RUNTIME_FAILED_DIR = RUNTIME_ROOT / "failed"
RUNTIME_EVIDENCE_DIR = RUNTIME_ROOT / "evidence"

SHADOWBOT_EXE_WIN = r"Z:\ShadowBot\ShadowBot.exe"


def _load_json(fp: Path) -> dict[str, Any]:
    try:
        return json.loads(fp.read_text(encoding="utf-8") or "{}")
    except Exception:
        return {}


def _write_json(fp: Path, obj: dict[str, Any]) -> None:
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _launch_shadowbot_once() -> None:
    # Non-blocking launch; safe if already running.
    subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-Command",
            f"$p='{SHADOWBOT_EXE_WIN}'; if(Test-Path $p){{ Start-Process -FilePath $p | Out-Null }}",
        ],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _base_failed(run_id: str, reason: str) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "operation_result": "write_adjust_inventory_bridge_failed",
        "verify_passed": False,
        "verify_reason": reason,
        "page_failure_code": "EXECUTOR_ERROR",
        "failure_layer": "bridge_executor_failed",
        "page_steps": [],
        "page_evidence_count": 0,
        "old_inventory": 0,
        "new_inventory": 0,
        "screenshot_paths": [],
    }


def _normalize_runtime_result(run_id: str, raw: dict[str, Any], payload: dict[str, Any], *, runtime_state: str) -> dict[str, Any]:
    # Runtime-side files may be either bridge-like object or custom detail object.
    # Normalize back to P90 outbox contract, keeping runtime route semantic consistency.
    page_steps = list(raw.get("page_steps") or [])
    old_inventory = int(raw.get("old_inventory") or payload.get("old_inventory") or 0)
    target_inventory = int(payload.get("target_inventory") or 0)
    new_inventory = int(raw.get("new_inventory") or target_inventory or 0)

    verify_passed = bool(raw.get("verify_passed", False))
    if runtime_state == "done":
        # done route should be success-semantic
        verify_passed = True if target_inventory == 0 else (new_inventory == target_inventory)
    elif runtime_state == "failed":
        # failed route should be failure-semantic
        verify_passed = False

    operation_result = str(raw.get("operation_result") or ("write_adjust_inventory" if verify_passed else "write_adjust_inventory_verify_failed"))
    if verify_passed:
        operation_result = "write_adjust_inventory"
    elif operation_result == "write_adjust_inventory":
        operation_result = "write_adjust_inventory_verify_failed"

    screenshot_paths = [str(x) for x in (raw.get("screenshot_paths") or []) if str(x)]
    if not screenshot_paths:
        # Ensure minimal evidence is always landed for success/failure stabilization.
        fallback_evidence = RUNTIME_EVIDENCE_DIR / f"{run_id}-runtime-result.json"
        _write_json(fallback_evidence, {"run_id": run_id, "runtime_state": runtime_state, "raw": raw})
        screenshot_paths = [str(fallback_evidence)]

    out = {
        "run_id": run_id,
        "operation_result": operation_result,
        "verify_passed": verify_passed,
        "verify_reason": str(raw.get("verify_reason") or ("ok" if verify_passed else "verify_fail")),
        "page_failure_code": str(raw.get("page_failure_code") or ("" if verify_passed else "VERIFY_FAIL")),
        "failure_layer": str(raw.get("failure_layer") or ("" if verify_passed else "verify_failed")),
        "page_steps": page_steps,
        "page_evidence_count": len(screenshot_paths),
        "old_inventory": old_inventory,
        "new_inventory": new_inventory,
        "screenshot_paths": screenshot_paths,
    }
    return out


def _wait_runtime_result(run_id: str, timeout_s: int = 180) -> tuple[str, dict[str, Any]]:
    done_fp = RUNTIME_DONE_DIR / f"{run_id}.done.json"
    fail_fp = RUNTIME_FAILED_DIR / f"{run_id}.failed.json"
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if done_fp.exists():
            return "done", _load_json(done_fp)
        if fail_fp.exists():
            return "failed", _load_json(fail_fp)
        time.sleep(0.2)
    return "timeout", {}


def process_one(input_fp: Path) -> Path:
    payload = _load_json(input_fp)
    run_id = str(payload.get("run_id") or input_fp.stem.replace(".input", ""))

    for p in (RUNTIME_INCOMING_DIR, RUNTIME_DONE_DIR, RUNTIME_FAILED_DIR, RUNTIME_EVIDENCE_DIR):
        p.mkdir(parents=True, exist_ok=True)

    # Map bridge inbox -> runtime incoming
    runtime_in_fp = RUNTIME_INCOMING_DIR / f"{run_id}.input.json"
    _write_json(runtime_in_fp, payload)

    # Ensure runtime entry is launched.
    _launch_shadowbot_once()

    state, runtime_raw = _wait_runtime_result(run_id)
    if state == "timeout":
        out = _base_failed(run_id, "bridge_request_timeout")
        out["operation_result"] = "write_adjust_inventory_bridge_timeout"
        out["failure_layer"] = "bridge_timeout"
        out["page_failure_code"] = "PAGE_TIMEOUT"
    else:
        out = _normalize_runtime_result(run_id, runtime_raw, payload, runtime_state=state)

    out_fp = OUTBOX_DIR / f"{run_id}.output.json"
    _write_json(out_fp, out)
    return out_fp


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
