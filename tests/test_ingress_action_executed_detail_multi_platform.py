import importlib
import sys
import types

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import TaskRecord


def test_action_executed_detail_contains_multi_platform_fields(monkeypatch):
    # Keep this test self-contained when celery package is unavailable.
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

    ingress_tasks = importlib.import_module("app.tasks.ingress_tasks")

    engine = create_engine("sqlite:///:memory:")
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    db = Session()
    try:
        monkeypatch.setattr(ingress_tasks, "SessionLocal", lambda: db)
        monkeypatch.setattr(ingress_tasks, "try_write_bitable_ledger", lambda **kwargs: None)

        class _FakeClient:
            def send_text_reply(self, message_id: str, text: str) -> bool:
                return True

        monkeypatch.setattr(ingress_tasks, "FeishuClient", _FakeClient)

        logs: list[tuple[str, str, str]] = []

        def _capture(task_id: str, step_code: str, step_status: str, detail: str):
            logs.append((step_code, step_status, detail))

        monkeypatch.setattr(ingress_tasks, "log_step", _capture)

        platform_cases = [
            (
                "TASK-P50-DETAIL-WOO",
                "查 SKU A001 状态",
                {
                    "intent_code": "product.query_sku_status",
                    "execution_mode": "api",
                    "platform": "woo",
                    "execution_backend": "sandbox_http_client",
                    "client_profile": "sandbox_http@woo",
                    "response_mapper": "woo_mapper",
                    "request_adapter": "woo_request_adapter",
                    "auth_profile": "woo_auth_profile",
                    "provider_profile": "woo",
                    "credential_profile": "woo_credential_profile",
                    "provider_id": "woo",
                    "capability": "product.query_sku_status",
                    "readiness_status": "ready",
                    "endpoint_profile": "woo_products_v3",
                    "session_injection_mode": "header_or_query",
                    "result_summary": "ok",
                    "status": "succeeded",
                },
            ),
            (
                "TASK-P50-DETAIL-ODOO",
                "查 Odoo 里 SKU A001 的库存",
                {
                    "intent_code": "warehouse.query_inventory",
                    "execution_mode": "api",
                    "platform": "odoo",
                    "execution_backend": "internal_sandbox",
                    "client_profile": "sandbox_http@odoo_inventory",
                    "response_mapper": "odoo_mapper",
                    "request_adapter": "odoo_request_adapter",
                    "auth_profile": "odoo_auth_profile",
                    "provider_profile": "odoo",
                    "credential_profile": "odoo_credential_profile",
                    "provider_id": "odoo",
                    "capability": "warehouse.query_inventory",
                    "readiness_status": "ready",
                    "endpoint_profile": "odoo_product_stock_v1",
                    "session_injection_mode": "header",
                    "result_summary": "ok",
                    "status": "succeeded",
                },
            ),
            (
                "TASK-P50-DETAIL-CHATWOOT",
                "查 Chatwoot 最近 5 个会话",
                {
                    "intent_code": "customer.list_recent_conversations",
                    "execution_mode": "api",
                    "platform": "chatwoot",
                    "execution_backend": "internal_sandbox",
                    "client_profile": "sandbox_http@chatwoot_recent",
                    "response_mapper": "chatwoot_mapper",
                    "request_adapter": "chatwoot_request_adapter",
                    "auth_profile": "chatwoot_auth_profile",
                    "provider_profile": "chatwoot",
                    "credential_profile": "chatwoot_credential_profile",
                    "provider_id": "chatwoot",
                    "capability": "customer.list_recent_conversations",
                    "readiness_status": "ready",
                    "endpoint_profile": "chatwoot_recent_conversations_v1",
                    "session_injection_mode": "header",
                    "result_summary": "ok",
                    "status": "succeeded",
                },
            ),
        ]

        for task_id, cmd, graph_result in platform_cases:
            db.add(
                TaskRecord(
                    task_id=task_id,
                    source_platform="feishu",
                    status="queued",
                    intent_text=cmd,
                )
            )
            db.commit()
            monkeypatch.setattr(ingress_tasks.lang_graph, "invoke", lambda state, _r=graph_result: _r)
            ingress_tasks.process_ingress_message.run(
                None,
                task_id=task_id,
                intent_text=cmd,
                source_message_id="",
                chat_id="chat-1",
            )

        detail_logs = [d for code, _st, d in logs if code == "action_executed"]
        assert len(detail_logs) == 3
        required_keys = {
            "execution_mode",
            "provider_id",
            "capability",
            "readiness_status",
            "endpoint_profile",
            "session_injection_mode",
        }

        def _parse_kv(detail: str) -> dict[str, str]:
            out: dict[str, str] = {}
            for part in (detail or "").split(","):
                part = part.strip()
                if "=" not in part:
                    continue
                k, v = part.split("=", 1)
                out[k.strip()] = v.strip()
            return out

        parsed = [_parse_kv(d) for d in detail_logs]
        for d in parsed:
            # 同形状：字段名一致、都存在、都为非空字符串（P5.0 骨架验证要求）
            assert required_keys.issubset(set(d.keys()))
            for k in required_keys:
                assert isinstance(d.get(k), str)
                val = (d.get(k) or "").strip()
                assert val
                assert val.lower() not in {"none", "null"}

        # P6.0 收紧：Odoo readonly 关键字段不得出现 unknown/none
        d_odoo = parsed[1]
        assert d_odoo.get("execution_mode") == "api"
        assert d_odoo.get("provider_id") == "odoo"
        assert d_odoo.get("capability") == "warehouse.query_inventory"
        assert d_odoo.get("readiness_status") == "ready"
        assert (d_odoo.get("endpoint_profile") or "").strip().lower() not in {"", "none", "unknown"}
        assert (d_odoo.get("session_injection_mode") or "").strip().lower() not in {"", "none", "unknown"}
    finally:
        db.close()


