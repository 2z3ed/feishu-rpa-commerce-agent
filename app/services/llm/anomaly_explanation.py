from __future__ import annotations

from app.core.config import settings
from app.schemas.llm_anomaly_explanation import AnomalyExplanationInput, AnomalyExplanationOutput


def _rule_reason(item: dict) -> str:
    reason = str(item.get("price_anomaly_reason") or "").strip()
    if reason:
        return reason

    source = str(item.get("price_source") or "").strip().lower()
    if source in {"mock_price", "fallback_mock"}:
        return "当前价格来自系统兜底值，不是稳定页面采集结果。"

    page_type = str(item.get("price_page_type") or "").strip().lower()
    if page_type in {"search_page", "listing_page"}:
        return "当前页面更像搜索或列表页，不是稳定商品详情页。"

    probe_status = str(item.get("price_probe_status") or "").strip().lower()
    if probe_status in {"failed", "fallback_mock"}:
        probe_error = str(item.get("price_probe_error") or "").strip()
        if probe_error:
            return f"价格采集失败（{probe_error}）。"
        return "价格采集失败，系统回退到兜底结果。"

    if bool(item.get("manual_review_required")):
        return "该对象已被标记为需要人工接管。"

    confidence = str(item.get("price_confidence") or "").strip().lower()
    if confidence in {"low", "unknown"}:
        return "价格可信度不足，暂不建议直接用于决策。"

    return "该对象存在监控风险，建议人工复核。"


def _rule_impact(item: dict) -> str:
    source = str(item.get("price_source") or "").strip().lower()
    page_type = str(item.get("price_page_type") or "").strip().lower()
    confidence = str(item.get("price_confidence") or "").strip().lower()
    probe_status = str(item.get("price_probe_status") or "").strip().lower()

    if source in {"mock_price", "fallback_mock"}:
        return "该价格可用于占位展示，但不能直接作为真实价格决策依据。"
    if page_type in {"search_page", "listing_page"}:
        return "页面价格可能不是目标商品价格，直接判断会带来误判风险。"
    if probe_status in {"failed", "fallback_mock"}:
        return "当前无法确认稳定价格，继续使用会放大决策不确定性。"
    if confidence in {"low", "unknown"}:
        return "可信度偏低，价格判断需要人工复核后再使用。"
    return "该对象建议先复核来源，再用于后续判断。"


def _rule_suggestion(item: dict) -> str:
    suggestion = str(item.get("action_suggestion") or "").strip()
    if suggestion:
        return suggestion

    probe_status = str(item.get("price_probe_status") or "").strip().lower()
    if probe_status in {"failed", "fallback_mock"}:
        return "建议先重试采集；若仍失败，再检查链接有效性和页面结构。"

    page_type = str(item.get("price_page_type") or "").strip().lower()
    if page_type in {"search_page", "listing_page"}:
        return "建议替换为商品详情页 URL 后重新采集。"

    if bool(item.get("manual_review_required")):
        return "建议由人工接管并确认该对象后再决定下一步动作。"

    return "建议人工复核后再进行任何价格相关决策。"


def _pick_typical_targets(targets: list[dict]) -> list[dict]:
    scored: list[tuple[int, dict]] = []
    for item in targets:
        if not isinstance(item, dict):
            continue
        score = 0
        if str(item.get("price_anomaly_status") or "").strip().lower() in {"suspected", "anomaly", "abnormal"}:
            score += 3
        if str(item.get("price_confidence") or "").strip().lower() in {"low", "unknown"}:
            score += 2
        if str(item.get("price_probe_status") or "").strip().lower() in {"failed", "fallback_mock"}:
            score += 2
        if bool(item.get("manual_review_required")):
            score += 2
        if str(item.get("price_source") or "").strip().lower() in {"mock_price", "fallback_mock"}:
            score += 1
        if str(item.get("price_page_type") or "").strip().lower() in {"search_page", "listing_page"}:
            score += 1
        if score > 0:
            scored.append((score, item))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored[:3]]


def _build_rule_explanation(explanation_input: AnomalyExplanationInput) -> str:
    stats = explanation_input.stats
    if stats.target_count <= 0:
        return "当前没有可解释的监控对象。建议先获取监控列表后，再让我解释异常原因。"

    if (
        stats.anomaly_count <= 0
        and stats.low_confidence_count <= 0
        and stats.failed_probe_count <= 0
        and stats.manual_review_count <= 0
    ):
        return (
            "当前监控对象没有明显异常或低可信信号。\n\n"
            "如果你希望我针对某个对象解释，请补充对象名称或对象ID。"
        )

    typical = _pick_typical_targets(explanation_input.targets)
    lines = [
        "当前问题是什么：",
        (
            f"当前共 {stats.target_count} 个监控对象，其中异常 {stats.anomaly_count} 个、"
            f"低可信 {stats.low_confidence_count} 个、采集失败 {stats.failed_probe_count} 个、"
            f"人工接管 {stats.manual_review_count} 个。"
        ),
        "",
        "为什么会出现这个问题：",
    ]

    if typical:
        for idx, item in enumerate(typical, start=1):
            name = str(item.get("name") or item.get("product_name") or f"对象#{idx}").strip()
            lines.append(f"{idx}) {name}：{_rule_reason(item)}")
    else:
        lines.append("主要由页面类型不稳定、采集失败或价格可信度不足造成。")

    lines.extend(["", "对价格判断的影响："])
    if typical:
        for idx, item in enumerate(typical, start=1):
            lines.append(f"{idx}) {_rule_impact(item)}")
    else:
        lines.append("这些信号会降低价格判断可靠性，建议先复核再决策。")

    lines.extend(["", "建议怎么处理："])
    if typical:
        for idx, item in enumerate(typical, start=1):
            lines.append(f"{idx}) {_rule_suggestion(item)}")
    else:
        lines.append("建议先复核异常对象，并按采集状态逐项处理。")

    lines.extend(["", "不会自动处理提醒：", "系统不会自动刷新、自动重试、自动替换 URL、自动删除对象或自动改价。"])
    return "\n".join(lines)


def run_llm_anomaly_explanation(explanation_input: AnomalyExplanationInput) -> AnomalyExplanationOutput:
    provider = (settings.LLM_ANOMALY_EXPLANATION_PROVIDER or "mock").strip().lower()

    if not settings.ENABLE_LLM_ANOMALY_EXPLANATION:
        return AnomalyExplanationOutput(
            explanation_text=_build_rule_explanation(explanation_input),
            provider=provider or "mock",
            explanation_focus=explanation_input.explanation_focus,
            fallback_used=True,
            error="feature_disabled",
        )

    try:
        if provider == "mock":
            text = _build_rule_explanation(explanation_input)
        else:
            raise ValueError(f"Unsupported LLM_ANOMALY_EXPLANATION_PROVIDER: {provider}")

        return AnomalyExplanationOutput(
            explanation_text=text,
            provider=provider or "mock",
            explanation_focus=explanation_input.explanation_focus,
            fallback_used=False,
            error="",
        )
    except Exception as exc:
        return AnomalyExplanationOutput(
            explanation_text=_build_rule_explanation(explanation_input),
            provider=provider or "mock",
            explanation_focus=explanation_input.explanation_focus,
            fallback_used=True,
            error=str(exc)[:200],
        )
