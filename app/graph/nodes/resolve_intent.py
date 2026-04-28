"""
Resolve Intent Node

Identifies the intent from the normalized text using rule-based matching.
"""
import re
from typing import Optional, Tuple, Dict, Any
from app.core.config import settings
from app.core.logging import logger
from app.services.llm.intent_fallback import run_llm_intent_fallback
from app.utils.task_logger import log_step


_LLM_FALLBACK_INTENT_ALLOWLIST = frozenset(
    {
        "ecom_watch.monitor_targets",
        "ecom_watch.monitor_summary",
        "ecom_watch.anomaly_explanation",
        "ecom_watch.action_plan",
        "ecom_watch.summary_today",
        "ecom_watch.monitor_probe_query",
        "ecom_watch.monitor_diagnostics_query",
        "ecom_watch.retry_price_probe",
        "ecom_watch.retry_price_probes",
        "ecom_watch.replace_monitor_target_url",
        "ecom_watch.refresh_monitor_target_price",
        "ecom_watch.refresh_monitor_prices",
        "ecom_watch.monitor_price_history",
        "ecom_watch.price_refresh_run_detail",
        "ecom_watch.product_detail",
        "ecom_watch.discovery_search",
        "ecom_watch.add_monitor_by_url",
        "ecom_watch.add_from_candidates",
        "ecom_watch.manage_monitor_target",
        "document.ocr_recognize",
        "product.query_sku_status",
        "product.update_price",
    }
)


def _log_fallback_step(state: dict, step_code: str, step_status: str, detail: str) -> None:
    task_id = str(state.get("task_id") or "").strip()
    if not task_id:
        return
    log_step(task_id, step_code, step_status, detail[:500])


