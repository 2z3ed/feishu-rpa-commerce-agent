import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import TaskRecord


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_task_record_creation(db_session):
    task = TaskRecord(
        task_id="TASK-20260408-001",
        source_platform="feishu",
        source_message_id="msg_123",
        chat_id="chat_abc",
        user_open_id="open_xyz",
        task_type="ingress",
        intent_text="查询商品状态",
        status="received"
    )
    db_session.add(task)
    db_session.commit()

    result = db_session.query(TaskRecord).filter(
        TaskRecord.task_id == "TASK-20260408-001"
    ).first()

    assert result is not None
    assert result.task_id == "TASK-20260408-001"
    assert result.status == "received"
    assert result.intent_text == "查询商品状态"


def test_task_record_status_transitions(db_session):
    task = TaskRecord(
        task_id="TASK-20260408-002",
        source_platform="feishu",
        status="received"
    )
    db_session.add(task)
    db_session.commit()

    task.status = "queued"
    db_session.commit()

    task.status = "processing"
    db_session.commit()

    task.status = "succeeded"
    task.result_summary = "MVP ingress task accepted"
    db_session.commit()

    result = db_session.query(TaskRecord).filter(
        TaskRecord.task_id == "TASK-20260408-002"
    ).first()

    assert result.status == "succeeded"
    assert result.result_summary == "MVP ingress task accepted"