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


UNKNOWN_REASON_TASK_NOT_FOUND = "task_not_found"
UNKNOWN_REASON_STEPS_NOT_FOUND = "steps_not_found"
UNKNOWN_REASON_MISSING_PARSED_RESULT_AND_NO_MAPPABLE_LABEL = "missing_parsed_result_and_no_mappable_label"
UNKNOWN_REASON_DETAIL_MISSING_FAILURE_HINTS = "detail_missing_failure_hints"
UNKNOWN_REASON_SUMMARY_MESSAGE_NOT_CLASSIFIABLE = "summary_message_not_classifiable"

SOURCE_MODE_NEW_SCHEMA = "new_schema"
SOURCE_MODE_LEGACY_COMPATIBLE = "legacy_compatible"
SOURCE_MODE_UNKNOWN = "unknown"

EVENT_CONFIRM_SUCCEEDED = "confirm_succeeded"
EVENT_CONFIRM_TARGET_ALREADY_CONSUMED = "confirm_target_already_consumed"
EVENT_CONFIRM_TARGET_INVALID = "confirm_target_invalid"
EVENT_OTHER_FAILED = "other_failed"
EVENT_UNKNOWN = "unknown"


def _classify_failure_layer_from_text(*, result_summary: str, error_message: str) -> tuple[str, str]:
    text = f"{result_summary} {error_message}".strip().lower()
    if not text:
        return "", UNKNOWN_REASON_SUMMARY_MESSAGE_NOT_CLASSIFIABLE
    if "confirm_target_already_consumed" in text:
        return EVENT_CONFIRM_TARGET_ALREADY_CONSUMED, ""
    if "already_consumed_status=" in text:
        return EVENT_CONFIRM_TARGET_ALREADY_CONSUMED, ""
    if "confirm_target_invalid" in text:
        return EVENT_CONFIRM_TARGET_INVALID, ""
    if "任务" in text and "不存在" in text:
        return EVENT_CONFIRM_TARGET_INVALID, ""
    return "", UNKNOWN_REASON_SUMMARY_MESSAGE_NOT_CLASSIFIABLE


