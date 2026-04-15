"""
P6.0 Round1 - Odoo readonly manual sample trigger (acceptance-only).

Goal:
- Create ONE stable, repeatable Odoo readonly sample task for `warehouse.query_inventory`.
- Evidence must be observable via:
  - GET /api/v1/tasks/{task_id}
  - GET /api/v1/tasks/{task_id}/steps
  - action_executed.detail contains stable key fields

Constraints:
- No new internal APIs.
- Do NOT change execute mode strategy.
- Do NOT add Odoo write chain or any second action.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import uuid

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Some environments running acceptance scripts don't have Feishu SDK installed.
try:
    import lark_oapi as _lark  # noqa: F401
except Exception:  # pragma: no cover
    import types

    fake_lark = types.ModuleType("lark_oapi")

    class _Client:
        pass

    fake_lark.Client = _Client
    sys.modules["lark_oapi"] = fake_lark

try:
    import celery as _celery  # noqa: F401
except Exception:  # pragma: no cover
    import types

    fake_celery = types.ModuleType("celery")

    class _Celery:
        def __init__(self, *args, **kwargs):
            self.conf = {}

        def config_from_object(self, *args, **kwargs):
            return None

        def task(self, *args, **kwargs):
            def _decorator(fn):
                class _TaskWrapper:
                    def __init__(self, f):
                        self.run = f

                return _TaskWrapper(fn)

            return _decorator

    fake_celery.Celery = _Celery
    sys.modules["celery"] = fake_celery

from app.core.time import get_shanghai_now
from app.services.feishu.idempotency import idempotency_service
from app.tasks.ingress_tasks import process_ingress_message


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sku", default="A001")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--poll-seconds", type=float, default=10.0)
    args = parser.parse_args()

    ts = get_shanghai_now().strftime("%Y%m%d-%H%M%S")
    task_id = f"TASK-P60-ODOO-READONLY-SAMPLE-{ts}"
    cmd = f"查 Odoo 里 SKU {args.sku} 的库存"

    # Force id from the EXISTING ingress chain (no direct TaskRecord/TaskStep writes here).
    idempotency_service._generate_task_id = lambda: task_id  # type: ignore[attr-defined]
    message_id = f"manual-p60-{uuid.uuid4().hex}"
    payload = {
        "message_id": message_id,
        "chat_id": "cli-manual-p60",
        "open_id": "manual-user",
        "text": cmd,
        "create_time": int(time.time()),
    }
    is_dup, existing_task_id, new_task_id = idempotency_service.check_and_create(
        message_id=message_id, raw_payload=payload
    )
    if is_dup:
        raise SystemExit(
            f"[p60_acceptance_failed] duplicate message_id hit unexpectedly: existing_task_id={existing_task_id}"
        )
    if new_task_id != task_id:
        raise SystemExit(
            f"[p60_acceptance_failed] task_id mismatch: expected={task_id} got={new_task_id}"
        )

    # Run the EXISTING celery task logic synchronously (no broker required).
    import inspect

    run_sig = inspect.signature(process_ingress_message.run)
    first_param = next(iter(run_sig.parameters.values()), None)
    if first_param and first_param.name == "self":
        process_ingress_message.run(None, task_id, cmd, payload["open_id"], message_id, payload["chat_id"])
    else:
        process_ingress_message.run(task_id, cmd, payload["open_id"], message_id, payload["chat_id"])

    # Verify observable evidence via running API.
    import json
    import urllib.request

    def _get_json(path: str):
        req = urllib.request.Request(
            args.base_url.rstrip("/") + path,
            headers={"accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.getcode(), json.loads(r.read().decode("utf-8"))

    deadline = time.time() + float(args.poll_seconds)
    last_err = None
    while time.time() < deadline:
        try:
            code_task, body_task = _get_json(f"/api/v1/tasks/{task_id}")
            code_steps, body_steps = _get_json(f"/api/v1/tasks/{task_id}/steps")
            if code_task == 200 and code_steps == 200:
                if (body_task or {}).get("status") != "succeeded":
                    raise RuntimeError(f"task status is not succeeded: {(body_task or {}).get('status')}")
                summary = str((body_task or {}).get("result_summary") or "")
                if "[warehouse.query_inventory]" not in summary:
                    raise RuntimeError("result_summary missing intent prefix")
                for k in ("SKU:", "库存：", "平台：odoo", "provider_id：odoo", "capability：warehouse.query_inventory"):
                    if k not in summary:
                        raise RuntimeError(f"result_summary missing: {k}")

                action_steps = [s for s in (body_steps or []) if s.get("step_code") == "action_executed"]
                detail = (action_steps[-1].get("detail") if action_steps else "") or ""
                must = {
                    "provider_id=odoo",
                    "capability=warehouse.query_inventory",
                    "execution_mode=api",
                    "readiness_status=ready",
                    "endpoint_profile=",
                    "session_injection_mode=",
                }
                for m in must:
                    if m not in detail:
                        raise RuntimeError(f"action_executed.detail missing: {m}")
                if "endpoint_profile=none" in detail or "session_injection_mode=none" in detail:
                    raise RuntimeError("action_executed.detail endpoint/profile empty")

                print(task_id)
                print(f"/api/v1/tasks/{task_id} => {code_task}")
                print(f"/api/v1/tasks/{task_id}/steps => {code_steps}")
                return 0
        except Exception as e:  # pragma: no cover
            last_err = e
            time.sleep(0.5)

    raise SystemExit(f"[p60_acceptance_failed] api not observable or evidence invalid: {last_err}")


if __name__ == "__main__":
    raise SystemExit(main())

