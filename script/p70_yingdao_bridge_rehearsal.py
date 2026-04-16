#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import socket
import urllib.error
import urllib.request


SAMPLE_PRESETS = {
    "success": {
        "task_id": "TASK-P70-REHEARSAL-SUCCESS-1",
        "confirm_task_id": "TASK-P70-REHEARSAL-SUCCESS-CFM-1",
        "force_verify_fail": False,
        "expected": {
            "operation_result": "write_adjust_inventory",
            "verify_passed": True,
            "failure_layer": "",
        },
    },
    "timeout": {
        "task_id": "TASK-P70-REHEARSAL-TIMEOUT-1",
        "confirm_task_id": "TASK-P70-REHEARSAL-TIMEOUT-CFM-1",
        "force_verify_fail": False,
        "page_failure_mode": "page_timeout",
        "expected": {
            "operation_result": "write_adjust_inventory_bridge_timeout",
            "verify_passed": False,
            "failure_layer": "bridge_timeout",
        },
    },
    "page_failure": {
        "task_id": "TASK-P71-REHEARSAL-PFAIL-1",
        "confirm_task_id": "TASK-P71-REHEARSAL-PFAIL-CFM-1",
        "force_verify_fail": False,
        "page_failure_mode": "element_missing",
        "expected": {
            "operation_result": "write_adjust_inventory_bridge_page_failed",
            "verify_passed": False,
            "failure_layer": "bridge_page_failed",
        },
    },
    "verify_fail": {
        "task_id": "TASK-P70-REHEARSAL-VFAIL-1",
        "confirm_task_id": "TASK-P70-REHEARSAL-VFAIL-CFM-1",
        "force_verify_fail": True,
        "page_failure_mode": "",
        "expected": {
            "operation_result": "write_adjust_inventory_verify_failed",
            "verify_passed": False,
            "failure_layer": "verify_failed",
        },
    },
}


def _build_payload(args) -> dict:
    preset = SAMPLE_PRESETS[str(args.sample)]
    return {
        "task_id": str(args.task_id or preset["task_id"]),
        "confirm_task_id": str(args.confirm_task_id or preset["confirm_task_id"]),
        "provider_id": "odoo",
        "capability": "warehouse.adjust_inventory",
        "sku": str(args.sku),
        "delta": int(args.delta),
        "old_inventory": int(args.old_inventory),
        "target_inventory": int(args.target_inventory),
        "environment": str(args.environment),
        "force_verify_fail": bool(args.force_verify_fail or preset["force_verify_fail"]),
        "page_failure_mode": str(args.page_failure_mode or preset.get("page_failure_mode") or ""),
        "page_profile": str(args.page_profile),
    }


