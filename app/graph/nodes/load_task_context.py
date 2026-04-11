"""
Load Task Context Node

Loads the task record from database and initializes the graph state.
"""
from datetime import datetime
from app.db.session import SessionLocal
from app.db.models import TaskRecord
from app.graph.state import GraphState
from app.core.logging import logger


def load_task_context(state: dict) -> dict:
    """
    Load task context from database.
    
    Args:
        state: Current graph state
        
    Returns:
        Updated state with task record data
    """
    task_id = state.get("task_id")
    if not task_id:
        logger.error("Task ID not provided in state")
        state["error_message"] = "Task ID not provided"
        state["status"] = "failed"
        return state
    
    db = SessionLocal()
    try:
        task_record = db.query(TaskRecord).filter(TaskRecord.task_id == task_id).first()
        if not task_record:
            logger.error("Task record not found: task_id=%s", task_id)
            state["error_message"] = f"Task record not found: {task_id}"
            state["status"] = "failed"
            return state
        
        logger.info("Task record loaded: task_id=%s, status=%s", task_id, task_record.status)
        
        # Update state with task record data
        state["source_message_id"] = task_record.source_message_id or ""
        state["source_chat_id"] = task_record.chat_id or ""
        state["user_open_id"] = task_record.user_open_id or ""
        state["raw_text"] = task_record.intent_text or ""
        state["normalized_text"] = task_record.intent_text or ""
        
        return state
        
    finally:
        db.close()
