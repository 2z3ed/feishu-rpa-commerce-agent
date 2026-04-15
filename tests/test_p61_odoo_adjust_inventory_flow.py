import types
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import TaskRecord
from app.graph.nodes.execute_action import execute_action
from app.graph.nodes.finalize_result import finalize_result
from app.core.config import settings


def test_p61_adjust_inventory_requires_confirmation_and_confirm_is_unique(monkeypatch):
    # Keep this test self-contained when optional deps are unavailable.
    fake_lark = types.ModuleType("lark_oapi")

    class _Client:
        pass

    fake_lark.Client = _Client
    monkeypatch.setitem(sys.modules, "lark_oapi", fake_lark)
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

    engine = create_engine("sqlite:///:memory:")
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    db = Session()
    try:
        # Ensure internal sandbox is enabled for controlled write.
        old_sandbox = settings.ENABLE_INTERNAL_SANDBOX_API
        settings.ENABLE_INTERNAL_SANDBOX_API = True

        # Patch SessionLocal in all involved modules to use the same in-memory DB.
        import app.db.session as db_session
        import app.utils.task_logger as task_logger
        import app.graph.nodes.execute_action as execute_action_mod
        import app.graph.nodes.finalize_result as finalize_mod

        monkeypatch.setattr(db_session, "SessionLocal", lambda: db)
        monkeypatch.setattr(task_logger, "SessionLocal", lambda: db)
        monkeypatch.setattr(execute_action_mod, "SessionLocal", lambda: db)
        monkeypatch.setattr(finalize_mod, "SessionLocal", lambda: db)

        orig_task_id = "TASK-P61-ORIG-1"
        confirm_task_id_1 = "TASK-P61-CFM-1"
        confirm_task_id_2 = "TASK-P61-CFM-2"

        db.add(TaskRecord(task_id=orig_task_id, source_platform="feishu", status="queued", intent_text=""))
        db.add(TaskRecord(task_id=confirm_task_id_1, source_platform="feishu", status="queued", intent_text=""))
        db.add(TaskRecord(task_id=confirm_task_id_2, source_platform="feishu", status="queued", intent_text=""))
        db.commit()

        # Original high-risk action must not execute directly.
        st_orig = {
            "task_id": orig_task_id,
            "intent_code": "warehouse.adjust_inventory",
            "slots": {"sku": "A001", "delta": 5, "platform": "odoo"},
            "status": "processing",
        }
        out_orig = execute_action(st_orig)
        assert out_orig["status"] == "awaiting_confirmation"
        assert out_orig["execution_mode"] == "api"
        assert "请回复：确认执行" in (out_orig.get("result_summary") or "")
        finalize_result(out_orig)

        rec = db.query(TaskRecord).filter(TaskRecord.task_id == orig_task_id).first()
        assert rec is not None
        assert rec.status == "awaiting_confirmation"

        # Confirm should execute controlled write and post-check.
        st_c1 = {
            "task_id": confirm_task_id_1,
            "intent_code": "system.confirm_task",
            "slots": {"task_id": orig_task_id},
            "raw_text": f"确认执行 {orig_task_id}",
            "status": "processing",
        }
        out_c1 = execute_action(st_c1)
        assert out_c1["status"] in {"succeeded", "failed"}
        pr = out_c1.get("parsed_result") or {}
        assert pr.get("target_task_id") == orig_task_id
        assert pr.get("confirm_task_id") == confirm_task_id_1
        assert pr.get("confirm_backend") == "internal_sandbox"
        assert pr.get("operation_result") in {
            "write_adjust_inventory",
            "write_adjust_inventory_verify_failed",
            "write_adjust_inventory_failed",
        }
        assert "verify_passed" in pr
        assert "verify_reason" in pr
        finalize_result(out_c1)

        rec2 = db.query(TaskRecord).filter(TaskRecord.task_id == orig_task_id).first()
        assert rec2 is not None
        assert rec2.status in {"succeeded", "failed"}

        # Second confirm on same original must be blocked (唯一放行 + 幂等).
        st_c2 = {
            "task_id": confirm_task_id_2,
            "intent_code": "system.confirm_task",
            "slots": {"task_id": orig_task_id},
            "raw_text": f"确认执行 {orig_task_id}",
            "status": "processing",
        }
        out_c2 = execute_action(st_c2)
        assert out_c2["status"] == "failed"
        pr2 = out_c2.get("parsed_result") or {}
        assert pr2.get("failure_layer") == "confirm_target_already_consumed"
        assert pr2.get("operation_result") == "confirm_blocked_noop"
        finalize_result(out_c2)
    finally:
        settings.ENABLE_INTERNAL_SANDBOX_API = old_sandbox
        db.close()


