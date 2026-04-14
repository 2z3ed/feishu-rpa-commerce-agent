#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import urllib.parse
import urllib.request
from collections import Counter


def _fetch_json(url: str, timeout: float = 10.0):
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body or "null")


def _extract_layer_from_text(text: str) -> str | None:
    raw = (text or "").strip()
    if not raw:
        return None
    m = re.match(r"^\[([^\]]+)\]", raw)
    if m:
        return m.group(1).strip()
    m = re.search(r"failure_layer=([^,\s]+)", raw)
    if m:
        return m.group(1).strip()
    return None


def _is_intent_label(label: str) -> bool:
    raw = (label or "").strip().lower()
    return bool(re.match(r"^[a-z]+\.[a-z0-9_]+$", raw))


def summarize_failures(*, base_url: str, limit: int, task_prefix: str) -> dict:
    q = urllib.parse.urlencode({"limit": str(limit)})
    tasks_url = f"{base_url.rstrip('/')}/api/v1/tasks?{q}"
    task_items = _fetch_json(tasks_url)
    task_items = task_items if isinstance(task_items, list) else []

    selected = []
    for item in task_items:
        task_id = str(item.get("task_id") or "")
        if task_prefix and not task_id.startswith(task_prefix):
            continue
        selected.append(task_id)

    failure_distribution: Counter[str] = Counter()
    recent_failed_tasks: list[dict] = []
    succeeded = 0
    failed = 0

    for task_id in selected:
        detail = _fetch_json(f"{base_url.rstrip('/')}/api/v1/tasks/{task_id}")
        steps = _fetch_json(f"{base_url.rstrip('/')}/api/v1/tasks/{task_id}/steps")
        steps = steps if isinstance(steps, list) else []
        status = str((detail or {}).get("status") or "")
        if status == "succeeded":
            succeeded += 1
            continue

        failed += 1
        layer = _extract_layer_from_text(str((detail or {}).get("result_summary") or ""))
        if not layer:
            layer = _extract_layer_from_text(str((detail or {}).get("error_message") or ""))
        if layer and _is_intent_label(layer):
            layer = None
        if not layer:
            for step in steps:
                if str(step.get("step_code") or "") == "action_executed":
                    layer = _extract_layer_from_text(str(step.get("detail") or ""))
                    if layer:
                        break
        if layer and _is_intent_label(layer):
            layer = None
        if not layer:
            layer = "unknown_exception"

        failure_distribution[layer] += 1
        recent_failed_tasks.append({"task_id": task_id, "failure_layer": layer})

    return {
        "total_tasks": len(selected),
        "succeeded_tasks": succeeded,
        "failed_tasks": failed,
        "failure_distribution": dict(sorted(failure_distribution.items())),
        "recent_failed_tasks": recent_failed_tasks[: min(len(recent_failed_tasks), 20)],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize Woo readonly failures from Tasks API")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--task-prefix", default="TASK-P50-R3-MANUAL-WOO-SAMPLE")
    args = parser.parse_args()

    result = summarize_failures(
        base_url=str(args.base_url),
        limit=max(1, int(args.limit)),
        task_prefix=str(args.task_prefix or ""),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