def _fallback_skip_unknown(state: dict, reason: str) -> dict:
    state["intent_code"] = "unknown"
    state["slots"] = {}
    _log_fallback_step(
        state,
        "llm_intent_fallback_skipped",
        "success",
        f"enabled={settings.ENABLE_LLM_INTENT_FALLBACK} provider={settings.LLM_INTENT_PROVIDER} reason={reason}",
    )
    return state


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

    # P10: query today summary from B service.
    if not intent_code:
        intent_code, slots = try_match_b_today_summary(normalized_text)

    # P10: query monitor targets from B service.
    if not intent_code:
        intent_code, slots = try_match_b_monitor_targets(normalized_text)

    # P14-B: boss readable monitor summary.
    if not intent_code:
        intent_code, slots = try_match_b_monitor_summary(normalized_text)

    # P14-C: anomaly explanation for boss-readable diagnostics.
    if not intent_code:
        intent_code, slots = try_match_b_anomaly_explanation(normalized_text)

    # P14-D: action plan generation for next-step operations.
    if not intent_code:
        intent_code, slots = try_match_b_action_plan(normalized_text)

    # P13-G: query monitor targets by probe status/source.
    if not intent_code:
        intent_code, slots = try_match_b_monitor_probe_query(normalized_text)

    # P13-I: query price diagnostics views.
    if not intent_code:
        intent_code, slots = try_match_b_monitor_diagnostics_query(normalized_text)

    # P13-J: replace monitor target URL.
    if not intent_code:
        intent_code, slots = try_match_b_replace_monitor_target_url(normalized_text)

    # P13-J: refresh single monitor target after URL replacement.
    if not intent_code:
        intent_code, slots = try_match_b_refresh_monitor_target_price(normalized_text)

    # P13-H: retry failed/mock probe objects.
    if not intent_code:
        intent_code, slots = try_match_b_retry_price_probe(normalized_text)

    # P13-A: refresh monitor target prices via B service.
    if not intent_code:
        intent_code, slots = try_match_b_refresh_monitor_prices(normalized_text)

    # P13-B: query monitor target price history.
    if not intent_code:
        intent_code, slots = try_match_b_price_history(normalized_text)

    # P13-D: query monitor refresh run detail by run_id.
    if not intent_code:
        intent_code, slots = try_match_b_price_refresh_run(normalized_text)

    # P11-D: manage monitor target (pause / resume / delete) by index.
    if not intent_code:
        intent_code, slots = try_match_b_manage_monitor_target(normalized_text)

    # P10: query product detail from B service.
    if not intent_code:
        intent_code, slots = try_match_b_product_detail(normalized_text)

    # P11-A: add monitor target directly by URL.
    if not intent_code:
        intent_code, slots = try_match_b_add_monitor_by_url(normalized_text)

    # P11-B: discovery search + candidate batch.
    if not intent_code:
        intent_code, slots = try_match_b_discovery_search(normalized_text)

    # P11-C: add monitor target from latest discovery candidates by index.
    if not intent_code:
        intent_code, slots = try_match_b_add_from_candidates(normalized_text)

    # Try to match warehouse.adjust_inventory (P6.1 Odoo high-risk write sample)
    if not intent_code:
        intent_code, slots = try_match_warehouse_adjust_inventory(normalized_text)

    # P15-A: OCR document recognize skeleton via mock input.
    if not intent_code:
        intent_code, slots = try_match_document_ocr_recognize(normalized_text, state)

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
        if not settings.ENABLE_LLM_INTENT_FALLBACK:
            state = _fallback_skip_unknown(state, reason="feature_disabled")
            logger.info("Unknown intent (fallback disabled): text='%s'", normalized_text[:100])
            return state

        _log_fallback_step(
            state,
            "llm_intent_fallback_started",
            "processing",
            f"enabled=true provider={settings.LLM_INTENT_PROVIDER} text={normalized_text[:80]}",
        )
        try:
            fallback = run_llm_intent_fallback(normalized_text)
            fallback_intent = str(fallback.intent or "unknown").strip()
            fallback_slots = fallback.slots if isinstance(fallback.slots, dict) else {}
            confidence = float(fallback.confidence)
            allowed = fallback_intent in _LLM_FALLBACK_INTENT_ALLOWLIST

            if not allowed:
                state["intent_code"] = "unknown"
                state["slots"] = {}
                state["clarification_question"] = (
                    fallback.clarification_question
                    or "我理解到一个不在白名单内的动作，请换一种说法。"
                )
                _log_fallback_step(
                    state,
                    "llm_intent_fallback_failed",
                    "failed",
                    f"intent={fallback_intent} confidence={confidence:.2f} allowed=false reason=intent_not_allowed",
                )
                logger.warning("LLM fallback blocked non-allowlist intent: %s", fallback_intent)
                return state

            if confidence < 0.5:
                state["intent_code"] = "unknown"
                state["slots"] = {}
                state["clarification_question"] = (
                    fallback.clarification_question
                    or "我还不太确定你的意图，请补充你想查询或操作的对象。"
                )
                _log_fallback_step(
                    state,
                    "llm_intent_fallback_low_confidence",
                    "success",
                    f"intent={fallback_intent} confidence={confidence:.2f} threshold=0.5 reason=too_low",
                )
                return state

            if confidence < float(settings.LLM_INTENT_CONFIDENCE_THRESHOLD):
                state["intent_code"] = "unknown"
                state["slots"] = {}
                state["clarification_question"] = (
                    fallback.clarification_question
                    or "我还需要确认你的目标，请再具体说明。"
                )
                _log_fallback_step(
                    state,
                    "llm_intent_fallback_low_confidence",
                    "success",
                    (
                        f"intent={fallback_intent} confidence={confidence:.2f} "
                        f"threshold={settings.LLM_INTENT_CONFIDENCE_THRESHOLD}"
                    ),
                )
                return state

            state["intent_code"] = fallback_intent
            state["slots"] = fallback_slots
            state["llm_intent_confidence"] = confidence
            state["llm_intent_reason"] = str(fallback.reason or "")
            _log_fallback_step(
                state,
                "llm_intent_fallback_succeeded",
                "success",
                f"intent={fallback_intent} confidence={confidence:.2f} allowed=true",
            )
            logger.info(
                "LLM fallback resolved intent: intent_code=%s confidence=%.2f",
                fallback_intent,
                confidence,
            )
        except Exception as exc:
            state["intent_code"] = "unknown"
            state["slots"] = {}
            _log_fallback_step(
                state,
                "llm_intent_fallback_failed",
                "failed",
                f"provider={settings.LLM_INTENT_PROVIDER} error={str(exc)[:120]}",
            )
            logger.warning("LLM intent fallback failed: %s", exc)
    
    return state


