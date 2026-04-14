import importlib.util
import json
import sys
import types
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import TaskRecord
from app.rpa.real_admin_readonly import ERROR_HOME_LOAD_FAILED, run_real_admin_readonly_flow


def test_round3_readonly_flow_no_nameerror_on_log(tmp_path):
    class _Resp:
        status = 500

    class _Page:
        url = "about:blank"

        def goto(self, *_args, **_kwargs):
            return _Resp()

        def screenshot(self, path: str, full_page: bool):  # noqa: ARG002
            Path(path).write_bytes(b"ok")

    out = run_real_admin_readonly_flow(
        page=_Page(),
        evidence_dir=tmp_path,
        evidence_paths=[],
        sku="A001",
        readiness_snapshot={"status": "ready"},
        timeout_ms=1000,
        requested_target_price=10.0,
        requested_current_price=9.0,
        verify_mode="strict",
        dry_run=False,
        platform="woo",
        read_source="detail_page",
        verify_only=True,
    )
    assert out.success is False
    assert out.error_code == ERROR_HOME_LOAD_FAILED


def test_round3_empty_source_message_id_skips_reply(monkeypatch):
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
    monkeypatch.setitem(sys.modules, "celery", fake_celery)

    fake_lark = types.ModuleType("lark_oapi")

    class _Client:
        pass

    fake_lark.Client = _Client
    monkeypatch.setitem(sys.modules, "lark_oapi", fake_lark)

    from app.tasks import ingress_tasks

    engine = create_engine("sqlite:///:memory:")
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    db = Session()
    try:
        db.add(TaskRecord(task_id="TASK-P50-R3-REPLY-SKIP", source_platform="feishu", status="queued", intent_text="查 SKU"))
        db.commit()

        monkeypatch.setattr(ingress_tasks, "SessionLocal", lambda: db)
        monkeypatch.setattr(ingress_tasks, "try_write_bitable_ledger", lambda **kwargs: None)
        monkeypatch.setattr(ingress_tasks.lang_graph, "invoke", lambda _state: {"status": "succeeded", "result_summary": "ok"})

        calls = {"reply": 0}

        class _FakeClient:
            def send_text_reply(self, message_id: str, text: str):  # noqa: ARG002
                calls["reply"] += 1
                return True

        monkeypatch.setattr(ingress_tasks, "FeishuClient", _FakeClient)
        monkeypatch.setattr(ingress_tasks, "log_step", lambda *args, **kwargs: None)

        ingress_tasks.process_ingress_message.run(
            None,
            task_id="TASK-P50-R3-REPLY-SKIP",
            intent_text="查 SKU",
            user_open_id="manual-user",
            source_message_id="",
            chat_id="cli-manual-round3",
        )
        assert calls["reply"] == 0
    finally:
        db.close()


def test_round3_manual_script_uses_real_chain_and_empty_source_message(monkeypatch):
    script_path = Path("scripts/p50_round3_manual_woo_sample.py").resolve()
    spec = importlib.util.spec_from_file_location("p50_round3_manual_woo_sample", script_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    fixed_task_id = "TASK-P50-R3-MANUAL-WOO-SAMPLE-20260414-120000"
    monkeypatch.setattr(mod, "get_shanghai_now", lambda: datetime(2026, 4, 14, 12, 0, 0))

    class _FakeIdem:
        def __init__(self):
            self._generate_task_id = lambda: fixed_task_id

        def check_and_create(self, message_id: str, raw_payload: dict):  # noqa: ARG002
            return False, None, fixed_task_id

    monkeypatch.setattr(mod, "idempotency_service", _FakeIdem())
    monkeypatch.setattr(mod.argparse.ArgumentParser, "parse_args", lambda _self: SimpleNamespace(sku="A001", base_url="http://local", poll_seconds=1.0))

    captured = {}

    def _run(*args):
        captured["args"] = args
        return None

    monkeypatch.setattr(mod, "process_ingress_message", SimpleNamespace(run=_run))

    class _FakeHTTPResponse:
        def __init__(self, body: dict):
            self._body = body

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def getcode(self):
            return 200

        def read(self):
            return json.dumps(self._body).encode("utf-8")

    def _fake_urlopen(req, timeout=10):  # noqa: ARG001
        url = req.full_url
        if url.endswith(f"/api/v1/tasks/{fixed_task_id}"):
            return _FakeHTTPResponse({"task_id": fixed_task_id, "status": "succeeded"})
        if url.endswith(f"/api/v1/tasks/{fixed_task_id}/steps"):
            return _FakeHTTPResponse(
                [
                    {
                        "step_code": "action_executed",
                        "detail": (
                            "provider_id=woo, readiness_status=ready, "
                            "endpoint_profile=real_admin_readonly_v1, session_injection_mode=cookie_or_header"
                        ),
                    }
                ]
            )
        raise RuntimeError(f"unexpected url: {url}")

    import urllib.request

    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)
    rc = mod.main()
    assert rc == 0
    # Celery wrapper signature in script branch: (task_id, cmd, open_id, source_message_id, chat_id)
    assert captured["args"][3] == ""
