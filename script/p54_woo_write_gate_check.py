#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


UNKNOWN_RATIO_BLOCK_THRESHOLD = 0.2


def _run_command(cmd: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return int(proc.returncode), str(proc.stdout or ""), str(proc.stderr or "")


def _run_json_command(cmd: list[str], *, label: str) -> tuple[dict, str | None]:
    code, out, err = _run_command(cmd)
    if code != 0:
        return {}, f"{label}_command_failed: exit={code} stderr={err.strip()[:300]}"
    try:
        return json.loads(out or "{}"), None
    except Exception as exc:
        return {}, f"{label}_invalid_json: {exc}"


def _validate_summary_shape(summary: dict) -> list[str]:
    required = {
        "total_confirm_attempts",
        "successful_confirms",
        "blocked_repeat_confirms",
        "invalid_target_confirms",
        "other_failed_confirms",
        "unknown_confirms",
        "governance_distribution",
        "source_mode_distribution",
        "unknown_reason_distribution",
        "recent_governance_events",
    }
    missing = [k for k in sorted(required) if k not in summary]
    return [f"summary_missing_field:{k}" for k in missing]


def _validate_replay_shape(replay: dict, *, task_id: str) -> list[str]:
    required = {
        "confirm_task_id",
        "target_task_id",
        "original_update_task_id",
        "operation_result",
        "verify_passed",
        "verify_reason",
        "failure_layer",
        "governance_event_type",
        "source_mode",
        "unknown_reason",
    }
    missing = [k for k in sorted(required) if k not in replay]
    errs = [f"replay_missing_field:{task_id}:{k}" for k in missing]
    if replay.get("source_mode") not in {"new_schema", "legacy_compatible", "unknown"}:
        errs.append(f"replay_invalid_source_mode:{task_id}:{replay.get('source_mode')}")
    return errs


def _build_gate_decision(summary: dict) -> tuple[list[str], list[str]]:
    blocking_failures: list[str] = []
    warnings: list[str] = []

    total = int(summary.get("total_confirm_attempts") or 0)
    other_failed = int(summary.get("other_failed_confirms") or 0)
    unknown = int(summary.get("unknown_confirms") or 0)
    blocked_repeat = int(summary.get("blocked_repeat_confirms") or 0)
    invalid_target = int(summary.get("invalid_target_confirms") or 0)

    if other_failed > 0:
        blocking_failures.append(f"other_failed_confirms_gt_0:{other_failed}")

    unknown_ratio = (unknown / total) if total > 0 else 0.0
    if unknown_ratio > UNKNOWN_RATIO_BLOCK_THRESHOLD:
        blocking_failures.append(
            f"unknown_ratio_gt_threshold:ratio={unknown_ratio:.4f},threshold={UNKNOWN_RATIO_BLOCK_THRESHOLD:.4f}"
        )
    elif unknown > 0:
        warnings.append(f"unknown_confirms_present:{unknown}")

    if blocked_repeat == 0:
        warnings.append("blocked_repeat_confirms_eq_0:coverage_maybe_insufficient")
    if invalid_target > 0:
        warnings.append(f"invalid_target_confirms_present:{invalid_target}")

    return blocking_failures, warnings


def run_gate_check(
    *,
    base_url: str,
    limit: int,
    task_prefix: str,
    recent_limit: int,
    replay_task_ids: list[str],
    run_tests: bool,
) -> dict:
    blocking_failures: list[str] = []
    warnings: list[str] = []
    checks: dict = {}

    if run_tests:
        code, out, err = _run_command(["pytest", "-q", "tests/test_p53_woo_write_governance_summary.py"])
        checks["pytest"] = {
            "return_code": code,
            "stdout": out.strip()[-500:],
            "stderr": err.strip()[-500:],
        }
        if code != 0:
            blocking_failures.append("pytest_failed:test_p53_woo_write_governance_summary")

    summary_cmd = [
        sys.executable,
        "script/p53_woo_write_governance_summary.py",
        "--base-url",
        base_url,
        "--limit",
        str(limit),
        "--task-prefix",
        task_prefix,
        "--recent-limit",
        str(recent_limit),
    ]
    summary, summary_err = _run_json_command(summary_cmd, label="summary")
    checks["summary"] = {"command": summary_cmd, "ok": summary_err is None}
    if summary_err:
        blocking_failures.append(summary_err)
    else:
        shape_errs = _validate_summary_shape(summary)
        blocking_failures.extend(shape_errs)
        b, w = _build_gate_decision(summary)
        blocking_failures.extend(b)
        warnings.extend(w)
        checks["summary_output"] = summary

    replay_outputs: dict[str, dict] = {}
    for task_id in replay_task_ids:
        replay_cmd = [
            sys.executable,
            "script/p53_woo_write_governance_summary.py",
            "--base-url",
            base_url,
            "--task-id",
            str(task_id),
        ]
        replay, replay_err = _run_json_command(replay_cmd, label=f"replay_{task_id}")
        checks.setdefault("replay", {})[task_id] = {"command": replay_cmd, "ok": replay_err is None}
        if replay_err:
            blocking_failures.append(replay_err)
            continue
        replay_outputs[task_id] = replay
        blocking_failures.extend(_validate_replay_shape(replay, task_id=task_id))

    if replay_outputs:
        checks["replay_output"] = replay_outputs

    status = "pass"
    if blocking_failures:
        status = "fail"
    elif warnings:
        status = "pass_with_warnings"

    return {
        "status": status,
        "blocking_failures": blocking_failures,
        "warnings": warnings,
        "thresholds": {
            "unknown_ratio_block_threshold": UNKNOWN_RATIO_BLOCK_THRESHOLD,
            "other_failed_confirms_block_if_gt": 0,
            "blocked_repeat_confirms_eq_0_warning": True,
            "invalid_target_confirms_non_blocking": True,
        },
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="P5.4 Woo governance gate check")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--limit", type=int, default=80)
    parser.add_argument("--task-prefix", default="TASK-")
    parser.add_argument("--recent-limit", type=int, default=20)
    parser.add_argument("--replay-task-id", action="append", default=[])
    parser.add_argument("--skip-tests", action="store_true")
    args = parser.parse_args()

    out = run_gate_check(
        base_url=str(args.base_url),
        limit=max(1, int(args.limit)),
        task_prefix=str(args.task_prefix or ""),
        recent_limit=max(1, int(args.recent_limit)),
        replay_task_ids=[str(x) for x in (args.replay_task_id or [])],
        run_tests=not bool(args.skip_tests),
    )
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 1 if out["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