def _bridge_call(base_url: str, payload: dict) -> tuple[dict, str]:
    req = urllib.request.Request(
        f"{str(base_url).rstrip('/')}/run",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads((resp.read() or b"{}").decode("utf-8")), ""
    except urllib.error.HTTPError as exc:
        return {}, f"bridge_http_error:{exc.code}"
    except (TimeoutError, socket.timeout):
        return {}, "bridge_timeout"
    except urllib.error.URLError as exc:
        return {}, f"bridge_unreachable:{exc.reason}"


def _governance_alignment(result: dict) -> dict:
    op = str(result.get("operation_result") or "")
    fl = str(result.get("failure_layer") or "")
    vp = bool(result.get("verify_passed", False))
    if op == "write_adjust_inventory" and vp:
        return {"sample_bucket": "success", "p62_view": "verify_pass_count", "gate_status": "allow", "gate_reason": "allow"}
    if "timeout" in op or fl == "bridge_timeout":
        return {"sample_bucket": "timeout_failure", "p62_view": "other_failed_confirms", "gate_status": "allow", "gate_reason": "allow"}
    if op == "write_adjust_inventory_verify_failed" or fl == "verify_failed":
        return {"sample_bucket": "verify_failure", "p62_view": "verify_fail_count", "gate_status": "allow", "gate_reason": "allow"}
    return {"sample_bucket": "unclassified", "p62_view": "manual_review", "gate_status": "allow", "gate_reason": "allow"}


def build_task_id_replay_report(*, task_id: str, base_url: str, payload: dict) -> dict:
    """Minimal single-sample replay report for manual verification.

    This does NOT read DB or /steps. It prints a deterministic structure that humans can compare
    against `/tasks/{confirm_task_id}/steps` (action_executed.detail).
    """
    out, call_error = _bridge_call(base_url, payload)
    actual = {
        "task_id": out.get("task_id"),
        "confirm_task_id": out.get("confirm_task_id"),
        "operation_result": out.get("operation_result"),
        "verify_passed": out.get("verify_passed"),
        "verify_reason": out.get("verify_reason"),
        "failure_layer": out.get("failure_layer"),
        "raw_result_path": out.get("raw_result_path"),
        "evidence_paths": out.get("evidence_paths"),
        "rpa_vendor": out.get("rpa_vendor"),
        "page_url": out.get("page_url"),
        "page_profile": out.get("page_profile"),
        "page_steps": out.get("page_steps"),
        "page_evidence_count": out.get("page_evidence_count"),
        "page_failure_code": out.get("page_failure_code"),
    }
    return {
        "mode": "task_id_replay",
        "task_id": task_id,
        "payload": payload,
        "bridge_call_error": call_error,
        "actual": actual,
        "page_evidence_summary": {
            "page_profile": actual.get("page_profile"),
            "page_failure_code": actual.get("page_failure_code"),
            "page_steps_count": len(actual.get("page_steps") or []) if isinstance(actual.get("page_steps"), list) else 0,
            "page_evidence_count": actual.get("page_evidence_count"),
            "raw_result_path_present": bool(actual.get("raw_result_path")),
        },
        "steps_checklist": [
            "operation_result",
            "verify_passed",
            "verify_reason",
            "failure_layer",
            "raw_result_path",
            "rpa_vendor",
            "confirm_task_id",
            "target_task_id",
            "page_url",
            "page_profile",
            "page_steps",
            "page_evidence_count",
            "page_failure_code",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="P7.0 local Yingdao bridge rehearsal")
    parser.add_argument("--base-url", default="http://127.0.0.1:17891")
    parser.add_argument("--sample", choices=("success", "timeout", "page_failure", "verify_fail"), default="success")
    parser.add_argument("--task-id", default="")
    parser.add_argument("--confirm-task-id", default="")
    parser.add_argument("--sku", default="A001")
    parser.add_argument("--delta", type=int, default=5)
    parser.add_argument("--old-inventory", type=int, default=100)
    parser.add_argument("--target-inventory", type=int, default=105)
    parser.add_argument("--environment", default="local_poc")
    parser.add_argument("--page-profile", default="internal_inventory_admin_like_v1")
    parser.add_argument("--page-failure-mode", choices=("", "page_timeout", "element_missing"), default="")
    parser.add_argument("--force-verify-fail", action="store_true")
    parser.add_argument("--print-expected-only", action="store_true")
    args = parser.parse_args()

    payload = _build_payload(args)
    expected = SAMPLE_PRESETS[str(args.sample)]["expected"]
    out = {}
    call_error = ""
    if not bool(args.print_expected_only):
        out, call_error = _bridge_call(str(args.base_url), payload)
    align = _governance_alignment(out) if out else {"sample_bucket": "call_failed", "p62_view": "manual_review"}
    base_report = {
        "sample": str(args.sample),
        "payload": payload,
        "expected": expected,
        "bridge_call_error": call_error,
        "actual": {
            "task_id": out.get("task_id"),
            "confirm_task_id": out.get("confirm_task_id"),
            "operation_result": out.get("operation_result"),
            "verify_passed": out.get("verify_passed"),
            "verify_reason": out.get("verify_reason"),
            "failure_layer": out.get("failure_layer"),
            "raw_result_path": out.get("raw_result_path"),
            "evidence_paths": out.get("evidence_paths"),
            "rpa_vendor": out.get("rpa_vendor"),
            "page_url": out.get("page_url"),
            "page_profile": out.get("page_profile"),
            "page_steps": out.get("page_steps"),
            "page_evidence_count": out.get("page_evidence_count"),
            "page_failure_code": out.get("page_failure_code"),
        },
        "governance_alignment": align,
        "steps_checklist": [
            "operation_result",
            "verify_passed",
            "verify_reason",
            "failure_layer",
            "raw_result_path",
            "rpa_vendor",
            "confirm_task_id",
            "target_task_id",
        ],
    }
    if str(args.task_id or "").strip():
        base_report["task_id_replay"] = build_task_id_replay_report(
            task_id=str(args.task_id),
            base_url=str(args.base_url),
            payload=payload,
        )
    print(json.dumps(base_report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
