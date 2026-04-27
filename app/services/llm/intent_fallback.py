from __future__ import annotations

from app.core.config import settings
from app.schemas.llm_intent import LLMIntentFallbackOutput


def _normalize_text(text: str) -> str:
    return (text or "").strip().lower()


def _mock_infer_intent(normalized_text: str) -> LLMIntentFallbackOutput:
    text = _normalize_text(normalized_text)

    if "不太对" in text or "有异常" in text:
        return LLMIntentFallbackOutput(
            intent="ecom_watch.monitor_diagnostics_query",
            slots={"query_type": "price_anomaly"},
            confidence=0.82,
            clarification_question="",
            reason="用户在问异常对象，语义贴近价格异常视图。",
        )

    if "失败" in text and ("再跑" in text or "重试" in text or "重新跑" in text):
        return LLMIntentFallbackOutput(
            intent="ecom_watch.retry_price_probes",
            slots={},
            confidence=0.86,
            clarification_question="",
            reason="用户表达重试失败对象，匹配批量重试语义。",
        )

    if "不可信" in text or ("低" in text and "可信" in text):
        return LLMIntentFallbackOutput(
            intent="ecom_watch.monitor_diagnostics_query",
            slots={"query_type": "low_confidence"},
            confidence=0.8,
            clarification_question="",
            reason="用户在查询低可信价格对象。",
        )

    if "人工" in text and ("处理" in text or "接管" in text):
        return LLMIntentFallbackOutput(
            intent="ecom_watch.monitor_diagnostics_query",
            slots={"query_type": "manual_review_required"},
            confidence=0.78,
            clarification_question="",
            reason="用户表达人工处理诉求，匹配人工接管视图。",
        )

    if "重试" in text and ("url" in text or "链接" in text):
        return LLMIntentFallbackOutput(
            intent="ecom_watch.action_plan",
            slots={},
            confidence=0.84,
            clarification_question="",
            reason="用户在询问重试和 URL 治理顺序，匹配操作计划生成语义。",
        )

    if "处理一下那个有问题的" in text:
        return LLMIntentFallbackOutput(
            intent="ecom_watch.monitor_diagnostics_query",
            slots={},
            confidence=0.62,
            clarification_question="我还需要确认你要处理哪一类问题：价格异常、采集失败，还是 URL 不准确？",
            reason="语义过于笼统，缺少可执行对象和范围。",
        )

    if ("sku" in text and "a001" in text and "改" in text and "99" in text) or (
        "a001" in text and "价格" in text and "99" in text
    ):
        return LLMIntentFallbackOutput(
            intent="product.update_price",
            slots={"sku": "A001", "target_price": 99.0},
            confidence=0.9,
            clarification_question="",
            reason="用户明确表达 A001 改价到 99。",
        )

    return LLMIntentFallbackOutput(
        intent="unknown",
        slots={},
        confidence=0.42,
        clarification_question="我还不太确定你的目标，请描述你想查询的是监控列表、异常对象还是重试失败对象。",
        reason="mock provider 未匹配到足够明确的意图。",
    )


def run_llm_intent_fallback(normalized_text: str) -> LLMIntentFallbackOutput:
    provider = (settings.LLM_INTENT_PROVIDER or "mock").strip().lower()
    if provider == "mock":
        return _mock_infer_intent(normalized_text)
    raise ValueError(f"Unsupported LLM_INTENT_PROVIDER: {provider}")