def _extract_governance_fields(task_detail: dict, task_steps: list[dict]) -> dict:
    pr = task_detail.get("parsed_result")
    parsed_result = pr if isinstance(pr, dict) else {}
    action_detail = ""
    for step in task_steps:
        if str(step.get("step_code") or "") == "action_executed":
            action_detail = str(step.get("detail") or "")
            break

    parsed_failure_layer = str(parsed_result.get("failure_layer") or "").strip()
    if parsed_failure_layer:
        return {
            "operation_result": str(parsed_result.get("operation_result") or ""),
            "verify_passed": str(parsed_result.get("verify_passed") or ""),
            "verify_reason": str(parsed_result.get("verify_reason") or ""),
            "failure_layer": parsed_failure_layer,
            "target_task_id": str(parsed_result.get("target_task_id") or task_detail.get("target_task_id") or ""),
            "original_update_task_id": str(parsed_result.get("original_update_task_id") or ""),
            "confirm_task_id": str(parsed_result.get("confirm_task_id") or task_detail.get("task_id") or ""),
            "action_executed_detail": action_detail,
            "source_mode": SOURCE_MODE_NEW_SCHEMA,
            "unknown_reason": "",
        }
    if parsed_result and not parsed_failure_layer:
        return {
            "operation_result": str(parsed_result.get("operation_result") or ""),
            "verify_passed": str(parsed_result.get("verify_passed") or ""),
            "verify_reason": str(parsed_result.get("verify_reason") or ""),
            "failure_layer": "",
            "target_task_id": str(parsed_result.get("target_task_id") or task_detail.get("target_task_id") or ""),
            "original_update_task_id": str(parsed_result.get("original_update_task_id") or ""),
            "confirm_task_id": str(parsed_result.get("confirm_task_id") or task_detail.get("task_id") or ""),
            "action_executed_detail": action_detail,
            "source_mode": SOURCE_MODE_NEW_SCHEMA,
            "unknown_reason": "",
        }

    def _pick(field: str) -> str:
        value = _extract_from_action_detail(action_detail, field)
        if value != "":
            return value
        if field == "confirm_task_id":
            return str(task_detail.get("task_id") or "")
        if field == "target_task_id":
            return str(task_detail.get("target_task_id") or "")
        return _extract_from_action_detail(action_detail, field)

    detail_failure_layer = _pick("failure_layer")
    if detail_failure_layer:
        return {
            "operation_result": _pick("operation_result"),
            "verify_passed": _pick("verify_passed"),
            "verify_reason": _pick("verify_reason"),
            "failure_layer": detail_failure_layer,
            "target_task_id": _pick("target_task_id"),
            "original_update_task_id": _pick("original_update_task_id"),
            "confirm_task_id": _pick("confirm_task_id"),
            "action_executed_detail": action_detail,
            "source_mode": SOURCE_MODE_LEGACY_COMPATIBLE,
            "unknown_reason": "",
        }
    if action_detail:
        return {
            "operation_result": _pick("operation_result"),
            "verify_passed": _pick("verify_passed"),
            "verify_reason": _pick("verify_reason"),
            "failure_layer": "",
            "target_task_id": _pick("target_task_id"),
            "original_update_task_id": _pick("original_update_task_id"),
            "confirm_task_id": _pick("confirm_task_id"),
            "action_executed_detail": action_detail,
            "source_mode": SOURCE_MODE_LEGACY_COMPATIBLE,
            "unknown_reason": UNKNOWN_REASON_DETAIL_MISSING_FAILURE_HINTS,
        }

    summary_failure_layer, summary_reason = _classify_failure_layer_from_text(
        result_summary=str(task_detail.get("result_summary") or ""),
        error_message=str(task_detail.get("error_message") or ""),
    )
    if summary_failure_layer:
        return {
            "operation_result": "",
            "verify_passed": "",
            "verify_reason": "",
            "failure_layer": summary_failure_layer,
            "target_task_id": str(task_detail.get("target_task_id") or ""),
            "original_update_task_id": "",
            "confirm_task_id": str(task_detail.get("task_id") or ""),
            "action_executed_detail": action_detail,
            "source_mode": SOURCE_MODE_LEGACY_COMPATIBLE,
            "unknown_reason": "",
        }

    return {
        "operation_result": _pick("operation_result"),
        "verify_passed": _pick("verify_passed"),
        "verify_reason": _pick("verify_reason"),
        "failure_layer": "",
        "target_task_id": _pick("target_task_id"),
        "original_update_task_id": _pick("original_update_task_id"),
        "confirm_task_id": str(task_detail.get("task_id") or ""),
        "action_executed_detail": action_detail,
        "source_mode": SOURCE_MODE_UNKNOWN,
        "unknown_reason": (
            summary_reason if summary_reason else UNKNOWN_REASON_MISSING_PARSED_RESULT_AND_NO_MAPPABLE_LABEL
        ),
    }


def _event_type_from_sample(*, status: str, failure_layer: str, source_mode: str) -> str:
    if source_mode == SOURCE_MODE_UNKNOWN:
        return EVENT_UNKNOWN
    if status == "succeeded":
        return EVENT_CONFIRM_SUCCEEDED
    if failure_layer == EVENT_CONFIRM_TARGET_ALREADY_CONSUMED:
        return EVENT_CONFIRM_TARGET_ALREADY_CONSUMED
    if failure_layer == EVENT_CONFIRM_TARGET_INVALID:
        return EVENT_CONFIRM_TARGET_INVALID
    if status == "failed":
        return EVENT_OTHER_FAILED
    return EVENT_UNKNOWN


