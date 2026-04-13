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
                assert (d.get(k) or "").strip()
    finally:
        db.close()
