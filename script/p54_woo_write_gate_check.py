#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys


UNKNOWN_RATIO_BLOCK_THRESHOLD = 0.2
MAX_RECOMMENDED_TASK_IDS = 3
ENTRY_P53_REPLAY_TASK_ID = "p53_replay_task_id"
ENTRY_TASKS_DETAIL = "tasks_detail"
ENTRY_STEPS_ACTION_EXECUTED = "steps_action_executed"
ACTION_BLOCK = "block"
ACTION_REVIEW = "review"
ACTION_ALLOW = "allow"


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


def _pick_recent_task_ids(summary: dict, *, event_type: str, max_items: int = MAX_RECOMMENDED_TASK_IDS) -> list[str]:
    events = summary.get("recent_governance_events")
    if not isinstance(events, list):
        return []
    out: list[str] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        if str(event.get("governance_event_type") or "") != event_type:
            continue
        task_id = str(event.get("confirm_task_id") or event.get("task_id") or "")
        if not task_id or task_id in out:
            continue
        out.append(task_id)
        if len(out) >= max_items:
            break
    return out


def _build_review_hints(*, summary: dict, blocking_failures: list[str], warnings: list[str]) -> list[dict]:
    hints: list[dict] = []
    # Blocking rules
    for failure in blocking_failures:
        if failure.startswith("other_failed_confirms_gt_0"):
            hints.append(
                {
                    "severity": "blocking",
                    "rule_name": "other_failed_confirms_gt_0",
                    "recommended_action": ACTION_BLOCK,
                    "recommended_entry": ENTRY_P53_REPLAY_TASK_ID,
                    "recommended_task_ids": _pick_recent_task_ids(summary, event_type="other_failed"),
                    "next_step": "按 task_id 执行 p53 回放，再对照 tasks_detail 与 steps_action_executed 定位失败层级。",
                }
            )
        elif failure.startswith("unknown_ratio_gt_threshold"):
            hints.append(
                {
                    "severity": "blocking",
                    "rule_name": "unknown_ratio_gt_threshold",
                    "recommended_action": ACTION_BLOCK,
                    "recommended_entry": ENTRY_P53_REPLAY_TASK_ID,
                    "recommended_task_ids": _pick_recent_task_ids(summary, event_type="unknown"),
                    "next_step": "优先回放 unknown 样本，确认是否是历史证据不足或字段口径退化，再决定是否放行。",
                }
            )
        elif failure.startswith("summary_") or failure.startswith("replay_") or failure.startswith("pytest_"):
            hints.append(
                {
                    "severity": "blocking",
                    "rule_name": "gate_infra_or_shape_failure",
                    "recommended_action": ACTION_BLOCK,
                    "recommended_entry": ENTRY_TASKS_DETAIL,
                    "recommended_task_ids": [],
                    "next_step": "先修复脚本执行/输出结构问题，再重新运行门禁。",
                }
            )

    # Warning rules
    for warning in warnings:
        if warning.startswith("unknown_confirms_present"):
            hints.append(
                {
                    "severity": "warning",
                    "rule_name": "unknown_confirms_present",
                    "recommended_action": ACTION_REVIEW,
                    "recommended_entry": ENTRY_P53_REPLAY_TASK_ID,
                    "recommended_task_ids": _pick_recent_task_ids(summary, event_type="unknown"),
                    "next_step": "抽样回放 unknown 样本，确认为历史证据不足后可人工复核放行。",
                }
            )
        elif warning.startswith("blocked_repeat_confirms_eq_0"):
            hints.append(
                {
                    "severity": "warning",
                    "rule_name": "blocked_repeat_confirms_eq_0",
                    "recommended_action": ACTION_REVIEW,
                    "recommended_entry": ENTRY_STEPS_ACTION_EXECUTED,
                    "recommended_task_ids": _pick_recent_task_ids(summary, event_type="confirm_succeeded"),
                    "next_step": "补一组重复 confirm 样本回归，确认幂等拦截覆盖后再放行。",
                }
            )
        elif warning.startswith("invalid_target_confirms_present"):
            hints.append(
                {
                    "severity": "warning",
                    "rule_name": "invalid_target_confirms_present",
                    "recommended_action": ACTION_ALLOW,
                    "recommended_entry": ENTRY_P53_REPLAY_TASK_ID,
                    "recommended_task_ids": _pick_recent_task_ids(summary, event_type="confirm_target_invalid"),
                    "next_step": "回放确认属于预期无效 target 测试噪音后可放行。",
                }
            )
    return hints


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
    summary_output: dict = {}
    if summary_err:
        blocking_failures.append(summary_err)
    else:
        summary_output = summary
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

    review_hints = _build_review_hints(
        summary=summary_output,
        blocking_failures=blocking_failures,
        warnings=warnings,
    )

    return {
        "status": status,
        "blocking_failures": blocking_failures,
        "warnings": warnings,
        "review_hints": review_hints,
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