def _build_governance_event(*, task_id: str, detail: dict, steps: list[dict] | None) -> dict:
    if not isinstance(detail, dict):
        return {
            "confirm_task_id": task_id,
            "task_id": task_id,
            "target_task_id": "",
            "original_update_task_id": "",
            "operation_result": "",
            "verify_passed": "",
            "verify_reason": "",
            "failure_layer": "",
            "governance_event_type": EVENT_UNKNOWN,
            "source_mode": SOURCE_MODE_UNKNOWN,
            "unknown_reason": UNKNOWN_REASON_TASK_NOT_FOUND,
            "status": "",
        }
    if not isinstance(steps, list):
        return {
            "confirm_task_id": task_id,
            "task_id": task_id,
            "target_task_id": str(detail.get("target_task_id") or ""),
            "original_update_task_id": "",
            "operation_result": "",
            "verify_passed": "",
            "verify_reason": "",
            "failure_layer": "",
            "governance_event_type": EVENT_UNKNOWN,
            "source_mode": SOURCE_MODE_UNKNOWN,
            "unknown_reason": UNKNOWN_REASON_STEPS_NOT_FOUND,
            "status": str(detail.get("status") or ""),
        }

    status = str(detail.get("status") or "")
    gov = _extract_governance_fields(detail, steps)
    failure_layer = str(gov.get("failure_layer") or "")
    return {
        "task_id": task_id,
        "status": status,
        "failure_layer": failure_layer,
        "operation_result": str(gov.get("operation_result") or ""),
        "verify_passed": str(gov.get("verify_passed") or ""),
        "verify_reason": str(gov.get("verify_reason") or ""),
        "target_task_id": str(gov.get("target_task_id") or ""),
        "original_update_task_id": str(gov.get("original_update_task_id") or ""),
        "confirm_task_id": str(gov.get("confirm_task_id") or task_id),
        "governance_event_type": _event_type_from_sample(
            status=status,
            failure_layer=failure_layer,
            source_mode=str(gov.get("source_mode") or SOURCE_MODE_UNKNOWN),
        ),
        "source_mode": str(gov.get("source_mode") or SOURCE_MODE_UNKNOWN),
        "unknown_reason": str(gov.get("unknown_reason") or ""),
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
    success = blocked_repeat = invalid_target = other_failed = unknown = 0
    source_distribution: Counter[str] = Counter()
    unknown_reason_distribution: Counter[str] = Counter()

    for task_id in confirm_task_ids:
        detail = _fetch_json(f"{base_url.rstrip('/')}/api/v1/tasks/{task_id}")
        steps = _fetch_json(f"{base_url.rstrip('/')}/api/v1/tasks/{task_id}/steps")
        event = _build_governance_event(
            task_id=task_id,
            detail=detail if isinstance(detail, dict) else None,
            steps=steps if isinstance(steps, list) else None,
        )
        et = event["governance_event_type"]
        source_distribution[event["source_mode"]] += 1
        if event["unknown_reason"]:
            unknown_reason_distribution[event["unknown_reason"]] += 1
        if et == EVENT_CONFIRM_SUCCEEDED:
            success += 1
        elif et == EVENT_CONFIRM_TARGET_ALREADY_CONSUMED:
            blocked_repeat += 1
        elif et == EVENT_CONFIRM_TARGET_INVALID:
            invalid_target += 1
        elif et == EVENT_OTHER_FAILED:
            other_failed += 1
        else:
            unknown += 1
        distribution[et] += 1
        events.append(event)

    return {
        "total_confirm_attempts": len(confirm_task_ids),
        "successful_confirms": success,
        "blocked_repeat_confirms": blocked_repeat,
        "invalid_target_confirms": invalid_target,
        "other_failed_confirms": other_failed,
        "unknown_confirms": unknown,
        "governance_distribution": dict(sorted(distribution.items())),
        "source_mode_distribution": dict(sorted(source_distribution.items())),
        "unknown_reason_distribution": dict(sorted(unknown_reason_distribution.items())),
        "recent_governance_events": events[: max(1, int(recent_limit))],
    }


def replay_governance_event(*, base_url: str, task_id: str) -> dict:
    detail = _fetch_json(f"{base_url.rstrip('/')}/api/v1/tasks/{task_id}")
    steps = _fetch_json(f"{base_url.rstrip('/')}/api/v1/tasks/{task_id}/steps")
    return _build_governance_event(
        task_id=task_id,
        detail=detail if isinstance(detail, dict) else None,
        steps=steps if isinstance(steps, list) else None,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize Woo confirm-governance samples from Tasks API")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--limit", type=int, default=80)
    parser.add_argument("--task-prefix", default="TASK-")
    parser.add_argument("--recent-limit", type=int, default=20)
    parser.add_argument("--task-id", default="")
    args = parser.parse_args()
    if str(args.task_id or "").strip():
        out = replay_governance_event(base_url=str(args.base_url), task_id=str(args.task_id).strip())
    else:
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
