#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request
from collections import Counter


def _fetch_json(url: str, timeout: float = 10.0):
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body or "null")


def _extract_from_action_detail(detail: str, key: str) -> str:
    marker = f"{key}="
    idx = detail.find(marker)
    if idx < 0:
        return ""
    tail = detail[idx + len(marker) :]
    return tail.split(",", 1)[0].strip()


def _extract_governance_fields(task_detail: dict, task_steps: list[dict]) -> dict:
    pr = task_detail.get("parsed_result")
    if not isinstance(pr, dict):
        pr = {}
    action_detail = ""
    for step in task_steps:
        if str(step.get("step_code") or "") == "action_executed":
            action_detail = str(step.get("detail") or "")
            break

    def _pick(field: str) -> str:
        from_pr = pr.get(field)
        if from_pr is not None and str(from_pr) != "":
            return str(from_pr)
        return _extract_from_action_detail(action_detail, field)

    return {
        "operation_result": _pick("operation_result"),
        "verify_passed": _pick("verify_passed"),
        "verify_reason": _pick("verify_reason"),
        "failure_layer": _pick("failure_layer"),
        "target_task_id": _pick("target_task_id"),
        "original_update_task_id": _pick("original_update_task_id"),
        "confirm_task_id": _pick("confirm_task_id"),
        "action_executed_detail": action_detail,
    }


def summarize_governance(*, base_url: str, limit: int, task_prefix: str, recent_limit: int) -> dict:
    q = urllib.parse.urlencode({"limit": str(limit)})
    tasks_url = f"{base_url.rstrip('/')}/api/v1/tasks?{q}"
    items = _fetch_json(tasks_url)
    items = items if isinstance(items, list) else []

    # confirm-only window: do not mix product.update_price samples.
    confirm_task_ids: list[str] = []
    for item in items:
        task_id = str(item.get("task_id") or "")
        if not task_id:
            continue
        if task_prefix and not task_id.startswith(task_prefix):
            continue
        intent_text = str(item.get("intent_text") or "")
        if intent_text.startswith("确认执行"):
            confirm_task_ids.append(task_id)

    distribution: Counter[str] = Counter()
    events: list[dict] = []
    success = 0
    blocked_repeat = 0
    invalid_target = 0
    other_failed = 0

    for task_id in confirm_task_ids:
        detail = _fetch_json(f"{base_url.rstrip('/')}/api/v1/tasks/{task_id}")
        steps = _fetch_json(f"{base_url.rstrip('/')}/api/v1/tasks/{task_id}/steps")
        detail = detail if isinstance(detail, dict) else {}
        steps = steps if isinstance(steps, list) else []
        status = str(detail.get("status") or "")
        gov = _extract_governance_fields(detail, steps)
        layer = gov["failure_layer"] or "none"

        if status == "succeeded":
            success += 1
            bucket = "confirm_succeeded"
        elif layer == "confirm_target_already_consumed":
            blocked_repeat += 1
            bucket = "confirm_target_already_consumed"
        elif layer == "confirm_target_invalid":
            invalid_target += 1
            bucket = "confirm_target_invalid"
        else:
            other_failed += 1
            bucket = "other_failed"
        distribution[bucket] += 1
        events.append(
            {
                "task_id": task_id,
                "status": status,
                "failure_layer": layer,
                "operation_result": gov["operation_result"],
                "verify_passed": gov["verify_passed"],
                "verify_reason": gov["verify_reason"],
                "target_task_id": gov["target_task_id"],
                "original_update_task_id": gov["original_update_task_id"],
                "confirm_task_id": gov["confirm_task_id"] or task_id,
            }
        )

    return {
        "total_confirm_attempts": len(confirm_task_ids),
        "successful_confirms": success,
        "blocked_repeat_confirms": blocked_repeat,
        "invalid_target_confirms": invalid_target,
        "other_failed_confirms": other_failed,
        "governance_distribution": dict(sorted(distribution.items())),
        "recent_governance_events": events[: max(1, int(recent_limit))],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize Woo confirm-governance samples from Tasks API")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--limit", type=int, default=80)
    parser.add_argument("--task-prefix", default="TASK-")
    parser.add_argument("--recent-limit", type=int, default=20)
    args = parser.parse_args()
    out = summarize_governance(
        base_url=str(args.base_url),
        limit=max(1, int(args.limit)),
        task_prefix=str(args.task_prefix or ""),
        recent_limit=max(1, int(args.recent_limit)),
    )
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
