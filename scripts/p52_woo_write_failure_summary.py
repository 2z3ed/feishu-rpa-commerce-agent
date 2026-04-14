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


def _extract_failure_layer(detail: dict, steps: list[dict]) -> str:
    pr = detail.get("parsed_result")
    if isinstance(pr, dict):
        layer = str(pr.get("failure_layer") or "").strip()
        if layer:
            return layer

    for step in steps:
        if str(step.get("step_code") or "") != "action_executed":
            continue
        text = str(step.get("detail") or "")
        marker = "failure_layer="
        idx = text.find(marker)
        if idx < 0:
            continue
        tail = text[idx + len(marker) :]
        layer = tail.split(",", 1)[0].split(" ", 1)[0].strip()
        if layer:
            return layer
    return "unknown_exception"


def summarize_write_failures(*, base_url: str, limit: int, task_prefix: str) -> dict:
    q = urllib.parse.urlencode({"limit": str(limit)})
    tasks_url = f"{base_url.rstrip('/')}/api/v1/tasks?{q}"
    task_items = _fetch_json(tasks_url)
    task_items = task_items if isinstance(task_items, list) else []

    selected_task_ids: list[str] = []
    for item in task_items:
        task_id = str(item.get("task_id") or "")
        if not task_id:
            continue
        if task_prefix and not task_id.startswith(task_prefix):
            continue
        selected_task_ids.append(task_id)

    failure_distribution: Counter[str] = Counter()
    recent_failed_tasks: list[dict] = []
    total = 0
    succeeded = 0
    failed = 0

    for task_id in selected_task_ids:
        detail = _fetch_json(f"{base_url.rstrip('/')}/api/v1/tasks/{task_id}")
        steps = _fetch_json(f"{base_url.rstrip('/')}/api/v1/tasks/{task_id}/steps")
        detail = detail if isinstance(detail, dict) else {}
        steps = steps if isinstance(steps, list) else []
        intent_code = str(detail.get("intent_code") or "").strip()
        intent_text = str(detail.get("intent_text") or "").strip()
        if intent_code != "system.confirm_task" and not intent_text.startswith("确认执行"):
            continue
        total += 1
        status = str(detail.get("status") or "")
        if status == "succeeded":
            succeeded += 1
            continue
        if status != "failed":
            continue

        failed += 1
        layer = _extract_failure_layer(detail, steps)
        failure_distribution[layer] += 1
        recent_failed_tasks.append({"task_id": task_id, "failure_layer": layer})

    return {
        "total_tasks": total,
        "succeeded_tasks": succeeded,
        "failed_tasks": failed,
        "failure_distribution": dict(sorted(failure_distribution.items())),
        "recent_failed_tasks": recent_failed_tasks[: min(20, len(recent_failed_tasks))],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize Woo write-chain failures from Tasks API")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--task-prefix", default="TASK-P52")
    args = parser.parse_args()

    result = summarize_write_failures(
        base_url=str(args.base_url),
        limit=max(1, int(args.limit)),
        task_prefix=str(args.task_prefix or ""),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
