import json

from app.rpa.yingdao_runner import run_yingdao_adjust_inventory


def test_yingdao_runner_calls_bridge(monkeypatch):
    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps(
                {
                    "task_id": "TASK-P7-RUNNER-1",
                    "confirm_task_id": "TASK-P7-CFM-1",
                    "provider_id": "odoo",
                    "capability": "warehouse.adjust_inventory",
                    "rpa_vendor": "yingdao",
                    "operation_result": "write_adjust_inventory",
                    "verify_passed": True,
                    "verify_reason": "ok",
                    "failure_layer": "",
                    "status": "done",
                    "raw_result_path": "/tmp/yingdao/result.json",
                    "evidence_paths": [],
                }
            ).encode("utf-8")

    def _urlopen(req, timeout=30):  # noqa: ARG001
        assert req.full_url.endswith("/run")
        return _Resp()

    import urllib.request

    monkeypatch.setattr(urllib.request, "urlopen", _urlopen)
    out = run_yingdao_adjust_inventory(
        {
            "task_id": "TASK-P7-RUNNER-1",
            "confirm_task_id": "TASK-P7-CFM-1",
            "provider_id": "odoo",
            "capability": "warehouse.adjust_inventory",
            "sku": "A001",
            "delta": 5,
            "old_inventory": 100,
            "target_inventory": 105,
            "environment": "local_poc",
        }
    )
    assert out["rpa_vendor"] == "yingdao"
    assert out["operation_result"] == "write_adjust_inventory"