def try_match_b_today_summary(text: str) -> tuple[str | None, dict]:
    summary_keywords = ("今天有什么变化", "看看今天摘要", "今日监控摘要")
    if any(keyword in text for keyword in summary_keywords):
        return "ecom_watch.summary_today", {}
    return None, {}


def try_match_b_monitor_targets(text: str) -> tuple[str | None, dict]:
    monitor_keywords = ("看看当前监控对象", "查看当前监控对象", "当前监控哪些商品", "监控列表")
    if any(keyword in text for keyword in monitor_keywords):
        return "ecom_watch.monitor_targets", {}
    return None, {}


def try_match_b_monitor_summary(text: str) -> tuple[str | None, dict]:
    summary_keywords = (
        "总结一下当前价格监控情况",
        "帮我看一下现在监控整体怎么样",
        "当前有哪些商品需要重点处理",
        "给我汇总一下价格监控状态",
        "今天价格监控有什么问题",
    )
    if any(keyword in text for keyword in summary_keywords):
        return "ecom_watch.monitor_summary", {}
    return None, {}


def try_match_b_anomaly_explanation(text: str) -> tuple[str | None, dict]:
    explanation_keywords = (
        "为什么这些商品价格不准",
        "解释一下低可信对象的问题",
        "为什么这个商品需要人工处理",
        "为什么这些商品需要人工处理",
        "这些异常是怎么来的",
        "mock_price 是什么意思",
        "fallback_mock 为什么不能直接用",
    )
    if any(keyword in text for keyword in explanation_keywords):
        return "ecom_watch.anomaly_explanation", {}
    return None, {}


def try_match_b_action_plan(text: str) -> tuple[str | None, dict]:
    normalized = str(text or "").strip().lower()
    action_plan_keywords = (
        "这些异常商品下一步怎么处理",
        "给我一个处理计划",
        "低可信对象接下来怎么处理",
        "帮我安排一下处理顺序",
    )
    if any(keyword in normalized for keyword in action_plan_keywords):
        return "ecom_watch.action_plan", {}

    has_which = "哪些" in normalized
    has_retry = "重试" in normalized
    has_url = ("url" in normalized) or ("链接" in normalized)
    has_switch_url = ("换url" in normalized) or ("换 url" in normalized) or ("换链接" in normalized)
    has_first_retry = "先重试" in normalized
    has_first_url = ("先换url" in normalized) or ("先换 url" in normalized) or ("先换链接" in normalized)

    if (has_which and has_retry) or (has_which and (has_url or has_switch_url)):
        return "ecom_watch.action_plan", {}
    if has_first_retry or has_first_url:
        return "ecom_watch.action_plan", {}
    if has_retry and (has_url or has_switch_url):
        return "ecom_watch.action_plan", {}
    return None, {}


def try_match_b_monitor_probe_query(text: str) -> tuple[str | None, dict]:
    failed_keywords = ("查看价格采集失败", "查看采集失败对象")
    mock_keywords = ("查看mock价格对象",)
    real_keywords = ("查看真实价格对象",)
    if any(keyword in text for keyword in failed_keywords):
        return "ecom_watch.monitor_probe_query", {"query_type": "failed"}
    if any(keyword in text for keyword in mock_keywords):
        return "ecom_watch.monitor_probe_query", {"query_type": "mock"}
    if any(keyword in text for keyword in real_keywords):
        return "ecom_watch.monitor_probe_query", {"query_type": "real"}
    return None, {}


