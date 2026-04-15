"""
P6.1 - Odoo high-risk write manual sample trigger (acceptance-only).

Goal:
- Create ONE stable, repeatable Odoo high-risk write sample task for `warehouse.adjust_inventory`.
- Evidence must be observable via:
  - GET /api/v1/tasks/{task_id}
  - GET /api/v1/tasks/{task_id}/steps

Flow:
- Create original task (awaiting_confirmation)
- Create confirm task via system.confirm_task (唯一放行入口)
- Verify post-check fields exist via /steps action_executed.detail

Constraints:
- No real production write.
- No real Odoo login automation.
- Use internal sandbox only.
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


def _run_ingress(task_id: str, text: str, open_id: str, message_id: str, chat_id: str):
    import inspect

    run_sig = inspect.signature(process_ingress_message.run)
    first_param = next(iter(run_sig.parameters.values()), None)
    if first_param and first_param.name == "self":
        process_ingress_message.run(None, task_id, text, open_id, message_id, chat_id)
    else:
        process_ingress_message.run(task_id, text, open_id, message_id, chat_id)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sku", default="A001")
    parser.add_argument("--delta", type=int, default=5)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--poll-seconds", type=float, default=10.0)
    args = parser.parse_args()

    if int(args.delta) == 0:
        raise SystemExit("[p61_acceptance_failed] delta must be non-zero")

    ts = get_shanghai_now().strftime("%Y%m%d-%H%M%S")
    orig_task_id = f"TASK-P61-ODOO-ADJ-ORIG-{ts}"
    confirm_task_id = f"TASK-P61-ODOO-ADJ-CFM-{ts}"

    sign = "+" if int(args.delta) > 0 else ""
    cmd_orig = f"调整 Odoo SKU {args.sku} 库存 {sign}{int(args.delta)}"
    cmd_confirm = f"确认执行 {orig_task_id}"

    # Create original task via idempotency+ingress chain.
    idempotency_service._generate_task_id = lambda: orig_task_id  # type: ignore[attr-defined]
    msg_id_1 = f"manual-p61-orig-{uuid.uuid4().hex}"
    payload_1 = {
        "message_id": msg_id_1,
        "chat_id": "cli-manual-p61",
        "open_id": "manual-user",
        "text": cmd_orig,
        "create_time": int(time.time()),
    }
    is_dup, _existing, new_id = idempotency_service.check_and_create(message_id=msg_id_1, raw_payload=payload_1)
    if is_dup or new_id != orig_task_id:
        raise SystemExit(f"[p61_acceptance_failed] orig task_id mismatch dup={is_dup} got={new_id}")

    _run_ingress(orig_task_id, cmd_orig, payload_1["open_id"], msg_id_1, payload_1["chat_id"])

    # Create confirm task via idempotency+ingress chain.
    idempotency_service._generate_task_id = lambda: confirm_task_id  # type: ignore[attr-defined]
    msg_id_2 = f"manual-p61-cfm-{uuid.uuid4().hex}"
    payload_2 = {
        "message_id": msg_id_2,
        "chat_id": "cli-manual-p61",
        "open_id": "manual-user",
        "text": cmd_confirm,
        "create_time": int(time.time()),
    }
    is_dup2, _existing2, new_id2 = idempotency_service.check_and_create(message_id=msg_id_2, raw_payload=payload_2)
    if is_dup2 or new_id2 != confirm_task_id:
        raise SystemExit(f"[p61_acceptance_failed] confirm task_id mismatch dup={is_dup2} got={new_id2}")

    _run_ingress(confirm_task_id, cmd_confirm, payload_2["open_id"], msg_id_2, payload_2["chat_id"])

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
            code_orig, body_orig = _get_json(f"/api/v1/tasks/{orig_task_id}")
            code_cfm, body_cfm = _get_json(f"/api/v1/tasks/{confirm_task_id}")
            code_steps_cfm, steps_cfm = _get_json(f"/api/v1/tasks/{confirm_task_id}/steps")
            if code_orig == 200 and code_cfm == 200 and code_steps_cfm == 200:
                if (body_cfm or {}).get("status") != "succeeded":
                    raise RuntimeError(f"confirm status is not succeeded: {(body_cfm or {}).get('status')}")
                if (body_orig or {}).get("status") not in {"succeeded", "failed"}:
                    raise RuntimeError(f"orig status unexpected: {(body_orig or {}).get('status')}")

                action_steps = [s for s in (steps_cfm or []) if s.get("step_code") == "action_executed"]
                detail = (action_steps[-1].get("detail") if action_steps else "") or ""
                must = {
                    "provider_id=odoo",
                    "capability=warehouse.adjust_inventory",
                    "operation_result=",
                    "verify_passed=",
                    "verify_reason=",
                    f"target_task_id={orig_task_id}",
                    f"confirm_task_id={confirm_task_id}",
                }
                for m in must:
                    if m not in detail:
                        raise RuntimeError(f"action_executed.detail missing: {m}")

                print(orig_task_id)
                print(confirm_task_id)
                print(f"/api/v1/tasks/{orig_task_id} => {code_orig} status={body_orig.get('status')}")
                print(f"/api/v1/tasks/{confirm_task_id} => {code_cfm} status={body_cfm.get('status')}")
                print(f"/api/v1/tasks/{confirm_task_id}/steps => {code_steps_cfm}")
                return 0
        except Exception as e:  # pragma: no cover
            last_err = e
            time.sleep(0.5)

    raise SystemExit(f"[p61_acceptance_failed] api not observable or evidence invalid: {last_err}")


if __name__ == "__main__":
    raise SystemExit(main())