def test_action_executed_detail_contains_confirm_audit_fields(monkeypatch):
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
    ingress_tasks = importlib.import_module("app.tasks.ingress_tasks")

    engine = create_engine("sqlite:///:memory:")
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    db = Session()
    try:
        monkeypatch.setattr(ingress_tasks, "SessionLocal", lambda: db)
        monkeypatch.setattr(ingress_tasks, "try_write_bitable_ledger", lambda **kwargs: None)
        monkeypatch.setattr(ingress_tasks, "FeishuClient", lambda: type("_F", (), {"send_text_reply": lambda *_a, **_k: True})())
        logs: list[tuple[str, str, str]] = []
        monkeypatch.setattr(ingress_tasks, "log_step", lambda task_id, code, status, detail: logs.append((code, status, detail)))

        task_id = "TASK-P53-DETAIL-CFM"
        db.add(
            TaskRecord(
                task_id=task_id,
                source_platform="feishu",
                status="queued",
                intent_text="确认执行 TASK-ORIG-1",
            )
        )
        db.commit()
        monkeypatch.setattr(
            ingress_tasks.lang_graph,
            "invoke",
            lambda state: {
                "intent_code": "system.confirm_task",
                "execution_mode": "rpa",
                "platform": "woo",
                "execution_backend": "rpa_browser_real",
                "client_profile": "rpa_runner",
                "response_mapper": "none",
                "request_adapter": "none",
                "auth_profile": "none",
                "provider_profile": "none",
                "credential_profile": "none",
                "provider_id": "woo",
                "capability": "none",
                "readiness_status": "unknown",
                "endpoint_profile": "none",
                "session_injection_mode": "none",
                "result_summary": "确认失败",
                "status": "failed",
                "target_task_id": "TASK-ORIG-1",
                "original_update_task_id": "TASK-ORIG-1",
                "confirm_task_id": task_id,
                "parsed_result": {
                    "failure_layer": "confirm_target_already_consumed",
                    "operation_result": "confirm_blocked_noop",
                    "verify_passed": False,
                    "verify_reason": "already_consumed_status=succeeded",
                    "old_price": None,
                    "new_price": None,
                    "post_save_price": None,
                    "target_task_id": "TASK-ORIG-1",
                    "original_update_task_id": "TASK-ORIG-1",
                    "confirm_task_id": task_id,
                },
            },
        )
        ingress_tasks.process_ingress_message.run(
            None,
            task_id=task_id,
            intent_text="确认执行 TASK-ORIG-1",
            source_message_id="",
            chat_id="chat-1",
        )
        detail_logs = [d for code, _st, d in logs if code == "action_executed"]
        assert len(detail_logs) == 1
        detail = detail_logs[0]
        assert "failure_layer=confirm_target_already_consumed" in detail
        assert "operation_result=confirm_blocked_noop" in detail
        assert "target_task_id=TASK-ORIG-1" in detail
        assert "original_update_task_id=TASK-ORIG-1" in detail
        assert f"confirm_task_id={task_id}" in detail
    finally:
        db.close()