def try_match_b_monitor_diagnostics_query(text: str) -> tuple[str | None, dict]:
    mapping = {
        "查看价格异常对象": "price_anomaly",
        "查看低可信价格对象": "low_confidence",
        "查看价格监控状态": "monitor_status",
        "价格监控概览": "monitor_overview",
        "查看高优先级处理对象": "high_priority_actions",
        "查看人工接管对象": "manual_review_required",
        "查看提醒候选对象": "alert_candidates",
        "查看价格处理建议": "price_action_suggestions",
    }
    for keyword, query_type in mapping.items():
        if keyword in text:
            return "ecom_watch.monitor_diagnostics_query", {"query_type": query_type}
    return None, {}


def try_match_b_retry_price_probe(text: str) -> tuple[str | None, dict]:
    single_patterns = (
        r"^重试对象\s*(\d+)\s*价格采集$",
        r"^重试对象ID\s*(\d+)\s*价格采集$",
    )
    for pattern in single_patterns:
        match = re.search(pattern, text)
        if match:
            return "ecom_watch.retry_price_probe", {"target_id": int(match.group(1))}

    batch_keywords = ("重试价格采集", "重试采集失败对象", "重试mock价格对象")
    if any(keyword in text for keyword in batch_keywords):
        return "ecom_watch.retry_price_probes", {}
    return None, {}


