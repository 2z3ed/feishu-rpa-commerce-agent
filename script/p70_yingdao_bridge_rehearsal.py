#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import urllib.request


def main() -> int:
    parser = argparse.ArgumentParser(description="P7.0 local Yingdao bridge rehearsal")
    parser.add_argument("--base-url", default="http://127.0.0.1:17891")
    parser.add_argument("--task-id", default="TASK-P70-REHEARSAL-1")
    parser.add_argument("--confirm-task-id", default="TASK-P70-REHEARSAL-CFM-1")
    parser.add_argument("--sku", default="A001")
    parser.add_argument("--delta", type=int, default=5)
    parser.add_argument("--old-inventory", type=int, default=100)
    parser.add_argument("--target-inventory", type=int, default=105)
    parser.add_argument("--environment", default="local_poc")
    parser.add_argument("--force-verify-fail", action="store_true")
    args = parser.parse_args()

    payload = {
        "task_id": str(args.task_id),
        "confirm_task_id": str(args.confirm_task_id),
        "provider_id": "odoo",
        "capability": "warehouse.adjust_inventory",
        "sku": str(args.sku),
        "delta": int(args.delta),
        "old_inventory": int(args.old_inventory),
        "target_inventory": int(args.target_inventory),
        "environment": str(args.environment),
        "force_verify_fail": bool(args.force_verify_fail),
    }
    req = urllib.request.Request(
        f"{str(args.base_url).rstrip('/')}/run",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        out = json.loads((resp.read() or b"{}").decode("utf-8"))
    print(
        json.dumps(
            {
                "task_id": out.get("task_id"),
                "confirm_task_id": out.get("confirm_task_id"),
                "operation_result": out.get("operation_result"),
                "verify_passed": out.get("verify_passed"),
                "verify_reason": out.get("verify_reason"),
                "failure_layer": out.get("failure_layer"),
                "raw_result_path": out.get("raw_result_path"),
                "evidence_paths": out.get("evidence_paths"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