def test_action_executed_detail_contains_yingdao_bridge_fields(monkeypatch):
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
    ingress_tasks = importlib.import_module("app.tasks.ingress_tasks")

    engine = create_engine("sqlite:///:memory:")
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    db = Session()
    try:
        monkeypatch.setattr(ingress_tasks, "SessionLocal", lambda: db)
        monkeypatch.setattr(ingress_tasks, "try_write_bitable_ledger", lambda **kwargs: None)
        monkeypatch.setattr(ingress_tasks, "FeishuClient", lambda: type("_F", (), {"send_text_reply": lambda *_a, **_k: True})())
        logs: list[tuple[str, str, str]] = []
        monkeypatch.setattr(ingress_tasks, "log_step", lambda task_id, code, status, detail: logs.append((code, status, detail)))

        task_id = "TASK-P70-DETAIL-BRIDGE"
        db.add(TaskRecord(task_id=task_id, source_platform="feishu", status="queued", intent_text="确认执行 TASK-ORIG-2"))
        db.commit()
        monkeypatch.setattr(
            ingress_tasks.lang_graph,
            "invoke",
            lambda state: {
                "intent_code": "system.confirm_task",
                "execution_mode": "api",
                "platform": "odoo",
                "execution_backend": "yingdao_bridge",
                "client_profile": "yingdao_runner",
                "provider_id": "odoo",
                "capability": "warehouse.adjust_inventory",
                "readiness_status": "ready",
                "endpoint_profile": "odoo_product_stock_v1",
                "session_injection_mode": "header",
                "result_summary": "ok",
                "status": "succeeded",
                "parsed_result": {
                    "operation_result": "write_adjust_inventory",
                    "verify_passed": True,
                    "verify_reason": "ok",
                    "failure_layer": "",
                    "confirm_backend": "yingdao_bridge",
                    "rpa_vendor": "yingdao",
                    "raw_result_path": "/tmp/yingdao/result.json",
                    "target_task_id": "TASK-ORIG-2",
                    "confirm_task_id": task_id,
                    "original_update_task_id": "TASK-ORIG-2",
                    "evidence_paths": ["/tmp/yingdao/shot.png"],
                    "page_url": "http://127.0.0.1:8000/api/v1/internal/rpa-sandbox/admin-like/catalog?sku=A001",
                    "page_profile": "internal_inventory_adjust_v1",
                    "page_steps": ["open_page", "locate_sku", "submit", "read_page_echo"],
                    "page_evidence_count": 1,
                    "page_failure_code": "",
                },
            },
        )
        ingress_tasks.process_ingress_message.run(
            None,
            task_id=task_id,
            intent_text="确认执行 TASK-ORIG-2",
            source_message_id="",
            chat_id="chat-1",
        )
        detail_logs = [d for code, _st, d in logs if code == "action_executed"]
        assert len(detail_logs) == 1
        detail = detail_logs[0]
        assert "confirm_backend=yingdao_bridge" in detail
        assert "rpa_vendor=yingdao" in detail
        assert "raw_result_path=/tmp/yingdao/result.json" in detail
        assert "operation_result=write_adjust_inventory" in detail
        assert "verify_passed=True" in detail
        assert "page_profile=internal_inventory_adjust_v1" in detail
        assert "page_steps=open_page|locate_sku|submit|read_page_echo" in detail
    finally:
        db.close()


