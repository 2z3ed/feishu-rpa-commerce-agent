import importlib.util
import json
from pathlib import Path


def _load_script_module():
    script_path = Path("scripts/p52_woo_write_failure_summary.py").resolve()
    spec = importlib.util.spec_from_file_location("p52_woo_write_failure_summary", script_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_write_failure_summary_uses_parsed_result_failure_layer(monkeypatch):
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
                    {"task_id": "TASK-P52-1"},
                    {"task_id": "TASK-P52-2"},
                    {"task_id": "TASK-P52-3"},
                ]
            )
        if url.endswith("/tasks/TASK-P52-1"):
            return _Resp(
                {
                    "task_id": "TASK-P52-1",
                    "status": "succeeded",
                    "intent_code": "system.confirm_task",
                    "parsed_result": {"failure_layer": ""},
                }
            )
        if url.endswith("/tasks/TASK-P52-2"):
            return _Resp(
                {
                    "task_id": "TASK-P52-2",
                    "status": "failed",
                    "intent_code": "system.confirm_task",
                    "parsed_result": {"failure_layer": "confirm_target_invalid"},
                    "result_summary": "确认失败：[other_label] x",
                    "error_message": "[other_label] x",
                }
            )
        if url.endswith("/tasks/TASK-P52-3"):
            return _Resp(
                {
                    "task_id": "TASK-P52-3",
                    "status": "failed",
                    "intent_code": "product.query_sku_status",
                    "parsed_result": {},
                }
            )
        if url.endswith("/tasks/TASK-P52-1/steps"):
            return _Resp([{"step_code": "action_executed", "detail": "ok"}])
        if url.endswith("/tasks/TASK-P52-2/steps"):
            return _Resp([{"step_code": "action_executed", "detail": "failure_layer=save_feedback_failed"}])
        if url.endswith("/tasks/TASK-P52-3/steps"):
            return _Resp([{"step_code": "action_executed", "detail": "failure_layer=save_feedback_failed"}])
        raise RuntimeError(f"unexpected url: {url}")

    import urllib.request

    monkeypatch.setattr(urllib.request, "urlopen", _urlopen)
    out = mod.summarize_write_failures(
        base_url="http://127.0.0.1:8000",
        limit=10,
        task_prefix="TASK-P52",
    )
    assert out["total_tasks"] == 2
    assert out["succeeded_tasks"] == 1
    assert out["failed_tasks"] == 1
    assert out["failure_distribution"] == {"confirm_target_invalid": 1}
    assert out["recent_failed_tasks"] == [
        {"task_id": "TASK-P52-2", "failure_layer": "confirm_target_invalid"},
    ]
