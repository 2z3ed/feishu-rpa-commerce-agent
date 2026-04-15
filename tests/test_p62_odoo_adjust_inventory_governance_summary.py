import importlib.util
import json
from pathlib import Path


def _load_script_module():
    script_path = Path("script/p62_odoo_adjust_inventory_governance_summary.py").resolve()
    spec = importlib.util.spec_from_file_location("p62_odoo_adjust_inventory_governance_summary", script_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_p62_governance_summary_counts(monkeypatch):
    mod = _load_script_module()

    class _Resp:
        def __init__(self, body):
            self._body = body

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps(self._body).encode("utf-8")

    def _urlopen(req, timeout=10):  # noqa: ARG001
        url = req.full_url
        if url.startswith("http://127.0.0.1:8000/api/v1/tasks?"):
            return _Resp(
                [
                    {
                        "task_id": "TASK-P62-U1",
                        "intent_text": "调整 Odoo SKU A001 库存 +5",
                        "result_summary": "[warehouse.adjust_inventory] ...",
                        "status": "awaiting_confirmation",
                    },
                    {
                        "task_id": "TASK-P62-U2",
                        "intent_text": "调整 Odoo SKU A001 库存 +5",
                        "result_summary": "[warehouse.adjust_inventory] ...",
                        "status": "succeeded",
                    },
                    {"task_id": "TASK-P62-C1", "intent_text": "确认执行 TASK-P62-U2"},
                    {"task_id": "TASK-P62-C2", "intent_text": "确认执行 TASK-P62-U2"},
                    {"task_id": "TASK-P62-C3", "intent_text": "确认执行 TASK-P62-U3"},
                ]
            )
        if url.endswith("/tasks/TASK-P62-C1"):
            return _Resp(
                {
                    "task_id": "TASK-P62-C1",
                    "status": "succeeded",
                    "parsed_result": {
                        "operation_result": "write_adjust_inventory",
                        "verify_passed": True,
                        "verify_reason": "ok",
                        "failure_layer": "",
                        "target_task_id": "TASK-P62-U2",
                        "original_update_task_id": "TASK-P62-U2",
                        "confirm_task_id": "TASK-P62-C1",
                    },
                }
            )
        if url.endswith("/tasks/TASK-P62-C2"):
            return _Resp(
                {
                    "task_id": "TASK-P62-C2",
                    "status": "failed",
                    "parsed_result": {
                        "operation_result": "confirm_blocked_noop",
                        "verify_passed": False,
                        "verify_reason": "confirm_context_missing",
                        "failure_layer": "confirm_context_missing",
                        "target_task_id": "TASK-P62-U2",
                        "original_update_task_id": "TASK-P62-U2",
                        "confirm_task_id": "TASK-P62-C2",
                    },
                }
            )
        if url.endswith("/tasks/TASK-P62-C3"):
            return _Resp(
                {
                    "task_id": "TASK-P62-C3",
                    "status": "failed",
                    "parsed_result": {
                        "operation_result": "write_adjust_inventory_verify_failed",
                        "verify_passed": False,
                        "verify_reason": "forced_verify_failure expected=105 got=105",
                        "failure_layer": "verify_failed",
                        "target_task_id": "TASK-P62-U3",
                        "original_update_task_id": "TASK-P62-U3",
                        "confirm_task_id": "TASK-P62-C3",
                    },
                }
            )
        if url.endswith("/tasks/TASK-P62-C1/steps"):
            return _Resp([{"step_code": "action_executed", "detail": "provider_id=odoo, capability=warehouse.adjust_inventory"}])
        if url.endswith("/tasks/TASK-P62-C2/steps"):
            return _Resp([{"step_code": "action_executed", "detail": "provider_id=odoo, capability=warehouse.adjust_inventory"}])
        if url.endswith("/tasks/TASK-P62-C3/steps"):
            return _Resp([{"step_code": "action_executed", "detail": "provider_id=odoo, capability=warehouse.adjust_inventory"}])
        raise RuntimeError(f"unexpected url: {url}")

    import urllib.request

    monkeypatch.setattr(urllib.request, "urlopen", _urlopen)
    out = mod.summarize_p62(
        base_url="http://127.0.0.1:8000",
        limit=20,
        task_prefix="TASK-P62-",
        recent_limit=20,
    )
    assert out["initiated_high_risk_tasks"] == 2
    assert out["awaiting_confirmation_count"] == 1
    assert out["confirm_released_count"] == 2
    assert out["confirm_blocked_count"] == 1
    assert out["verify_pass_count"] == 1
    assert out["verify_fail_count"] == 1
    assert out["block_reason_distribution"] == {"confirm_context_missing": 1}
    assert out["verify_reason_distribution"] == {"forced_verify_failure expected=105 got=105": 1}


def test_p62_governance_summary_fallback_from_action_detail(monkeypatch):
    mod = _load_script_module()

    class _Resp:
        def __init__(self, body):
            self._body = body

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps(self._body).encode("utf-8")

    def _urlopen(req, timeout=10):  # noqa: ARG001
        url = req.full_url
        if url.startswith("http://127.0.0.1:8000/api/v1/tasks?"):
            return _Resp(
                [
                    {
                        "task_id": "TASK-P62-U4",
                        "intent_text": "调整 Odoo SKU A001 库存 +5",
                        "result_summary": "[warehouse.adjust_inventory] ...",
                        "status": "failed",
                    },
                    {"task_id": "TASK-P62-C4", "intent_text": "确认执行 TASK-P62-U4"},
                ]
            )
        if url.endswith("/tasks/TASK-P62-C4"):
            return _Resp({"task_id": "TASK-P62-C4", "status": "failed"})
        if url.endswith("/tasks/TASK-P62-C4/steps"):
            return _Resp(
                [
                    {
                        "step_code": "action_executed",
                        "detail": "execution_mode=api, provider_id=odoo, capability=warehouse.adjust_inventory, confirm_backend=none, operation_result=confirm_blocked_noop, verify_passed=False, verify_reason=confirm_context_invalid_json, failure_layer=confirm_context_invalid_json, target_task_id=TASK-P62-U4, original_update_task_id=TASK-P62-U4, confirm_task_id=TASK-P62-C4",
                    }
                ]
            )
        raise RuntimeError(f"unexpected url: {url}")

    import urllib.request

    monkeypatch.setattr(urllib.request, "urlopen", _urlopen)
    out = mod.summarize_p62(
        base_url="http://127.0.0.1:8000",
        limit=20,
        task_prefix="TASK-P62-",
        recent_limit=20,
    )
    assert out["initiated_high_risk_tasks"] == 1
    assert out["awaiting_confirmation_count"] == 0
    assert out["confirm_released_count"] == 0
    assert out["confirm_blocked_count"] == 1
    assert out["verify_pass_count"] == 0
    assert out["verify_fail_count"] == 0
    assert out["block_reason_distribution"] == {"confirm_context_invalid_json": 1}


def test_p62_gate_precheck_pass_when_no_risk():
    mod = _load_script_module()
    summary = {
        "initiated_high_risk_tasks": 4,
        "awaiting_confirmation_count": 0,
        "confirm_released_count": 4,
        "confirm_blocked_count": 0,
        "verify_pass_count": 4,
        "verify_fail_count": 0,
        "block_reason_distribution": {},
        "verify_reason_distribution": {},
        "recent_samples": [{"task_id": "TASK-P62-C1"}],
    }
    out = mod.build_p62_gate_precheck(summary)
    assert out["gate_status"] == "pass"
    assert out["gate_reason"] == "no_risk_signal"
    assert out["allow_adjust_inventory_flow"] is True
    assert out["has_blocking_risk"] is False
    assert out["risk_flags"] == ["none"]
    assert set(out["summary_counts"].keys()) == {
        "initiated_high_risk_tasks",
        "awaiting_confirmation_count",
        "confirm_released_count",
        "confirm_blocked_count",
        "verify_pass_count",
        "verify_fail_count",
    }


def test_p62_gate_precheck_warn_for_confirm_blocked():
    mod = _load_script_module()
    summary = {
        "initiated_high_risk_tasks": 5,
        "awaiting_confirmation_count": 1,
        "confirm_released_count": 4,
        "confirm_blocked_count": 2,
        "verify_pass_count": 4,
        "verify_fail_count": 0,
        "block_reason_distribution": {"confirm_context_missing": 2},
        "verify_reason_distribution": {},
        "recent_samples": [{"task_id": "TASK-P62-C2"}],
    }
    out = mod.build_p62_gate_precheck(summary)
    assert out["gate_status"] == "warn"
    assert out["gate_reason"] == "confirm_blocked_present:confirm_context_missing"
    assert out["allow_adjust_inventory_flow"] is True
    assert out["has_blocking_risk"] is False
    assert "confirm_blocked_present" in out["risk_flags"]


def test_p62_gate_precheck_block_for_verify_fail():
    mod = _load_script_module()
    summary = {
        "initiated_high_risk_tasks": 5,
        "awaiting_confirmation_count": 0,
        "confirm_released_count": 5,
        "confirm_blocked_count": 0,
        "verify_pass_count": 4,
        "verify_fail_count": 1,
        "block_reason_distribution": {},
        "verify_reason_distribution": {"forced_verify_failure expected=105 got=105": 1},
        "recent_samples": [{"task_id": "TASK-P62-C3"}],
    }
    out = mod.build_p62_gate_precheck(summary)
    assert out["gate_status"] == "block"
    assert out["gate_reason"] == "verify_fail_present:forced_verify_failure expected=105 got=105"
    assert out["allow_adjust_inventory_flow"] is False
    assert out["has_blocking_risk"] is True
    assert "verify_fail_present" in out["risk_flags"]


def test_p62_gate_precheck_warn_for_sample_insufficient():
    mod = _load_script_module()
    summary = {
        "initiated_high_risk_tasks": 1,
        "awaiting_confirmation_count": 0,
        "confirm_released_count": 1,
        "confirm_blocked_count": 0,
        "verify_pass_count": 1,
        "verify_fail_count": 0,
        "block_reason_distribution": {},
        "verify_reason_distribution": {},
        "recent_samples": [{"task_id": "TASK-P62-C5"}],
    }
    out = mod.build_p62_gate_precheck(summary)
    assert out["gate_status"] == "warn"
    assert out["gate_reason"] == "insufficient_samples_lt_3"
    assert out["allow_adjust_inventory_flow"] is True
    assert out["has_blocking_risk"] is False
    assert "sample_insufficient" in out["risk_flags"]


def test_p62_gate_precheck_output_shape_stable():
    mod = _load_script_module()
    summary = {
        "initiated_high_risk_tasks": 4,
        "awaiting_confirmation_count": 0,
        "confirm_released_count": 4,
        "confirm_blocked_count": 0,
        "verify_pass_count": 4,
        "verify_fail_count": 0,
        "block_reason_distribution": {},
        "verify_reason_distribution": {},
        "recent_samples": [{"task_id": "TASK-P62-C1"}],
    }
    out = mod.build_p62_gate_precheck(summary)
    assert set(out.keys()) == {
        "gate_status",
        "gate_reason",
        "allow_adjust_inventory_flow",
        "has_blocking_risk",
        "risk_flags",
        "summary_counts",
        "block_reason_distribution",
        "verify_reason_distribution",
        "latest_samples",
    }
