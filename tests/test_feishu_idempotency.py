import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import MessageIdempotency


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_message_idempotency_creation(db_session):
    idempotency = MessageIdempotency(
        source_platform="feishu",
        message_id="test_msg_123",
        chat_id="chat_abc",
        sender_open_id="open_xyz",
        raw_event_type="im.message.receive_v1",
        status="pending",
        task_id="TASK-20260408-ABC123"
    )
    db_session.add(idempotency)
    db_session.commit()

    result = db_session.query(MessageIdempotency).filter(
        MessageIdempotency.message_id == "test_msg_123"
    ).first()

    assert result is not None
    assert result.message_id == "test_msg_123"
    assert result.task_id == "TASK-20260408-ABC123"
    assert result.status == "pending"


def test_message_idempotency_unique_constraint(db_session):
    idempotency1 = MessageIdempotency(
        source_platform="feishu",
        message_id="test_msg_456",
        task_id="TASK-1"
    )
    db_session.add(idempotency1)
    db_session.commit()

    idempotency2 = MessageIdempotency(
        source_platform="feishu",
        message_id="test_msg_456",
        task_id="TASK-2"
    )
    db_session.add(idempotency2)
    
    with pytest.raises(Exception):
        db_session.commit()