"""
Parse Command Node

Parses and normalizes the raw text command.
"""
import re
from app.core.logging import logger


def parse_command(state: dict) -> dict:
    """
    Parse and normalize the raw text command.
    
    Args:
        state: Current graph state
        
    Returns:
        Updated state with normalized text
    """
    raw_text = state.get("raw_text", "")
    
    if not raw_text:
        logger.warning("Raw text is empty")
        state["normalized_text"] = ""
        return state
    
    # Step 1: Trim whitespace
    normalized = raw_text.strip()
    
    # Step 2: Remove any remaining @ mention prefixes (fallback)
    normalized = re.sub(r'^@_user_\d+\s*', '', normalized).strip()
    
    # Step 3: Remove extra whitespace
    normalized = re.sub(r'\s+', ' ', normalized)
    
    state["normalized_text"] = normalized
    
    logger.info("Command parsed: raw='%s' -> normalized='%s'", raw_text[:50], normalized[:50])
    
    return state
