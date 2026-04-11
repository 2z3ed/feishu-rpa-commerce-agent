from sqlalchemy import Column, Integer, String, DateTime, Text, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base import BaseModel
from app.core.constants import SourcePlatform


class MessageIdempotency(BaseModel):
    __tablename__ = "message_idempotency"

    source_platform = Column(String(32), nullable=False, index=True)
    message_id = Column(String(128), nullable=False, unique=True, index=True)
    idempotency_key = Column(String(256), nullable=True, index=True)
    chat_id = Column(String(128), nullable=True, index=True)
    sender_open_id = Column(String(128), nullable=True, index=True)
    raw_event_type = Column(String(64), nullable=True)
    status = Column(String(32), nullable=False, default="pending")
    task_id = Column(String(64), nullable=True, index=True)
    raw_payload_json = Column(Text, nullable=True)

    def __repr__(self):
        return f"<MessageIdempotency(id={self.id}, message_id={self.message_id}, status={self.status})>"