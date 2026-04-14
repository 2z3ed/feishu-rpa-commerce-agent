import importlib.util
import json
from pathlib import Path


def _load_script_module():
    script_path = Path("scripts/p51_woo_readonly_failure_summary.py").resolve()
    spec = importlib.util.spec_from_file_location("p51_woo_readonly_failure_summary", script_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_failure_summary_uses_api_and_counts_distribution(monkeypatch):
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
                    {"task_id": "TASK-P50-R3-MANUAL-WOO-SAMPLE-1", "status": "succeeded"},
                    {"task_id": "TASK-P50-R3-MANUAL-WOO-SAMPLE-2", "status": "failed"},
                    {"task_id": "TASK-P50-R3-MANUAL-WOO-SAMPLE-3", "status": "failed"},
                ]
            )
        if url.endswith("/tasks/TASK-P50-R3-MANUAL-WOO-SAMPLE-1"):
            return _Resp({"task_id": "TASK-P50-R3-MANUAL-WOO-SAMPLE-1", "status": "succeeded"})
        if url.endswith("/tasks/TASK-P50-R3-MANUAL-WOO-SAMPLE-2"):
            return _Resp(
                {
                    "task_id": "TASK-P50-R3-MANUAL-WOO-SAMPLE-2",
                    "status": "failed",
                    "result_summary": "[detail_not_loaded] detail price selector missing",
                    "error_message": "[detail_not_loaded] detail selector missing",
                }
            )
        if url.endswith("/tasks/TASK-P50-R3-MANUAL-WOO-SAMPLE-3"):
            return _Resp(
                {
                    "task_id": "TASK-P50-R3-MANUAL-WOO-SAMPLE-3",
                    "status": "failed",
                    "result_summary": "[product.query_sku_status] 执行失败",
                    "error_message": "执行失败",
                }
            )
        if url.endswith("/tasks/TASK-P50-R3-MANUAL-WOO-SAMPLE-1/steps"):
            return _Resp([{"step_code": "action_executed", "detail": "ok"}])
        if url.endswith("/tasks/TASK-P50-R3-MANUAL-WOO-SAMPLE-2/steps"):
            return _Resp([{"step_code": "action_executed", "detail": "failure_layer=detail_not_loaded error_code=xx"}])
        if url.endswith("/tasks/TASK-P50-R3-MANUAL-WOO-SAMPLE-3/steps"):
            return _Resp([{"step_code": "action_executed", "detail": "failure_layer=readback_unstable error_code=yy"}])
        raise RuntimeError(f"unexpected url: {url}")

    import urllib.request

    monkeypatch.setattr(urllib.request, "urlopen", _urlopen)
    out = mod.summarize_failures(
        base_url="http://127.0.0.1:8000",
        limit=10,
        task_prefix="TASK-P50-R3-MANUAL-WOO-SAMPLE",
    )
    assert out["total_tasks"] == 3
    assert out["succeeded_tasks"] == 1
    assert out["failed_tasks"] == 2
    assert out["failure_distribution"] == {"detail_not_loaded": 1, "readback_unstable": 1}
    assert out["recent_failed_tasks"] == [
        {"task_id": "TASK-P50-R3-MANUAL-WOO-SAMPLE-2", "failure_layer": "detail_not_loaded"},
        {"task_id": "TASK-P50-R3-MANUAL-WOO-SAMPLE-3", "failure_layer": "readback_unstable"},
    ]
