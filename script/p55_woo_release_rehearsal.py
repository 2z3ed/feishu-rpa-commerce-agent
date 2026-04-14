#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone


COVERED_CHECKS = [
    "update_enters_awaiting_confirmation",
    "first_confirm_succeeds",
    "post_write_verification_present",
    "repeat_confirm_blocked",
    "invalid_target_safe_failure",
    "confirm_only_summary_available",
    "task_id_replay_available",
    "gate_output_available",
    "review_hints_available",
    "review_record_templates_available",
]


def _run_json_command(cmd: list[str], *, label: str) -> tuple[dict, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if int(proc.returncode) != 0:
        return {}, f"{label}_command_failed: exit={proc.returncode} stderr={(proc.stderr or '').strip()[:300]}"
    try:
        return json.loads(proc.stdout or "{}"), ""
    except Exception as exc:
        return {}, f"{label}_invalid_json: {exc}"


def _build_review_summary(gate_output: dict) -> dict:
    hints = gate_output.get("review_hints")
    if not isinstance(hints, list):
        hints = []
    blocking = [x for x in hints if isinstance(x, dict) and str(x.get("severity") or "") == "blocking"]
    warning = [x for x in hints if isinstance(x, dict) and str(x.get("severity") or "") == "warning"]
    return {
        "hint_count": len(hints),
        "blocking_hint_count": len(blocking),
        "warning_hint_count": len(warning),
        "rule_names": [str(x.get("rule_name") or "") for x in hints if isinstance(x, dict)],
    }


def _bool_check(checks: dict, name: str) -> bool:
    return bool(checks.get(name))


def run_rehearsal(
    *,
    base_url: str,
    task_prefix: str,
    limit: int,
    recent_limit: int,
    success_task_id: str,
    repeat_task_id: str,
    invalid_or_unknown_task_id: str,
    environment: str,
    gate_skip_tests: bool,
) -> dict:
    rehearsal_run_at = datetime.now(timezone.utc).astimezone().isoformat()
    checked_scripts = [
        "script/p53_woo_write_governance_summary.py",
        "script/p54_woo_write_gate_check.py",
    ]

    summary_cmd = [
        sys.executable,
        "script/p53_woo_write_governance_summary.py",
        "--base-url",
        base_url,
        "--task-prefix",
        task_prefix,
        "--limit",
        str(limit),
        "--recent-limit",
        str(recent_limit),
    ]
    summary, summary_err = _run_json_command(summary_cmd, label="p53_summary")

    replays: dict[str, dict] = {}
    replay_errors: dict[str, str] = {}
    for tid in [success_task_id, repeat_task_id, invalid_or_unknown_task_id]:
        if not tid:
            continue
        replay_cmd = [
            sys.executable,
            "script/p53_woo_write_governance_summary.py",
            "--base-url",
            base_url,
            "--task-id",
            tid,
        ]
        out, err = _run_json_command(replay_cmd, label=f"p53_replay_{tid}")
        if err:
            replay_errors[tid] = err
        else:
            replays[tid] = out

    gate_cmd = [
        sys.executable,
        "script/p54_woo_write_gate_check.py",
        "--base-url",
        base_url,
        "--task-prefix",
        task_prefix,
        "--limit",
        str(limit),
        "--recent-limit",
        str(recent_limit),
        "--replay-task-id",
        success_task_id,
        "--replay-task-id",
        repeat_task_id,
        "--replay-task-id",
        invalid_or_unknown_task_id,
    ]
    if gate_skip_tests:
        gate_cmd.append("--skip-tests")
    gate_output, gate_err = _run_json_command(gate_cmd, label="p54_gate")

    check_map = {
        "update_enters_awaiting_confirmation": bool(success_task_id),
        "first_confirm_succeeds": str((replays.get(success_task_id) or {}).get("governance_event_type") or "") == "confirm_succeeded",
        "post_write_verification_present": str((replays.get(success_task_id) or {}).get("verify_passed") or "") != "",
        "repeat_confirm_blocked": str((replays.get(repeat_task_id) or {}).get("governance_event_type") or "") == "confirm_target_already_consumed",
        "invalid_target_safe_failure": str((replays.get(invalid_or_unknown_task_id) or {}).get("governance_event_type") or "")
        in {"confirm_target_invalid", "unknown"},
        "confirm_only_summary_available": summary_err == "" and isinstance(summary.get("governance_distribution"), dict),
        "task_id_replay_available": len(replay_errors) == 0 and len(replays) >= 3,
        "gate_output_available": gate_err == "" and str(gate_output.get("status") or "") in {"pass", "pass_with_warnings", "fail"},
        "review_hints_available": isinstance(gate_output.get("review_hints"), list),
        "review_record_templates_available": isinstance(gate_output.get("review_record_templates"), list),
    }

    covered_checks = [{"name": name, "passed": _bool_check(check_map, name)} for name in COVERED_CHECKS]
    failed_checks = [x["name"] for x in covered_checks if not x["passed"]]
    final_result = "passed" if not failed_checks else "failed"

    out = {
        "rehearsal_run_at": rehearsal_run_at,
        "environment": environment or "",
        "covered_checks": covered_checks,
        "key_task_ids": {
            "success_confirm_task_id": success_task_id or "",
            "repeat_confirm_task_id": repeat_task_id or "",
            "invalid_or_unknown_task_id": invalid_or_unknown_task_id or "",
        },
        "gate_status": str(gate_output.get("gate_status") or gate_output.get("status") or ""),
        "review_summary": _build_review_summary(gate_output if isinstance(gate_output, dict) else {}),
        "final_result": final_result,
        "artifacts": {
            "p53_summary": summary,
            "p53_replays": replays,
            "p54_gate": gate_output,
        },
        "notes": {
            "summary_error": summary_err,
            "replay_errors": replay_errors,
            "gate_error": gate_err,
            "failed_checks": failed_checks,
            "stage_status_summary": "P5.0-P5.4 已通过，当前执行 P5.5 全链路演练与收口。",
        },
        "links": {
            "governance_sop": "docs/p53-woo-write-governance-sop.md",
            "rehearsal_doc": "docs/p55-woo-release-rehearsal.md",
            "checked_scripts": checked_scripts,
        },
    }
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="P5.5 Woo release rehearsal orchestrator")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--task-prefix", default="TASK-")
    parser.add_argument("--limit", type=int, default=80)
    parser.add_argument("--recent-limit", type=int, default=20)
    parser.add_argument("--success-task-id", required=True)
    parser.add_argument("--repeat-task-id", required=True)
    parser.add_argument("--invalid-or-unknown-task-id", required=True)
    parser.add_argument("--environment", default="staging_like")
    parser.add_argument("--gate-skip-tests", action="store_true")
    parser.add_argument("--output-json", default="")
    args = parser.parse_args()

    out = run_rehearsal(
        base_url=str(args.base_url),
        task_prefix=str(args.task_prefix or ""),
        limit=max(1, int(args.limit)),
        recent_limit=max(1, int(args.recent_limit)),
        success_task_id=str(args.success_task_id or ""),
        repeat_task_id=str(args.repeat_task_id or ""),
        invalid_or_unknown_task_id=str(args.invalid_or_unknown_task_id or ""),
        environment=str(args.environment or ""),
        gate_skip_tests=bool(args.gate_skip_tests),
    )
    if str(args.output_json or "").strip():
        with open(str(args.output_json).strip(), "w", encoding="utf-8") as f:
            f.write(json.dumps(out, ensure_ascii=False, indent=2))
            f.write("\n")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if str(out.get("final_result") or "") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