def test_action_executed_detail_contains_yingdao_bridge_timeout_fields(monkeypatch):
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
    ingress_tasks = importlib.import_module("app.tasks.ingress_tasks")

    engine = create_engine("sqlite:///:memory:")
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    db = Session()
    try:
        monkeypatch.setattr(ingress_tasks, "SessionLocal", lambda: db)
        monkeypatch.setattr(ingress_tasks, "try_write_bitable_ledger", lambda **kwargs: None)
        monkeypatch.setattr(ingress_tasks, "FeishuClient", lambda: type("_F", (), {"send_text_reply": lambda *_a, **_k: True})())
        logs: list[tuple[str, str, str]] = []
        monkeypatch.setattr(ingress_tasks, "log_step", lambda task_id, code, status, detail: logs.append((code, status, detail)))

        task_id = "TASK-P70-DETAIL-BRIDGE-TIMEOUT"
        db.add(TaskRecord(task_id=task_id, source_platform="feishu", status="queued", intent_text="确认执行 TASK-ORIG-3"))
        db.commit()
        monkeypatch.setattr(
            ingress_tasks.lang_graph,
            "invoke",
            lambda state: {
                "intent_code": "system.confirm_task",
                "execution_mode": "api",
                "platform": "odoo",
                "execution_backend": "yingdao_bridge",
                "client_profile": "yingdao_runner",
                "provider_id": "odoo",
                "capability": "warehouse.adjust_inventory",
                "readiness_status": "ready",
                "endpoint_profile": "odoo_product_stock_v1",
                "session_injection_mode": "header",
                "result_summary": "确认失败",
                "status": "failed",
                "parsed_result": {
                    "operation_result": "write_adjust_inventory_bridge_timeout",
                    "verify_passed": False,
                    "verify_reason": "bridge_request_timeout",
                    "failure_layer": "bridge_timeout",
                    "confirm_backend": "yingdao_bridge",
                    "rpa_vendor": "yingdao",
                    "raw_result_path": "",
                    "target_task_id": "TASK-ORIG-3",
                    "confirm_task_id": task_id,
                    "original_update_task_id": "TASK-ORIG-3",
                    "evidence_paths": [],
                    "page_url": "http://127.0.0.1:8000/api/v1/internal/rpa-sandbox/admin-like/catalog?sku=A001",
                    "page_profile": "internal_inventory_adjust_v1",
                    "page_steps": ["open_page"],
                    "page_evidence_count": 0,
                    "page_failure_code": "page_timeout",
                },
            },
        )
        ingress_tasks.process_ingress_message.run(
            None,
            task_id=task_id,
            intent_text="确认执行 TASK-ORIG-3",
            source_message_id="",
            chat_id="chat-1",
        )
        detail_logs = [d for code, _st, d in logs if code == "action_executed"]
        assert len(detail_logs) == 1
        detail = detail_logs[0]
        assert "confirm_backend=yingdao_bridge" in detail
        assert "operation_result=write_adjust_inventory_bridge_timeout" in detail
        assert "verify_passed=False" in detail
        assert "verify_reason=bridge_request_timeout" in detail
        assert "failure_layer=bridge_timeout" in detail
        assert "page_failure_code=page_timeout" in detail
    finally:
        db.close()
