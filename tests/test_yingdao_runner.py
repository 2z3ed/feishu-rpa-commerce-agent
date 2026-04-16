import json
import socket
import urllib.error

from app.rpa.yingdao_runner import YingdaoBridgeError, run_yingdao_adjust_inventory


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
                    "page_url": "http://127.0.0.1:8000/api/v1/internal/rpa-sandbox/admin-like/catalog?sku=A001",
                    "page_profile": "internal_inventory_adjust_v1",
                    "page_steps": ["open_page", "locate_sku", "submit", "read_page_echo"],
                    "page_evidence_count": 0,
                    "page_failure_code": "",
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
    assert out["page_profile"] == "internal_inventory_adjust_v1"


def test_yingdao_runner_unreachable(monkeypatch):
    def _urlopen(req, timeout=30):  # noqa: ARG001
        raise urllib.error.URLError("connection refused")

    import urllib.request

    monkeypatch.setattr(urllib.request, "urlopen", _urlopen)
    try:
        run_yingdao_adjust_inventory({"task_id": "TASK-P7-RUNNER-ERR"})
        assert False, "expected YingdaoBridgeError"
    except YingdaoBridgeError as exc:
        assert exc.failure_layer == "bridge_unreachable"
        assert exc.operation_result == "write_adjust_inventory_bridge_unreachable"


def test_yingdao_runner_timeout(monkeypatch):
    def _urlopen(req, timeout=30):  # noqa: ARG001
        raise socket.timeout("timed out")

    import urllib.request

    monkeypatch.setattr(urllib.request, "urlopen", _urlopen)
    try:
        run_yingdao_adjust_inventory({"task_id": "TASK-P7-RUNNER-TIMEOUT"})
        assert False, "expected YingdaoBridgeError"
    except YingdaoBridgeError as exc:
        assert exc.failure_layer == "bridge_timeout"
        assert exc.operation_result == "write_adjust_inventory_bridge_timeout"


def test_yingdao_runner_missing_fields(monkeypatch):
    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps({"task_id": "TASK-P7-RUNNER-MISSING"}).encode("utf-8")

    def _urlopen(req, timeout=30):  # noqa: ARG001
        return _Resp()

    import urllib.request

    monkeypatch.setattr(urllib.request, "urlopen", _urlopen)
    try:
        run_yingdao_adjust_inventory({"task_id": "TASK-P7-RUNNER-MISSING"})
        assert False, "expected YingdaoBridgeError"
    except YingdaoBridgeError as exc:
        assert exc.failure_layer == "bridge_result_missing_fields"
