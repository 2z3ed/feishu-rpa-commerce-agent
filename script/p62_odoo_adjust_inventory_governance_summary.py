#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request
from collections import Counter


MIN_SAMPLE_SIZE = 3


def _fetch_json(url: str, timeout: float = 10.0):
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body or "null")


def _extract_kv(detail: str, key: str) -> str:
    marker = f"{key}="
    idx = (detail or "").find(marker)
    if idx < 0:
        return ""
    tail = detail[idx + len(marker) :]
    return tail.split(",", 1)[0].strip()


def _extract_action_detail(step_items: list[dict]) -> str:
    for s in step_items:
        if str(s.get("step_code") or "") == "action_executed":
            return str(s.get("detail") or "")
    return ""


def _extract_confirm_fields(task_detail: dict, step_items: list[dict]) -> dict:
    pr = task_detail.get("parsed_result")
    pr = pr if isinstance(pr, dict) else {}
    action_detail = _extract_action_detail(step_items)

    def _pick(key: str) -> str:
        v = pr.get(key, "")
        if v not in ("", None):
            return str(v)
        return _extract_kv(action_detail, key)

    return {
        "operation_result": _pick("operation_result"),
        "verify_passed": _pick("verify_passed"),
        "verify_reason": _pick("verify_reason"),
        "failure_layer": _pick("failure_layer"),
        "provider_id": _pick("provider_id"),
        "capability": _pick("capability"),
        "execution_mode": _pick("execution_mode"),
        "confirm_backend": _pick("confirm_backend"),
        "readiness_status": _pick("readiness_status"),
        "endpoint_profile": _pick("endpoint_profile"),
        "session_injection_mode": _pick("session_injection_mode"),
        "target_task_id": _pick("target_task_id"),
        "confirm_task_id": _pick("confirm_task_id") or str(task_detail.get("task_id") or ""),
        "original_update_task_id": _pick("original_update_task_id"),
        "action_executed_detail": action_detail,
    }


def summarize_p62(*, base_url: str, limit: int, task_prefix: str, recent_limit: int) -> dict:
    q = urllib.parse.urlencode({"limit": str(limit)})
    tasks = _fetch_json(f"{base_url.rstrip('/')}/api/v1/tasks?{q}")
    tasks = tasks if isinstance(tasks, list) else []

    adjust_tasks: list[dict] = []
    confirm_task_ids: list[str] = []
    for item in tasks:
        task_id = str(item.get("task_id") or "")
        if not task_id:
            continue
        if task_prefix and not task_id.startswith(task_prefix):
            continue
        rs = str(item.get("result_summary") or "")
        intent_text = str(item.get("intent_text") or "")
        if rs.startswith("[warehouse.adjust_inventory]"):
            adjust_tasks.append(item)
        if intent_text.startswith("确认执行"):
            confirm_task_ids.append(task_id)

    initiated_high_risk_tasks = len(adjust_tasks)
    awaiting_confirmation_count = sum(1 for t in adjust_tasks if str(t.get("status") or "") == "awaiting_confirmation")

    confirm_released = 0
    confirm_blocked = 0
    verify_pass = 0
    verify_fail = 0
    block_reason_distribution: Counter[str] = Counter()
    verify_reason_distribution: Counter[str] = Counter()
    recent_samples: list[dict] = []

    for task_id in confirm_task_ids:
        detail = _fetch_json(f"{base_url.rstrip('/')}/api/v1/tasks/{task_id}")
        detail = detail if isinstance(detail, dict) else {}
        steps = _fetch_json(f"{base_url.rstrip('/')}/api/v1/tasks/{task_id}/steps")
        steps = steps if isinstance(steps, list) else []
        fields = _extract_confirm_fields(detail, steps)
        op = str(fields["operation_result"] or "")
        fl = str(fields["failure_layer"] or "")
        vp_raw = str(fields["verify_passed"] or "").strip().lower()
        vp = vp_raw in {"true", "1", "yes"}

        # P6.2 minimum governance expression.
        if op == "confirm_blocked_noop":
            confirm_blocked += 1
            block_reason_distribution[str(fl or "unknown")] += 1
        if op in {"write_adjust_inventory", "write_adjust_inventory_verify_failed", "write_adjust_inventory_failed"}:
            confirm_released += 1
        if op == "write_adjust_inventory" and vp:
            verify_pass += 1
        if op == "write_adjust_inventory_verify_failed" or (fl == "verify_failed" and not vp):
            verify_fail += 1
            verify_reason_distribution[str(fields["verify_reason"] or "unknown")] += 1

        recent_samples.append(
            {
                "task_id": task_id,
                "status": str(detail.get("status") or ""),
                "operation_result": op,
                "failure_layer": fl,
                "verify_passed": fields["verify_passed"],
                "verify_reason": fields["verify_reason"],
                "provider_id": fields["provider_id"],
                "capability": fields["capability"],
                "execution_mode": fields["execution_mode"],
                "confirm_backend": fields["confirm_backend"],
                "target_task_id": fields["target_task_id"],
                "confirm_task_id": fields["confirm_task_id"],
                "original_update_task_id": fields["original_update_task_id"],
            }
        )

    return {
        "initiated_high_risk_tasks": initiated_high_risk_tasks,
        "awaiting_confirmation_count": awaiting_confirmation_count,
        "confirm_released_count": confirm_released,
        "confirm_blocked_count": confirm_blocked,
        "verify_pass_count": verify_pass,
        "verify_fail_count": verify_fail,
        "block_reason_distribution": dict(sorted(block_reason_distribution.items())),
        "verify_reason_distribution": dict(sorted(verify_reason_distribution.items())),
        "recent_samples": recent_samples[: max(1, int(recent_limit))],
    }


