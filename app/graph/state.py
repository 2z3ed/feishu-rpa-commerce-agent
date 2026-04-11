"""
LangGraph State Definition for Feishu RPA Commerce Agent

This module defines the state structure that flows through the LangGraph workflow.
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


@dataclass
class GraphState:
    """
    State that flows through the LangGraph workflow.
    
    Attributes:
        task_id: Unique task identifier
        source_message_id: Original message ID from Feishu
        source_chat_id: Chat ID where the message was sent
        user_open_id: User's open ID
        raw_text: Original text from the message
        normalized_text: Cleaned/normalized text
        intent_code: Identified intent (e.g., product.query_sku_status)
        slots: Extracted parameters for the intent
        execution_mode: How to execute (auto/api/rpa)
        result_summary: Summary of the execution result
        error_message: Error message if failed
        status: Current status of the task
        platform: Target platform (woo/odoo/auto)
    """
    task_id: str
    source_message_id: str = ""
    source_chat_id: str = ""
    user_open_id: str = ""
    raw_text: str = ""
    normalized_text: str = ""
    intent_code: str = "unknown"
    slots: Dict[str, Any] = field(default_factory=dict)
    execution_mode: str = "auto"
    result_summary: str = ""
    error_message: str = ""
    status: str = "processing"
    platform: str = "auto"