def test_p61_confirm_fails_when_risk_context_missing(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    db = Session()
    try:
        old_sandbox = settings.ENABLE_INTERNAL_SANDBOX_API
        settings.ENABLE_INTERNAL_SANDBOX_API = True

        import app.db.session as db_session
        import app.utils.task_logger as task_logger
        import app.graph.nodes.execute_action as execute_action_mod
        import app.graph.nodes.finalize_result as finalize_mod

        monkeypatch.setattr(db_session, "SessionLocal", lambda: db)
        monkeypatch.setattr(task_logger, "SessionLocal", lambda: db)
        monkeypatch.setattr(execute_action_mod, "SessionLocal", lambda: db)
        monkeypatch.setattr(finalize_mod, "SessionLocal", lambda: db)

        orig_task_id = "TASK-P61-ORIG-NOCTX"
        confirm_task_id = "TASK-P61-CFM-NOCTX"

        # Create an awaiting_confirmation target task that looks like adjust_inventory,
        # but intentionally has no risk_context TaskStep.
        db.add(
            TaskRecord(
                task_id=orig_task_id,
                source_platform="feishu",
                status="awaiting_confirmation",
                intent_text="调整 Odoo SKU A001 库存 +5",
                result_summary="[warehouse.adjust_inventory] placeholder",
            )
        )
        db.add(TaskRecord(task_id=confirm_task_id, source_platform="feishu", status="queued", intent_text=""))
        db.commit()

        st_c = {
            "task_id": confirm_task_id,
            "intent_code": "system.confirm_task",
            "slots": {"task_id": orig_task_id},
            "raw_text": f"确认执行 {orig_task_id}",
            "status": "processing",
        }
        out = execute_action(st_c)
        assert out["status"] == "failed"
        pr = out.get("parsed_result") or {}
        assert pr.get("failure_layer") == "confirm_context_missing"
        assert pr.get("operation_result") == "confirm_blocked_noop"
        assert pr.get("verify_passed") is False
        assert str(pr.get("verify_reason") or "").startswith("confirm_context_missing")
        # Prove no fallback: missing ctx yields a dedicated failure layer (not Woo parsing errors).
        assert "risk_context" in (out.get("error_message") or "") or "confirm_context_missing" in (
            out.get("error_message") or ""
        )
        finalize_result(out)
    finally:
        settings.ENABLE_INTERNAL_SANDBOX_API = old_sandbox
        db.close()


def test_p61_confirm_fails_when_risk_context_invalid_json(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    db = Session()
    try:
        old_sandbox = settings.ENABLE_INTERNAL_SANDBOX_API
        settings.ENABLE_INTERNAL_SANDBOX_API = True

        import app.db.session as db_session
        import app.utils.task_logger as task_logger
        import app.graph.nodes.execute_action as execute_action_mod
        import app.graph.nodes.finalize_result as finalize_mod

        monkeypatch.setattr(db_session, "SessionLocal", lambda: db)
        monkeypatch.setattr(task_logger, "SessionLocal", lambda: db)
        monkeypatch.setattr(execute_action_mod, "SessionLocal", lambda: db)
        monkeypatch.setattr(finalize_mod, "SessionLocal", lambda: db)

        from app.db.models import TaskStep
        from app.core.time import get_shanghai_now

        orig_task_id = "TASK-P61-ORIG-BADJSON"
        confirm_task_id = "TASK-P61-CFM-BADJSON"
        db.add(
            TaskRecord(
                task_id=orig_task_id,
                source_platform="feishu",
                status="awaiting_confirmation",
                intent_text="调整 Odoo SKU A001 库存 +5",
                result_summary="[warehouse.adjust_inventory] placeholder",
            )
        )
        db.add(
            TaskStep(
                id="step-badjson",
                task_id=orig_task_id,
                step_code="risk_context",
                step_status="success",
                detail="{not a json",
                created_at=get_shanghai_now(),
            )
        )
        db.add(TaskRecord(task_id=confirm_task_id, source_platform="feishu", status="queued", intent_text=""))
        db.commit()

        out = execute_action(
            {
                "task_id": confirm_task_id,
                "intent_code": "system.confirm_task",
                "slots": {"task_id": orig_task_id},
                "raw_text": f"确认执行 {orig_task_id}",
                "status": "processing",
            }
        )
        assert out["status"] == "failed"
        pr = out.get("parsed_result") or {}
        assert pr.get("failure_layer") == "confirm_context_invalid_json"
        assert pr.get("operation_result") == "confirm_blocked_noop"
        assert pr.get("verify_passed") is False
        assert str(pr.get("verify_reason") or "").startswith("confirm_context_invalid_json")
        finalize_result(out)
    finally:
        settings.ENABLE_INTERNAL_SANDBOX_API = old_sandbox
        db.close()


def test_p61_confirm_fails_when_risk_context_missing_keys(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    db = Session()
    try:
        old_sandbox = settings.ENABLE_INTERNAL_SANDBOX_API
        settings.ENABLE_INTERNAL_SANDBOX_API = True

        import app.db.session as db_session
        import app.utils.task_logger as task_logger
        import app.graph.nodes.execute_action as execute_action_mod
        import app.graph.nodes.finalize_result as finalize_mod

        monkeypatch.setattr(db_session, "SessionLocal", lambda: db)
        monkeypatch.setattr(task_logger, "SessionLocal", lambda: db)
        monkeypatch.setattr(execute_action_mod, "SessionLocal", lambda: db)
        monkeypatch.setattr(finalize_mod, "SessionLocal", lambda: db)

        from app.db.models import TaskStep
        from app.core.time import get_shanghai_now

        orig_task_id = "TASK-P61-ORIG-MISSKEY"
        confirm_task_id = "TASK-P61-CFM-MISSKEY"
        db.add(
            TaskRecord(
                task_id=orig_task_id,
                source_platform="feishu",
                status="awaiting_confirmation",
                intent_text="调整 Odoo SKU A001 库存 +5",
                result_summary="[warehouse.adjust_inventory] placeholder",
            )
        )
        # Missing sku/delta/target_inventory
        db.add(
            TaskStep(
                id="step-misskey",
                task_id=orig_task_id,
                step_code="risk_context",
                step_status="success",
                detail='{"provider_id":"odoo","capability":"warehouse.adjust_inventory"}',
                created_at=get_shanghai_now(),
            )
        )
        db.add(TaskRecord(task_id=confirm_task_id, source_platform="feishu", status="queued", intent_text=""))
        db.commit()

        out = execute_action(
            {
                "task_id": confirm_task_id,
                "intent_code": "system.confirm_task",
                "slots": {"task_id": orig_task_id},
                "raw_text": f"确认执行 {orig_task_id}",
                "status": "processing",
            }
        )
        assert out["status"] == "failed"
        pr = out.get("parsed_result") or {}
        assert pr.get("failure_layer") == "confirm_context_incomplete"
        assert pr.get("operation_result") == "confirm_blocked_noop"
        assert pr.get("verify_passed") is False
        vr = str(pr.get("verify_reason") or "")
        assert vr.startswith("confirm_context_incomplete:missing=")
        assert "sku" in vr
        assert "delta" in vr
        assert "target_inventory" in vr
        finalize_result(out)
    finally:
        settings.ENABLE_INTERNAL_SANDBOX_API = old_sandbox
        db.close()
