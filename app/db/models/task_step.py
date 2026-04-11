"""Task step model."""
from sqlalchemy import Column, DateTime, String, Text
from app.db.base import Base
from app.core.time import get_shanghai_now


class TaskStep(Base):
    """Task step execution log."""
    
    __tablename__ = "task_steps"
    
    id = Column(String(50), primary_key=True, index=True)
    task_id = Column(String(50), index=True, nullable=False)
    step_code = Column(String(50), nullable=False)  # e.g., ingress_received, graph_started
    step_status = Column(String(20), nullable=False)  # success, failed, processing
    detail = Column(Text, default="")  # Additional details
    created_at = Column(DateTime, default=get_shanghai_now, nullable=False)
    
    def __repr__(self):
        return f"<TaskStep(id={self.id}, task_id={self.task_id}, step_code={self.step_code}, status={self.step_status})>"
