"""Finalize task result and persist status."""
from app.db.session import SessionLocal
from app.db.models import TaskRecord
from app.core.logging import logger
from app.core.time import get_shanghai_now


def finalize_result(state: dict) -> dict:
    """
    Finalize result and update task record.
    
    Args:
        state: Current graph state
        
    Returns:
        Updated state
    """
    task_id = state.get("task_id")
    if not task_id:
        logger.error("Task ID not provided")
        return state
    
    db = SessionLocal()
    try:
        task_record = db.query(TaskRecord).filter(TaskRecord.task_id == task_id).first()
        if not task_record:
            logger.error("Task record not found: task_id=%s", task_id)
            return state
        
        # Update task record with result
        status = state.get("status", "processing")
        # Support all valid statuses including succeeded
        valid_statuses = ["received", "queued", "processing", "succeeded", "failed", "awaiting_confirmation", "completed"]
        if status not in valid_statuses:
            logger.warning("Invalid status '%s', defaulting to 'processing'", status)
            status = "processing"
        task_record.status = status
        task_record.intent_text = state.get("normalized_text", "") or task_record.intent_text
        task_record.result_summary = state.get("result_summary", "")
        task_record.error_message = state.get("error_message", "")
        now_ts = get_shanghai_now()
        # Only set finished_at if not awaiting_confirmation
        if status != "awaiting_confirmation":
            task_record.finished_at = now_ts
        task_record.updated_at = now_ts
        
        # Store intent_code and slots in result_summary as prefix if needed
        intent_code = state.get("intent_code", "unknown")
        if intent_code != "unknown" and not task_record.result_summary.startswith(f"[{intent_code}]"):
            task_record.result_summary = f"[{intent_code}] {task_record.result_summary}"
        
        db.commit()
        
        intent_code = state.get("intent_code", "unknown")
        logger.info(
            "Task finalized: task_id=%s, status=%s, intent=%s",
            task_id, task_record.status, intent_code
        )
        
        return state
        
    except Exception as e:
        logger.error("Failed to finalize task: %s", str(e))
        db.rollback()
        return state
    finally:
        db.close()
