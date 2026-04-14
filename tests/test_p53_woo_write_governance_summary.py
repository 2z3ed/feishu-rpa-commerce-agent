import importlib.util
import json
from pathlib import Path


def _load_script_module():
    script_path = Path("script/p53_woo_write_governance_summary.py").resolve()
    spec = importlib.util.spec_from_file_location("p53_woo_write_governance_summary", script_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_governance_summary_counts_confirm_only(monkeypatch):
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
                    {"task_id": "TASK-P53-U1", "intent_text": "修改 SKU A001 价格到 39.9"},
                    {"task_id": "TASK-P53-C1", "intent_text": "确认执行 TASK-P53-U1"},
                    {"task_id": "TASK-P53-C2", "intent_text": "确认执行 TASK-P53-U1"},
                    {"task_id": "TASK-P53-C3", "intent_text": "确认执行 TASK-INVALID"},
                    {"task_id": "TASK-P53-C4", "intent_text": "确认执行 TASK-LEGACY-UNKNOWN"},
                ]
            )
        if url.endswith("/tasks/TASK-P53-C1"):
            return _Resp(
                {
                    "task_id": "TASK-P53-C1",
                    "status": "succeeded",
                    "parsed_result": {
                        "failure_layer": "",
                        "operation_result": "write_update_price",
                        "verify_passed": True,
                        "verify_reason": "ok",
                        "target_task_id": "TASK-P53-U1",
                        "original_update_task_id": "TASK-P53-U1",
                        "confirm_task_id": "TASK-P53-C1",
                    },
                }
            )
        if url.endswith("/tasks/TASK-P53-C2"):
            return _Resp({"task_id": "TASK-P53-C2", "status": "failed"})
        if url.endswith("/tasks/TASK-P53-C3"):
            return _Resp({"task_id": "TASK-P53-C3", "status": "failed"})
        if url.endswith("/tasks/TASK-P53-C4"):
            return _Resp(
                {
                    "task_id": "TASK-P53-C4",
                    "status": "failed",
                    "result_summary": "确认失败：历史文案不可解析",
                    "error_message": "legacy free text no mapped label",
                }
            )
        if url.endswith("/tasks/TASK-P53-C1/steps"):
            return _Resp(
                [
                    {
                        "step_code": "action_executed",
                        "detail": "failure_layer=, operation_result=write_update_price, verify_passed=True, verify_reason=ok, target_task_id=TASK-P53-U1, original_update_task_id=TASK-P53-U1, confirm_task_id=TASK-P53-C1",
                    }
                ]
            )
        if url.endswith("/tasks/TASK-P53-C2/steps"):
            return _Resp(
                [
                    {
                        "step_code": "action_executed",
                        "detail": "failure_layer=confirm_target_already_consumed, operation_result=confirm_blocked_noop, verify_passed=False, verify_reason=already_consumed_status=succeeded, target_task_id=TASK-P53-U1, original_update_task_id=TASK-P53-U1, confirm_task_id=TASK-P53-C2",
                    }
                ]
            )
        if url.endswith("/tasks/TASK-P53-C3/steps"):
            return _Resp(
                [
                    {
                        "step_code": "action_executed",
                        "detail": "failure_layer=confirm_target_invalid, operation_result=confirm_blocked_noop, verify_passed=False, verify_reason=confirm_target_invalid, target_task_id=TASK-INVALID, original_update_task_id=TASK-INVALID, confirm_task_id=TASK-P53-C3",
                    }
                ]
            )
        if url.endswith("/tasks/TASK-P53-C4/steps"):
            return _Resp([])
        raise RuntimeError(f"unexpected url: {url}")

    import urllib.request

    monkeypatch.setattr(urllib.request, "urlopen", _urlopen)
    out = mod.summarize_governance(
        base_url="http://127.0.0.1:8000",
        limit=10,
        task_prefix="TASK-P53-",
        recent_limit=10,
    )
    assert out["total_confirm_attempts"] == 4
    assert out["successful_confirms"] == 1
    assert out["blocked_repeat_confirms"] == 1
    assert out["invalid_target_confirms"] == 1
    assert out["other_failed_confirms"] == 0
    assert out["unknown_confirms"] == 1
    assert out["governance_distribution"] == {
        "confirm_succeeded": 1,
        "confirm_target_already_consumed": 1,
        "confirm_target_invalid": 1,
        "unknown": 1,
    }
    assert out["source_mode_distribution"] == {
        "legacy_compatible": 2,
        "new_schema": 1,
        "unknown": 1,
    }
    assert out["unknown_reason_distribution"] == {
        "summary_message_not_classifiable": 1,
    }
    assert len(out["recent_governance_events"]) == 4


def test_replay_governance_event_new_schema(monkeypatch):
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
        if url.endswith("/tasks/TASK-P53-C1"):
            return _Resp(
                {
                    "task_id": "TASK-P53-C1",
                    "status": "succeeded",
                    "parsed_result": {
                        "failure_layer": "",
                        "operation_result": "write_update_price",
                        "verify_passed": True,
                        "verify_reason": "ok",
                        "target_task_id": "TASK-P53-U1",
                        "original_update_task_id": "TASK-P53-U1",
                        "confirm_task_id": "TASK-P53-C1",
                    },
                }
            )
        if url.endswith("/tasks/TASK-P53-C1/steps"):
            return _Resp([])
        raise RuntimeError(f"unexpected url: {url}")

    import urllib.request

    monkeypatch.setattr(urllib.request, "urlopen", _urlopen)
    out = mod.replay_governance_event(base_url="http://127.0.0.1:8000", task_id="TASK-P53-C1")
    assert out["confirm_task_id"] == "TASK-P53-C1"
    assert out["source_mode"] == "new_schema"
    assert out["unknown_reason"] == ""
    assert out["governance_event_type"] == "confirm_succeeded"


def test_replay_governance_event_unknown(monkeypatch):
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
        if url.endswith("/tasks/TASK-P53-C4"):
            return _Resp(
                {
                    "task_id": "TASK-P53-C4",
                    "status": "failed",
                    "result_summary": "确认失败：历史文案不可解析",
                    "error_message": "legacy free text no mapped label",
                }
            )
        if url.endswith("/tasks/TASK-P53-C4/steps"):
            return _Resp([])
        raise RuntimeError(f"unexpected url: {url}")

    import urllib.request

    monkeypatch.setattr(urllib.request, "urlopen", _urlopen)
    out = mod.replay_governance_event(base_url="http://127.0.0.1:8000", task_id="TASK-P53-C4")
    assert out["confirm_task_id"] == "TASK-P53-C4"
    assert out["source_mode"] == "unknown"
    assert out["unknown_reason"] == "summary_message_not_classifiable"
    assert out["governance_event_type"] == "unknown"
