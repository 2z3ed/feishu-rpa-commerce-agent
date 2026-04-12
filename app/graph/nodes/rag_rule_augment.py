"""RAG use case 2: pre-execution rule / SOP hints for high-risk chain (mock semantics unchanged)."""
from __future__ import annotations

from app.core.config import settings
from app.core.logging import logger
from app.rag.models import RetrievalHit, RetrievalResult
from app.rag.retrieval_service import USE_CASE_RULE_AUGMENT, format_rag_footer, retrieve
from app.utils.task_logger import log_step

_SCOPED_INTENTS = frozenset({"product.update_price", "system.confirm_task"})

# Broad rule_augment fallback for update_price: keep rows safe for 改价, never confirm/query.
_UPDATE_PRICE_RULE_INTENT_HINT_ALLOW = frozenset({"", "product.update_price"})


def _filter_update_price_rule_hits(hits: list[RetrievalHit]) -> list[RetrievalHit]:
    out = []
    for h in hits:
        ih = (getattr(h, "intent_hint", None) or "").strip()
        if ih in _UPDATE_PRICE_RULE_INTENT_HINT_ALLOW:
            out.append(h)
    return out


def _build_rule_augment_query(*, intent: str, state: dict, norm: str) -> str:
    """
    Build retrieval query text. Hash pseudo-embeddings are sensitive to full string
    overlap with ingested rule documents, so product.update_price uses a rich,
    template-aligned query (intent + sku + target_price + user text).
    system.confirm_task keeps user text only (already validated path).
    """
    norm = (norm or "").strip()
    if intent != "product.update_price":
        return norm[:2000]

    slots = state.get("slots") or {}
    sku = slots.get("sku")
    target_price = slots.get("target_price")
    sku_s = str(sku).strip() if sku is not None else ""
    tp_s = ""
    if target_price is not None:
        if isinstance(target_price, float):
            tp_s = f"{target_price:.12g}"
        else:
            tp_s = str(target_price).strip()

    chunks = [
        "product.update_price",
        "改价",
        "修改商品价格",
        "修改价格",
        "高风险价格变更",
        "须二次确认",
        "确认前追加价格规则与风险提示",
    ]
    if sku_s:
        chunks.append(f"SKU {sku_s}")
    if tp_s:
        chunks.append(f"目标价格 {tp_s}")
        chunks.append(f"价格到 {tp_s}")
        chunks.append(f"修改为 {tp_s}")
    if sku_s and tp_s:
        # Aligns with common seeded rule sentences (e.g. milvus_seed_rule_update_price.py)
        chunks.append(
            f"当用户发起修改 SKU {sku_s} 价格到 {tp_s} 这类改价请求时，"
            f"应在确认前追加价格规则与风险提示，但不改变当前 mock 执行结果。"
        )
    if norm:
        chunks.append(f"用户原话: {norm}")
    q = " ".join(c for c in chunks if c).strip()
    return q[:2000]


def rag_rule_augment(state: dict) -> dict:
    task_id = state.get("task_id", "")
    intent = state.get("intent_code", "unknown")
    norm = (state.get("normalized_text") or state.get("raw_text") or "").strip()

    state["rag_rule_footer"] = ""
    state["rag_rule_hits"] = 0
    state["rag_rule_fallback"] = True

    if not settings.ENABLE_RAG:
        log_step(
            task_id,
            "rag_retrieval_skipped",
            "success",
            "use_case=rule_augment reason=rag_disabled",
        )
        return state

    if not settings.RAG_USE_CASE_ENABLED_RULE_AUGMENT:
        log_step(
            task_id,
            "rag_retrieval_skipped",
            "success",
            "use_case=rule_augment reason=flag_off",
        )
        return state

    if intent not in _SCOPED_INTENTS:
        log_step(
            task_id,
            "rag_retrieval_skipped",
            "success",
            f"use_case=rule_augment reason=intent_out_of_scope intent={intent}",
        )
        return state

    if not norm and intent != "product.update_price":
        log_step(
            task_id,
            "rag_retrieval_skipped",
            "success",
            "use_case=rule_augment reason=empty_query",
        )
        return state

    query = _build_rule_augment_query(intent=intent, state=state, norm=norm)
    if not query.strip():
        log_step(
            task_id,
            "rag_retrieval_skipped",
            "success",
            "use_case=rule_augment reason=empty_query_after_build",
        )
        return state

    top_k = int(settings.RAG_TOP_K)
    log_step(
        task_id,
        "rag_retrieval_started",
        "processing",
        f"use_case=rule_augment top_k={top_k}",
    )

    intent_hints = ["product.update_price"] if intent == "product.update_price" else None
    res = retrieve(
        use_case=USE_CASE_RULE_AUGMENT,
        query=query,
        categories=["rule", "sop"],
        intent_hints=intent_hints,
    )

    # Milvus rows may omit intent_hint (NULL/empty); strict filter yields 0 hits though rule text exists.
    if (
        intent == "product.update_price"
        and not res.fallback
        and not res.error
        and len(res.hits) == 0
    ):
        res_broad = retrieve(
            use_case=USE_CASE_RULE_AUGMENT,
            query=query,
            categories=["rule", "sop"],
            intent_hints=None,
        )
        if not res_broad.fallback and not res_broad.error:
            kept = _filter_update_price_rule_hits(res_broad.hits)
            if kept:
                res = RetrievalResult(
                    use_case=res_broad.use_case,
                    query=res_broad.query,
                    hits=kept,
                    fallback=False,
                    error=None,
                )

    if res.fallback or res.error:
        log_step(
            task_id,
            "rag_retrieval_failed",
            "failed",
            f"use_case=rule_augment top_k={top_k} hits=0 err={res.error or 'fallback'} fallback=true",
        )
        logger.debug("RAG rule augment fallback: %s", res.error)
        return state

    hits_n = len(res.hits)
    if hits_n == 0:
        log_step(
            task_id,
            "rag_retrieval_succeeded",
            "success",
            f"use_case=rule_augment top_k={top_k} hits=0 fallback=true",
        )
        return state

    state["rag_rule_footer"] = format_rag_footer(res.hits, title="规则与确认说明")
    state["rag_rule_hits"] = hits_n
    state["rag_rule_fallback"] = False
    log_step(
        task_id,
        "rag_retrieval_succeeded",
        "success",
        f"use_case=rule_augment top_k={top_k} hits={hits_n} fallback=false",
    )
    return state
