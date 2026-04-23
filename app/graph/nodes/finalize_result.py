"""Finalize task result and persist status."""
from app.core.config import settings
from app.core.logging import logger
from app.core.time import get_shanghai_now
from app.db.models import TaskRecord
from app.db.session import SessionLocal
from app.rag.models import RetrievalHit, RetrievalResult
from app.rag.retrieval_service import (
    USE_CASE_FAILURE_EXPLANATION,
    format_rag_footer,
    retrieve,
)
from app.utils.task_logger import log_step

_FAILURE_INTENT_HINT_ALLOW = frozenset({"", "unknown"})


def _build_failure_explanation_query(state: dict) -> str:
    """Rich query aligned with seeded failure docs (hash embedding + Milvus filter)."""
    err = (state.get("error_message") or "").strip()
    norm = (state.get("normalized_text") or state.get("raw_text") or "").strip()
    intent = (state.get("intent_code") or "unknown").strip()
    parts = [
        "failure_explanation",
        "任务执行失败",
        "命令无法处理",
        "unknown intent",
        "未识别命令",
        "失败原因",
        "排查建议",
        "FAQ",
        "error_resolution",
        "确认目标不存在",
        f"intent={intent}",
    ]
    if err:
        parts.append(f"错误信息: {err}")
    if norm:
        parts.append(f"用户原话: {norm}")
    parts.append(
        "当任务执行失败、确认目标不存在或命令无法处理时，"
        "应补充失败原因、排查建议和 FAQ 参考。"
    )
    return " ".join(p for p in parts if p).strip()[:2000]


def _filter_failure_hits(hits: list[RetrievalHit]) -> list[RetrievalHit]:
    out: list[RetrievalHit] = []
    for h in hits:
        ih = (h.intent_hint or "").strip()
        if ih in _FAILURE_INTENT_HINT_ALLOW:
            out.append(h)
    return out


def _retrieve_failure_explanation(*, query: str) -> RetrievalResult:
    res = retrieve(
        use_case=USE_CASE_FAILURE_EXPLANATION,
        query=query,
        categories=["faq", "error_resolution", "case"],
        intent_hints=["unknown"],
    )
    if res.fallback or res.error or res.hits:
        return res
    res_broad = retrieve(
        use_case=USE_CASE_FAILURE_EXPLANATION,
        query=query,
        categories=["faq", "error_resolution", "case"],
        intent_hints=None,
    )
    if res_broad.fallback or res_broad.error:
        return res
    kept = _filter_failure_hits(res_broad.hits)
    if not kept:
        return res
    return RetrievalResult(
        use_case=res_broad.use_case,
        query=res_broad.query,
        hits=kept,
        fallback=False,
        error=None,
    )


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

    status = state.get("status", "processing")
    intent_code = str(state.get("intent_code") or "").strip()
    append_rag_footer = not intent_code.startswith("ecom_watch.")

    # RAG use case 3: failure explanation (does not change status / error fields)
    state.setdefault("rag_failure_footer", "")
    state.setdefault("rag_failure_fallback", True)
    if (
        status == "failed"
        and append_rag_footer
        and settings.ENABLE_RAG
        and settings.RAG_USE_CASE_ENABLED_FAILURE_EXPLANATION
    ):
        q = _build_failure_explanation_query(state)
        if q:
            top_k = int(settings.RAG_TOP_K)
            log_step(
                task_id,
                "rag_retrieval_started",
                "processing",
                f"use_case=failure_explanation top_k={top_k}",
            )
            res = _retrieve_failure_explanation(query=q)
            if res.fallback or res.error:
                log_step(
                    task_id,
                    "rag_retrieval_failed",
                    "failed",
                    f"use_case=failure_explanation top_k={top_k} hits=0 err={res.error or 'fallback'} fallback=true",
                )
            elif not res.hits:
                log_step(
                    task_id,
                    "rag_retrieval_succeeded",
                    "success",
                    f"use_case=failure_explanation top_k={top_k} hits=0 fallback=true",
                )
            else:
                state["rag_failure_footer"] = format_rag_footer(
                    res.hits, title="失败解释参考"
                )
                state["rag_failure_fallback"] = False
                log_step(
                    task_id,
                    "rag_retrieval_succeeded",
                    "success",
                    f"use_case=failure_explanation top_k={top_k} hits={len(res.hits)} fallback=false",
                )

    summary = state.get("result_summary", "")
    if append_rag_footer:
        rag_keys = ["rag_command_footer", "rag_rule_footer", "rag_failure_footer"]
        if status == "failed":
            # Do not append command_interpretation on failed tasks (failure_explanation / rule only).
            rag_keys = ["rag_rule_footer", "rag_failure_footer"]
        for key in rag_keys:
            extra = state.get(key) or ""
            if extra:
                summary += extra
    state["result_summary"] = summary

    db = SessionLocal()
    try:
        task_record = db.query(TaskRecord).filter(TaskRecord.task_id == task_id).first()
        if not task_record:
            logger.error("Task record not found: task_id=%s", task_id)
            return state
        
        # Update task record with result
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
