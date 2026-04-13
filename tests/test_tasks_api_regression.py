from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.tasks import get_db_session, router as tasks_router
from app.core.time import get_shanghai_now
from app.db.base import Base
from app.db.models import TaskRecord, TaskStep


def test_tasks_detail_and_steps_api_not_regressed():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    db = Session()
    try:
        db.add(
            TaskRecord(
                task_id="TASK-P50-001",
                source_platform="feishu",
                status="succeeded",
                intent_text="查 Odoo 里 SKU A001 的库存",
                result_summary="ok",
                created_at=get_shanghai_now(),
                updated_at=get_shanghai_now(),
            )
        )
        db.add(
            TaskStep(
                id="TASK-P50-STEP-1",
                task_id="TASK-P50-001",
                step_code="action_executed",
                step_status="success",
                detail="platform=odoo,provider_id=odoo,capability=warehouse.query_inventory",
            )
        )
        db.commit()

        app = FastAPI()
        app.include_router(tasks_router, prefix="/api/v1")

        def _override_db():
            try:
                yield db
            finally:
                pass

        app.dependency_overrides[get_db_session] = _override_db
        client = TestClient(app)

        detail_resp = client.get("/api/v1/tasks/TASK-P50-001")
        assert detail_resp.status_code == 200
        assert detail_resp.json()["task_id"] == "TASK-P50-001"

        steps_resp = client.get("/api/v1/tasks/TASK-P50-001/steps")
        assert steps_resp.status_code == 200
        body = steps_resp.json()
        assert len(body) == 1
        assert "provider_id=odoo" in body[0]["detail"]

        db.add(
            TaskRecord(
                task_id="TASK-P50-002",
                source_platform="feishu",
                status="failed",
                intent_text="查 Chatwoot 最近 5 个会话",
                result_summary="failed case",
                created_at=get_shanghai_now(),
                updated_at=get_shanghai_now(),
            )
        )
        db.commit()

        list_resp = client.get("/api/v1/tasks", params={"limit": 1})
        assert list_resp.status_code == 200
        arr = list_resp.json()
        assert isinstance(arr, list)
        assert len(arr) == 1

        filtered = client.get("/api/v1/tasks", params={"status": "succeeded", "limit": 10})
        assert filtered.status_code == 200
        body_f = filtered.json()
        assert isinstance(body_f, list)
        assert any(item["task_id"] == "TASK-P50-001" for item in body_f)
        assert all(item["status"] == "succeeded" for item in body_f)

        # list 接口结构回归：确保是 JSON 数组、limit 生效、status 过滤生效
        assert isinstance(list_resp.headers.get("content-type", ""), str)
        assert list_resp.headers.get("content-type", "").startswith("application/json")
    finally:
        db.close()
