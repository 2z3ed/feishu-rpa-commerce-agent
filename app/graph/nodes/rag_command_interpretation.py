"""RAG use case 1: command interpretation hint (does not replace rule-based intent)."""
from __future__ import annotations

from app.core.config import settings
from app.core.logging import logger
from app.rag.retrieval_service import (
    USE_CASE_COMMAND_INTERPRETATION,
    format_rag_footer,
    retrieve,
)
from app.utils.task_logger import log_step

_SCOPED_INTENTS = frozenset({"product.query_sku_status", "product.update_price"})


def _command_interpretation_intent_hints(intent: str) -> list[str] | None:
    """Narrow Milvus candidates by intent_hint so update_price does not hit query_sku docs."""
    if intent == "product.query_sku_status":
        return ["product.query_sku_status"]
    if intent == "product.update_price":
        return ["product.update_price"]
    return None


def _build_command_interpretation_query(*, intent: str, state: dict, norm: str) -> str:
    """For update_price, bias the query toward 改价 semantics (hash embedding + clearer docs)."""
    norm = (norm or "").strip()
    if intent != "product.update_price":
        return norm[:2000]

    slots = state.get("slots") or {}
    sku = slots.get("sku")
    target_price = slots.get("target_price")
    sku_s = str(sku).strip() if sku is not None else ""
    tp_s = ""
    if target_price is not None:
        tp_s = (
            f"{target_price:.12g}"
            if isinstance(target_price, float)
            else str(target_price).strip()
        )

    parts = [
        "product.update_price",
        "改价命令",
        "修改商品价格",
        "价格调整说明",
    ]
    if sku_s:
        parts.append(f"SKU {sku_s}")
    if tp_s:
        parts.append(f"目标价格 {tp_s}")
    parts.append(f"用户原话: {norm}")
    return " ".join(p for p in parts if p).strip()[:2000]


def rag_command_interpretation(state: dict) -> dict:
    task_id = state.get("task_id", "")
    intent = state.get("intent_code", "unknown")
    norm = (state.get("normalized_text") or state.get("raw_text") or "").strip()

    state["rag_command_footer"] = ""
    state["rag_command_hits"] = 0
    state["rag_command_fallback"] = True

    if not settings.ENABLE_RAG:
        log_step(
            task_id,
            "rag_retrieval_skipped",
            "success",
            "use_case=command_interpretation reason=rag_disabled",
        )
        return state

    if not settings.RAG_USE_CASE_ENABLED_COMMAND_INTERPRETATION:
        log_step(
            task_id,
            "rag_retrieval_skipped",
            "success",
            "use_case=command_interpretation reason=flag_off",
        )
        return state

    if intent == "unknown":
        log_step(
            task_id,
            "rag_retrieval_skipped",
            "success",
            "use_case=command_interpretation reason=unknown_intent_use_failure_rag_in_finalize",
        )
        return state

    if intent not in _SCOPED_INTENTS:
        log_step(
            task_id,
            "rag_retrieval_skipped",
            "success",
            f"use_case=command_interpretation reason=intent_out_of_scope intent={intent}",
        )
        return state

    if not norm:
        log_step(
            task_id,
            "rag_retrieval_skipped",
            "success",
            "use_case=command_interpretation reason=empty_query",
        )
        return state

    query = _build_command_interpretation_query(intent=intent, state=state, norm=norm)
    if not query.strip():
        log_step(
            task_id,
            "rag_retrieval_skipped",
            "success",
            "use_case=command_interpretation reason=empty_query_after_build",
        )
        return state

    top_k = int(settings.RAG_TOP_K)
    log_step(
        task_id,
        "rag_retrieval_started",
        "processing",
        f"use_case=command_interpretation top_k={top_k}",
    )

    res = retrieve(
        use_case=USE_CASE_COMMAND_INTERPRETATION,
        query=query,
        categories=["rule", "sop", "faq"],
        intent_hints=_command_interpretation_intent_hints(intent),
    )

    if res.fallback or res.error:
        log_step(
            task_id,
            "rag_retrieval_failed",
            "failed",
            f"use_case=command_interpretation top_k={top_k} hits=0 err={res.error or 'fallback'} fallback=true",
        )
        logger.debug("RAG command interpretation fallback: %s", res.error)
        return state

    hits_n = len(res.hits)
    if hits_n == 0:
        log_step(
            task_id,
            "rag_retrieval_succeeded",
            "success",
            f"use_case=command_interpretation top_k={top_k} hits=0 fallback=true",
        )
        return state

    state["rag_command_footer"] = format_rag_footer(res.hits, title="命令说明参考")
    state["rag_command_hits"] = hits_n
    state["rag_command_fallback"] = False
    log_step(
        task_id,
        "rag_retrieval_succeeded",
        "success",
        f"use_case=command_interpretation top_k={top_k} hits={hits_n} fallback=false",
    )
    return state
