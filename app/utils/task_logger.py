"""
Task Step Logger

Utility for writing task execution steps to the database.
"""
import uuid
from app.db.session import SessionLocal
from app.db.models import TaskStep
from app.core.time import get_shanghai_now


def log_step(task_id: str, step_code: str, step_status: str, detail: str = ""):
    """
    Log a task execution step.
    
    Args:
        task_id: Task unique identifier
        step_code: Step code (e.g., ingress_received, graph_started)
        step_status: Step status (success, failed, processing)
        detail: Additional details
    """
    db = SessionLocal()
    try:
        step = TaskStep(
            id=str(uuid.uuid4()),
            task_id=task_id,
            step_code=step_code,
            step_status=step_status,
            detail=detail,
            created_at=get_shanghai_now()
        )
        db.add(step)
        db.commit()
    finally:
        db.close()
