"""
Resolve Intent Node

Identifies the intent from the normalized text using rule-based matching.
"""
import re
from typing import Optional, Tuple, Dict, Any
from app.core.logging import logger


def resolve_intent(state: dict) -> dict:
    """
    Resolve intent from normalized text.
    
    Args:
        state: Current graph state
        
    Returns:
        Updated state with intent_code and slots
    """
    normalized_text = state.get("normalized_text", "")
    
    if not normalized_text:
        logger.warning("Normalized text is empty")
        state["intent_code"] = "unknown"
        state["slots"] = {}
        return state
    
    # Try to match confirmation command first
    intent_code, slots = try_match_confirmation_command(normalized_text)
    
    # Try to match product.query_sku_status
    if not intent_code:
        intent_code, slots = try_match_warehouse_query_inventory(normalized_text)

    # Try to match chatwoot recent conversations
    if not intent_code:
        intent_code, slots = try_match_customer_list_recent_conversations(normalized_text)

    # Try to match product.query_sku_status
    if not intent_code:
        intent_code, slots = try_match_product_query_sku_status(normalized_text)
    
    # Try to match product.update_price
    if not intent_code:
        intent_code, slots = try_match_product_update_price(normalized_text)
    
    if intent_code:
        state["intent_code"] = intent_code
        state["slots"] = slots
        logger.info("Intent resolved: intent_code=%s, slots=%s", intent_code, slots)
    else:
        state["intent_code"] = "unknown"
        state["slots"] = {}
        logger.info("Unknown intent: text='%s'", normalized_text[:100])
    
    return state


def try_match_product_query_sku_status(text: str) -> Tuple[Optional[str], Dict[str, Any]]:
    """
    Try to match product.query_sku_status intent.
    
    Patterns:
    - 查询 SKU A001 状态
    - 帮我查一下 SKU A001
    - 看一下商品 A001 库存和状态
    - 查 SKU A001
    - 查询 A001 状态
    
    Args:
        text: Normalized text
        
    Returns:
        Tuple of (intent_code, slots) or (None, {}) if not matched
    """
    # Pattern 1: SKU followed by alphanumeric code (e.g., "SKU A001" or "SKUA001")
    sku_pattern = r'(?:SKU|商品 | 产品)\s*([A-Z0-9]+)'
    sku_match = re.search(sku_pattern, text, re.IGNORECASE)
    
    # Pattern 2: Just alphanumeric code if no SKU prefix (e.g., "A001")
    if not sku_match:
        sku_pattern = r'\b([A-Z][0-9]+)\b'
        sku_match = re.search(sku_pattern, text, re.IGNORECASE)
    
    if sku_match:
        sku = sku_match.group(1)
        
        # Check if text contains query-related keywords
        query_keywords = ['查询', '查', '看一下', '看看', '状态', '库存']
        has_query_keyword = any(keyword in text for keyword in query_keywords)
        
        if has_query_keyword:
            # Extract platform if mentioned
            platform = None
            if 'woo' in text.lower() or 'woocommerce' in text.lower():
                platform = 'woo'
            elif 'odoo' in text.lower():
                platform = 'odoo'
            
            slots = {'sku': sku}
            if platform:
                slots['platform'] = platform
            
            return 'product.query_sku_status', slots
    
    return None, {}


def try_match_warehouse_query_inventory(text: str) -> tuple[str | None, dict]:
    """Match warehouse.query_inventory for minimal Odoo readonly entry."""
    inventory_keywords = ["库存", "库存数量"]
    query_keywords = ["查", "查询", "看", "查看"]
    has_inventory = any(k in text for k in inventory_keywords)
    has_query = any(k in text for k in query_keywords)
    if not (has_inventory and has_query):
        return None, {}
    if "odoo" not in text.lower():
        return None, {}

    sku_match = re.search(r"(?:SKU|商品|产品)?\s*([A-Z][0-9]+)", text, re.IGNORECASE)
    if not sku_match:
        return None, {}
    return "warehouse.query_inventory", {"sku": sku_match.group(1), "platform": "odoo"}


def try_match_customer_list_recent_conversations(text: str) -> tuple[str | None, dict]:
    """Match customer.list_recent_conversations for minimal Chatwoot readonly entry."""
    if "chatwoot" not in text.lower():
        return None, {}
    if "会话" not in text:
        return None, {}
    if not any(k in text for k in ("最近", "最新", "列表", "列出", "查", "查询")):
        return None, {}

    limit_match = re.search(r"(\d+)\s*个", text)
    limit = int(limit_match.group(1)) if limit_match else 5
    if limit <= 0:
        limit = 5
    return "customer.list_recent_conversations", {"limit": limit, "platform": "chatwoot"}


def try_match_confirmation_command(text: str) -> tuple[str | None, dict]:
    """
    Try to match confirmation command.
    
    Patterns:
    - 确认执行 TASK-20260409-E4D73C
    - 确认执行 TASK-20260409E4D73C
    - 确认 TASK-20260409-E4D73C
    - 执行 TASK-20260409-E4D73C
    
    Args:
        text: Normalized text
        
    Returns:
        Tuple of (intent_code, slots) or (None, {}) if not matched
    """
    # Pattern for task confirmation - support full task_id format: TASK-20260409-E4D73C
    # Format: TASK-YYYYMMDD-XXXXXX (digits and uppercase letters)
    confirmation_pattern = r'(?:确认执行 | 确认 | 执行)\s*(TASK-\d{8}-[A-Z0-9]+)'
    confirmation_match = re.search(confirmation_pattern, text, re.IGNORECASE)
    
    if confirmation_match:
        task_id = confirmation_match.group(1)
        slots = {'task_id': task_id}
        return 'system.confirm_task', slots
    
    return None, {}


def try_match_product_update_price(text: str) -> tuple[str | None, dict]:
    """
    Try to match product.update_price intent.
    
    Patterns:
    - 修改 SKU A001 价格到 59.9
    - 把 A001 价格改成 59.9
    - 更新商品 A001 售价为 39.9
    - 改价 A001 到 59.9
    - 调整 A001 价格为 59.9
    
    Args:
        text: Normalized text
        
    Returns:
        Tuple of (intent_code, slots) or (None, {}) if not matched
    """
    # Check if text contains price update keywords first
    update_keywords = ['修改', '改价', '更新', '调整', '改成', '改为']
    has_update_keyword = any(keyword in text for keyword in update_keywords)
    
    if not has_update_keyword:
        return None, {}
    
    # Pattern for SKU: SKU followed by alphanumeric or just alphanumeric
    sku_pattern = r'(?:SKU|商品 | 产品)?\s*([A-Z][0-9]+)'
    sku_match = re.search(sku_pattern, text, re.IGNORECASE)
    
    if not sku_match:
        return None, {}
    
    sku = sku_match.group(1)
    
    # Pattern for price: support combinations like "价格到", "价格改为", "售价为", etc.
    # This pattern matches: [价格/价/售价] + [到/为/改成/改为] + number
    # Or just: [到/为/改成/改为] + number
    price_pattern = r'(?:价格 | 价 | 售价)?\s*(?:到 | 为 | 改成 | 改为|调整到)\s*(\d+(?:\.\d+)?)'
    price_match = re.search(price_pattern, text, re.IGNORECASE)
    
    if not price_match:
        return None, {}
    
    target_price = float(price_match.group(1))
    
    slots = {
        'sku': sku,
        'target_price': target_price
    }
    return 'product.update_price', slots