def try_match_b_replace_monitor_target_url(text: str) -> tuple[str | None, dict]:
    patterns = (
        r"^替换监控对象URL\s*(\d+)\s+(https?://\S+)$",
        r"^替换对象URL\s*(\d+)\s+(https?://\S+)$",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            continue
        return "ecom_watch.replace_monitor_target_url", {
            "target_id": int(match.group(1)),
            "product_url": match.group(2),
        }
    return None, {}


def try_match_b_refresh_monitor_target_price(text: str) -> tuple[str | None, dict]:
    patterns = (
        r"^重新采集对象\s*(\d+)$",
        r"^重新采集监控对象\s*(\d+)$",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        return "ecom_watch.refresh_monitor_target_price", {"target_id": int(match.group(1))}
    return None, {}


def try_match_b_refresh_monitor_prices(text: str) -> tuple[str | None, dict]:
    refresh_keywords = ("刷新监控价格", "刷新监控对象价格", "刷新价格")
    if any(keyword in text for keyword in refresh_keywords):
        return "ecom_watch.refresh_monitor_prices", {}
    return None, {}


def try_match_b_price_history(text: str) -> tuple[str | None, dict]:
    explicit_id_patterns = (
        r"^查看对象ID\s*(\d+)\s*的?价格历史$",
        r"^查看监控对象ID\s*(\d+)\s*的?价格历史$",
        r"^查看ID\s*(\d+)\s*价格历史$",
    )
    for pattern in explicit_id_patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        return "ecom_watch.monitor_price_history", {"target_id": int(match.group(1)), "query_mode": "target_id"}

    index_patterns = (
        r"^查看第\s*(\d+)\s*个价格历史$",
        r"^查看第\s*(\d+)\s*个监控对象价格历史$",
    )
    for pattern in index_patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        return "ecom_watch.monitor_price_history", {"list_index": int(match.group(1)), "query_mode": "list_index"}

    implied_id_patterns = (
        r"^查看价格历史\s*(\d+)$",
        r"^查看历史价格\s*(\d+)$",
        r"^查看监控对象\s*(\d+)\s*价格历史$",
    )
    for pattern in implied_id_patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        raw_id = int(match.group(1))
        return "ecom_watch.monitor_price_history", {"target_id": raw_id, "query_mode": "target_id", "ambiguous_input": True}
    return None, {}


def try_match_b_price_refresh_run(text: str) -> tuple[str | None, dict]:
    pattern = (
        r"^(查看刷新结果|查看价格刷新批次|查看刷新批次)\s*"
        r"(PRR-\d{8}-[A-Z0-9]{4,})$"
    )
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None, {}
    return "ecom_watch.price_refresh_run_detail", {"run_id": match.group(2).upper()}


def try_match_b_manage_monitor_target(text: str) -> tuple[str | None, dict]:
    def _parse_zh_ordinal_index(raw: str) -> int | None:
        """
        Parse Chinese ordinal like '第2个' / '第二个' / '第二' into index int.
        Scope: 1-10 (minimal boss-friendly range).
        """
        s = (raw or "").strip()
        if not s:
            return None
        s = re.sub(r"^第\s*", "", s)
        s = re.sub(r"\s*个$", "", s)
        if s.isdigit():
            n = int(s)
            return n if n > 0 else None
        mapping = {
            "一": 1,
            "二": 2,
            "三": 3,
            "四": 4,
            "五": 5,
            "六": 6,
            "七": 7,
            "八": 8,
            "九": 9,
            "十": 10,
            "1": 1,
            "2": 2,
            "3": 3,
            "4": 4,
            "5": 5,
            "6": 6,
            "7": 7,
            "8": 8,
            "9": 9,
            "10": 10,
        }
        n = mapping.get(s)
        return n if isinstance(n, int) and 1 <= n <= 10 else None

    patterns = (
        (r"^(暂停监控|暂停)\s*第\s*(\d+)\s*个$", "pause"),
        (r"^(恢复监控|恢复)\s*第\s*(\d+)\s*个$", "resume"),
        (r"^(删除监控|删除)\s*第\s*(\d+)\s*个$", "delete"),
        # More colloquial ordinal: 第二个 / 第三个 (no spaces, no digits).
        (r"^(暂停监控|暂停)\s*(第?[一二三四五六七八九十]个)$", "pause"),
        (r"^(恢复监控|恢复)\s*(第?[一二三四五六七八九十]个)$", "resume"),
        (r"^(删除监控|删除)\s*(第?[一二三四五六七八九十]个)$", "delete"),
    )
    for pattern, action in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        idx = _parse_zh_ordinal_index(match.group(2))
        if idx is None:
            return None, {}
        return "ecom_watch.manage_monitor_target", {"action": action, "index": idx}
    return None, {}


def try_match_b_product_detail(text: str) -> tuple[str | None, dict]:
    if "商品" not in text and "product" not in text.lower():
        return None, {}
    if not any(k in text for k in ("详情", "查看", "看看", "怎么样")):
        return None, {}
    product_match = re.search(r"(?:商品|product)\s*(\d+)", text, re.IGNORECASE)
    if not product_match:
        return None, {}
    return "ecom_watch.product_detail", {"product_id": int(product_match.group(1))}


def try_match_b_add_monitor_by_url(text: str) -> tuple[str | None, dict]:
    command_prefixes = ("监控这个商品：", "把这个链接加入监控：", "加入监控：")
    for prefix in command_prefixes:
        if prefix not in text:
            continue
        # P11-A: capture the raw single URL slot candidate and let B validate.
        candidate = text.split(prefix, 1)[1].strip()
        if not candidate:
            return None, {}
        return "ecom_watch.add_monitor_by_url", {"url": candidate}
    return None, {}


def try_match_b_discovery_search(text: str) -> tuple[str | None, dict]:
    command_prefixes = ("搜索商品：", "搜索：", "帮我找一下 ")
    for prefix in command_prefixes:
        if prefix not in text:
            continue
        query = text.split(prefix, 1)[1].strip()
        # P11-B: empty query should still route into discovery_search so that
        # the execution layer can return a user-readable validation failure.
        return "ecom_watch.discovery_search", {"query": query}
    if text.startswith("帮我找一下"):
        query = text[len("帮我找一下"):].strip()
        return "ecom_watch.discovery_search", {"query": query}
    return None, {}


def try_match_b_add_from_candidates(text: str) -> tuple[str | None, dict]:
    patterns = (
        r"^加入监控第\s*(\d+)\s*个$",
        r"^监控第\s*(\d+)\s*个$",
        r"^选第\s*(\d+)\s*个加入监控$",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        return "ecom_watch.add_from_candidates", {"index": int(match.group(1))}
    return None, {}


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


def try_match_document_ocr_recognize(text: str, state: dict | None = None) -> tuple[str | None, dict]:
    normalized = str(text or "").strip().lower()
    explicit_keywords = (
        "识别这张发票",
        "帮我读一下这个文件",
        "提取这张图片里的文字",
        "ocr 识别一下",
        "ocr识别一下",
        "帮我识别票据文字",
    )
    has_explicit_keyword = any(keyword in normalized for keyword in explicit_keywords)
    has_ocr = "ocr" in normalized
    has_recognize = any(keyword in normalized for keyword in ("识别", "提取", "读一下", "读出"))
    has_document = any(keyword in normalized for keyword in ("发票", "票据", "文件", "图片", "文字"))
    if not (has_explicit_keyword or (has_recognize and has_document) or (has_ocr and (has_recognize or has_document))):
        return None, {}

    hint_document_type = "invoice"
    if "收据" in normalized or "小票" in normalized:
        hint_document_type = "receipt"
    elif "发票" not in normalized and "票据" not in normalized:
        hint_document_type = "unknown"

    user_open_id = ""
    if isinstance(state, dict):
        user_open_id = str(state.get("user_open_id") or "").strip()
    requested_by = user_open_id or "feishu_user"

    file_name = "ocr_document.png"
    if hint_document_type == "invoice":
        file_name = "invoice_sample.png"
    elif hint_document_type == "receipt":
        file_name = "receipt_sample.png"

    slots = {
        "document_id": f"mock-doc-{hint_document_type or 'unknown'}",
        "file_name": file_name,
        "mime_type": "image/png",
        "file_path": f"mock://{file_name}",
        "source": "mock",
        "requested_by": requested_by,
        "hint_document_type": hint_document_type,
    }
    return "document.ocr_recognize", slots


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


def try_match_warehouse_adjust_inventory(text: str) -> tuple[str | None, dict]:
    """Match warehouse.adjust_inventory in P9-E minimal command scope.

    Supported examples:
    - 把 A001 的库存改到 105
    - 调整 A001 库存到 105
    - 调整 Odoo SKU A001 库存 +5
    - Odoo 把 A001 库存增加 5
    """
    if "库存" not in text:
        return None, {}
    if not any(k in text for k in ("调整", "增加", "减少", "加", "减", "改到", "改成", "到")):
        return None, {}

    sku_match = re.search(r"(?:SKU|商品|产品)?\s*([A-Z][0-9]+)", text, re.IGNORECASE)
    if not sku_match:
        return None, {}

    # Parse delta first: explicit signed number (+5/-3), then 增加/减少 N.
    delta = None
    signed = re.search(r"([+-]\s*\d+)", text)
    if signed:
        try:
            delta = int(signed.group(1).replace(" ", ""))
        except Exception:
            delta = None
    if delta is None:
        inc = re.search(r"(增加|加)\s*(\d+)", text)
        dec = re.search(r"(减少|减)\s*(\d+)", text)
        if inc:
            delta = int(inc.group(2))
        elif dec:
            delta = -int(dec.group(2))

    slots: dict[str, int | str] = {"sku": sku_match.group(1), "platform": "odoo"}
    if delta is not None and delta != 0:
        slots["delta"] = delta
        return "warehouse.adjust_inventory", slots

    # Parse target_inventory for boss-demo text command:
    # - 把 A001 的库存改到 105
    # - 调整 A001 库存到 105
    target_match = re.search(r"库存(?:改到|改成|到|为)?\s*(\d+)", text)
    if target_match:
        target_inventory = int(target_match.group(1))
        if target_inventory >= 0:
            slots["target_inventory"] = target_inventory
            return "warehouse.adjust_inventory", slots

    return None, {}

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
    # Pattern for task confirmation.
    # Historically: TASK-YYYYMMDD-XXXXXX. For acceptance scripts we also allow prefixed ids
    # like TASK-P61-... while still anchoring to "TASK-" prefix.
    confirmation_pattern = r"(?:确认执行|确认|执行)\s*(TASK-[A-Z0-9][A-Z0-9-]{6,})"
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
