"""Task query APIs for records and execution steps."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import TaskRecord, TaskStep
from app.core.time import to_shanghai_iso

router = APIRouter(prefix="/tasks", tags=["tasks"])


def get_db_session():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class TaskListItemResponse(BaseModel):
    task_id: str
    status: str
    intent_text: Optional[str] = None
    result_summary: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class TaskDetailResponse(BaseModel):
    task_id: str
    status: str
    source_message_id: Optional[str] = None
    chat_id: Optional[str] = None
    user_open_id: Optional[str] = None
    intent_text: Optional[str] = None
    target_task_id: Optional[str] = None
    result_summary: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class TaskStepResponse(BaseModel):
    id: str
    task_id: str
    step_code: str
    step_status: str
    detail: str
    created_at: Optional[str] = None


def _table_has_column(db: Session, table_name: str, column_name: str) -> bool:
    """Avoid 500s when model/schema drift exists in current DB."""
    try:
        columns = inspect(db.bind).get_columns(table_name)
    except Exception:
        return False
    return any(col.get("name") == column_name for col in columns)


@router.get("/{task_id}")
def get_task(task_id: str, db: Session = Depends(get_db_session)) -> TaskDetailResponse:
    """
    Get task details by task_id.
    
    Args:
        task_id: Task unique identifier
        db: Database session
        
    Returns:
        Task details including status, result, timestamps, etc.
        
    Raises:
        HTTPException: 404 if task not found
    """
    has_target_task_id = _table_has_column(db, "task_records", "target_task_id")
    query_columns = [
        TaskRecord.task_id,
        TaskRecord.status,
        TaskRecord.source_message_id,
        TaskRecord.chat_id,
        TaskRecord.user_open_id,
        TaskRecord.intent_text,
        TaskRecord.result_summary,
        TaskRecord.error_message,
        TaskRecord.started_at,
        TaskRecord.finished_at,
        TaskRecord.created_at,
        TaskRecord.updated_at,
    ]
    if has_target_task_id:
        query_columns.append(TaskRecord.target_task_id)

    row = (
        db.query(*query_columns)
        .filter(TaskRecord.task_id == task_id)
        .first()
    )

    task = row._asdict() if row else None
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    return TaskDetailResponse(
        task_id=task["task_id"],
        status=task["status"],
        source_message_id=task["source_message_id"],
        chat_id=task["chat_id"],
        user_open_id=task["user_open_id"],
        intent_text=task["intent_text"],
        target_task_id=task.get("target_task_id"),
        result_summary=task["result_summary"],
        error_message=task["error_message"],
        started_at=to_shanghai_iso(task["started_at"]),
        finished_at=to_shanghai_iso(task["finished_at"]),
        created_at=to_shanghai_iso(task["created_at"]),
        updated_at=to_shanghai_iso(task["updated_at"]),
    )


@router.get("/")
@router.get("", include_in_schema=False)
def list_tasks(
    status: Optional[str] = None,
    intent: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db_session)
) -> list[TaskListItemResponse]:
    """
    List tasks with optional filters.
    
    Args:
        status: Filter by task status
        intent: Filter by intent text
        limit: Maximum number of tasks to return (default: 20)
        db: Database session
        
    Returns:
        List of tasks ordered by creation time (newest first)
    """
    query = db.query(
        TaskRecord.task_id,
        TaskRecord.status,
        TaskRecord.intent_text,
        TaskRecord.result_summary,
        TaskRecord.created_at,
        TaskRecord.updated_at,
    )

    if status:
        query = query.filter(TaskRecord.status == status)

    if intent:
        query = query.filter(TaskRecord.intent_text.ilike(f"%{intent}%"))

    rows = query.order_by(TaskRecord.created_at.desc()).limit(limit).all()
    if not rows:
        return []

    return [
        TaskListItemResponse(
            task_id=row.task_id,
            status=row.status,
            intent_text=row.intent_text,
            result_summary=row.result_summary,
            created_at=to_shanghai_iso(row.created_at),
            updated_at=to_shanghai_iso(row.updated_at),
        )
        for row in rows
    ]


@router.get("/{task_id}/steps")
def get_task_steps(task_id: str, db: Session = Depends(get_db_session)) -> list[TaskStepResponse]:
    """
    Get steps for a specific task.
    
    Args:
        task_id: Task unique identifier
        db: Database session
        
    Returns:
        List of task steps ordered by creation time (oldest first)
    """
    task = (
        db.query(TaskRecord.task_id)
        .filter(TaskRecord.task_id == task_id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    steps = (
        db.query(
            TaskStep.id,
            TaskStep.task_id,
            TaskStep.step_code,
            TaskStep.step_status,
            TaskStep.detail,
            TaskStep.created_at,
        )
        .filter(TaskStep.task_id == task_id)
        .order_by(TaskStep.created_at.asc())
        .all()
    )
    if not steps:
        return []

    return [
        TaskStepResponse(
            id=step.id,
            task_id=step.task_id,
            step_code=step.step_code,
            step_status=step.step_status,
            detail=step.detail or "",
            created_at=to_shanghai_iso(step.created_at),
        )
        for step in steps
    ]