def build_p62_gate_precheck(summary: dict) -> dict:
    counts = {
        "initiated_high_risk_tasks": int(summary.get("initiated_high_risk_tasks") or 0),
        "awaiting_confirmation_count": int(summary.get("awaiting_confirmation_count") or 0),
        "confirm_released_count": int(summary.get("confirm_released_count") or 0),
        "confirm_blocked_count": int(summary.get("confirm_blocked_count") or 0),
        "verify_pass_count": int(summary.get("verify_pass_count") or 0),
        "verify_fail_count": int(summary.get("verify_fail_count") or 0),
    }
    block_reason_distribution = summary.get("block_reason_distribution") or {}
    verify_reason_distribution = summary.get("verify_reason_distribution") or {}
    latest_samples = summary.get("recent_samples") or []

    risk_flags: list[str] = []
    gate_status = "pass"
    gate_reason = "no_risk_signal"

    # Sample sufficiency should be explicit for P6.2 precheck.
    if counts["initiated_high_risk_tasks"] < MIN_SAMPLE_SIZE:
        risk_flags.append("sample_insufficient")
        gate_status = "warn"
        gate_reason = f"insufficient_samples_lt_{MIN_SAMPLE_SIZE}"

    if counts["confirm_blocked_count"] > 0:
        risk_flags.append("confirm_blocked_present")
        if gate_status != "block":
            gate_status = "warn"
            primary = sorted(block_reason_distribution.keys())[0] if block_reason_distribution else "unknown"
            gate_reason = f"confirm_blocked_present:{primary}"

    if counts["verify_fail_count"] > 0:
        risk_flags.append("verify_fail_present")
        gate_status = "block"
        primary_verify_reason = sorted(verify_reason_distribution.keys())[0] if verify_reason_distribution else "unknown"
        gate_reason = f"verify_fail_present:{primary_verify_reason}"

    if counts["awaiting_confirmation_count"] > counts["initiated_high_risk_tasks"] and counts["initiated_high_risk_tasks"] > 0:
        risk_flags.append("summary_counts_anomaly")
        if gate_status != "block":
            gate_status = "warn"
            gate_reason = "summary_counts_anomaly:awaiting_gt_initiated"

    if not risk_flags:
        risk_flags.append("none")

    return {
        "gate_status": gate_status,
        "gate_reason": gate_reason,
        "allow_adjust_inventory_flow": gate_status != "block",
        "has_blocking_risk": gate_status == "block",
        "risk_flags": risk_flags,
        "summary_counts": counts,
        "block_reason_distribution": dict(sorted((block_reason_distribution or {}).items())),
        "verify_reason_distribution": dict(sorted((verify_reason_distribution or {}).items())),
        "latest_samples": latest_samples[:5],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="P6.2 Odoo adjust_inventory governance summary")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--task-prefix", default="TASK-")
    parser.add_argument("--recent-limit", type=int, default=20)
    parser.add_argument("--with-gate", action="store_true")
    args = parser.parse_args()
    out = summarize_p62(
        base_url=str(args.base_url),
        limit=max(1, int(args.limit)),
        task_prefix=str(args.task_prefix or ""),
        recent_limit=max(1, int(args.recent_limit)),
    )
    if bool(args.with_gate):
        out = {
            "summary": out,
            "gate_precheck": build_p62_gate_precheck(out),
        }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
