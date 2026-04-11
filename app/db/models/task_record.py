from sqlalchemy import Column, Integer, String, DateTime, Text, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base import BaseModel
from app.core.constants import SourcePlatform, TaskStatus


class TaskRecord(BaseModel):
    __tablename__ = "task_records"

    task_id = Column(String(64), nullable=False, unique=True, index=True)
    source_platform = Column(String(32), nullable=False, index=True)
    source_message_id = Column(String(128), nullable=True, index=True)
    chat_id = Column(String(128), nullable=True, index=True)
    user_open_id = Column(String(128), nullable=True, index=True)
    task_type = Column(String(64), nullable=True)
    intent_text = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default=TaskStatus.RECEIVED.value, index=True)
    result_summary = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    accepted_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    target_task_id = Column(String(64), nullable=True, index=True)  # For confirmation tasks to point to original task

    # 删除这行，避免循环依赖
    # idempotency_record = relationship("MessageIdempotency", back_populates="task_record")

    def __repr__(self):
        return f"<TaskRecord(id={self.id}, task_id={self.task_id}, status={self.status})>"