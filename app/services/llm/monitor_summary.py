from __future__ import annotations

from app.core.config import settings
from app.schemas.llm_monitor_summary import MonitorSummaryInput, MonitorSummaryOutput


def _fallback_action_suggestion(item: dict) -> str:
    suggestion = str(item.get("action_suggestion") or "").strip()
    if suggestion:
        return suggestion
    if bool(item.get("manual_review_required")):
        return "建议人工复核价格来源与页面内容，再决定后续动作。"
    if str(item.get("action_priority") or "").strip().lower() == "high":
        return "建议优先处理该对象并确认风险原因。"
    return "建议持续观察并在必要时人工复核。"


def _risk_reason(item: dict) -> str:
    reason = str(item.get("price_anomaly_reason") or "").strip()
    if reason:
        return reason
    probe_error = str(item.get("price_probe_error") or "").strip()
    if probe_error:
        return f"价格采集异常：{probe_error}"
    confidence = str(item.get("price_confidence") or "").strip().lower()
    if confidence in {"low", "unknown"}:
        return "价格可信度偏低，需要人工复核。"
    if bool(item.get("manual_review_required")):
        return "当前对象被标记为人工接管。"
    return "存在处理优先级，需要尽快确认。"


def _build_overview_summary(summary_input: MonitorSummaryInput) -> str:
    stats = summary_input.stats
    if stats.target_count <= 0:
        return "当前还没有监控对象。建议先添加需要跟踪的商品链接，再让我做整体监控总结。"

    lines = [
        "当前价格监控运营总结：",
        f"1) 当前总体情况：共 {stats.target_count} 个监控对象，异常 {stats.anomaly_count} 个，低可信 {stats.low_confidence_count} 个。",
        f"2) 重点风险：高优先级 {stats.high_priority_count} 个，人工接管 {stats.manual_review_count} 个。",
        "3) 需要人工处理：建议先处理高优先级与人工接管对象，逐个核对页面与价格来源。",
        "4) 建议下一步动作：先做人工复核，再按建议执行重试采集或 URL 修正。",
        "5) 自动处理提醒：当前不建议自动处理，系统不会自动刷新、自动改价或自动删除对象。",
    ]
    return "\n".join(lines)


def _build_priority_targets_summary(summary_input: MonitorSummaryInput) -> str:
    stats = summary_input.stats
    if stats.target_count <= 0:
        return "当前还没有监控对象。建议先添加监控对象后，再查看重点处理清单。"

    targets = summary_input.targets if isinstance(summary_input.targets, list) else []
    ranked: list[dict] = []
    for item in targets:
        if not isinstance(item, dict):
            continue
        if (
            str(item.get("action_priority") or "").strip().lower() == "high"
            or bool(item.get("manual_review_required"))
            or bool(item.get("alert_candidate"))
        ):
            ranked.append(item)
    top_items = ranked[:3]

    lines = [
        "重点处理对象总结：",
        f"- 当前高优先级对象：{stats.high_priority_count} 个",
        f"- 当前人工接管对象：{stats.manual_review_count} 个",
    ]
    if top_items:
        lines.append("- 建议优先处理（前 3 个）：")
        for idx, item in enumerate(top_items, start=1):
            name = str(item.get("name") or item.get("product_name") or "").strip()
            target_id = item.get("target_id")
            display = name or (f"对象ID={target_id}" if target_id not in (None, "") else f"对象#{idx}")
            lines.append(f"  {idx}. {display}")
            lines.append(f"     风险原因：{_risk_reason(item)}")
            lines.append(f"     建议动作：{_fallback_action_suggestion(item)}")
    else:
        lines.append("- 当前没有明显高优先级对象，建议继续观察并定期复核。")

    lines.append("- 提醒：系统不会自动处理，请人工确认后再执行对应动作。")
    return "\n".join(lines)


def _build_health_check_summary(summary_input: MonitorSummaryInput) -> str:
    stats = summary_input.stats
    if stats.target_count <= 0:
        return "当前还没有监控对象，暂无法评估整体健康度。建议先补充监控对象。"

    risk_score = stats.anomaly_count + stats.low_confidence_count + stats.high_priority_count
    if risk_score <= max(1, stats.target_count // 4):
        health_level = "整体偏正常"
    elif risk_score <= max(2, stats.target_count // 2):
        health_level = "整体一般"
    else:
        health_level = "风险较高"

    return "\n".join(
        [
            "监控健康度检查：",
            f"- 当前判断：{health_level}",
            (
                f"- 核心指标：总数 {stats.target_count}，异常 {stats.anomaly_count}，"
                f"低可信 {stats.low_confidence_count}，高优先级 {stats.high_priority_count}"
            ),
            "- 建议下一步：先处理高优先级与人工接管对象，再复核低可信对象页面来源。",
            "- 提醒：系统不会自动执行处理动作，需要人工确认后执行。",
        ]
    )


def _build_rule_summary(summary_input: MonitorSummaryInput) -> str:
    focus = str(summary_input.summary_focus or "overview").strip().lower()
    if focus == "priority_targets":
        return _build_priority_targets_summary(summary_input)
    if focus == "health_check":
        return _build_health_check_summary(summary_input)
    return _build_overview_summary(summary_input)


def _mock_generate_summary(summary_input: MonitorSummaryInput) -> str:
    return _build_rule_summary(summary_input)


def run_llm_monitor_summary(summary_input: MonitorSummaryInput) -> MonitorSummaryOutput:
    provider = (settings.LLM_MONITOR_SUMMARY_PROVIDER or "mock").strip().lower()
    if not settings.ENABLE_LLM_MONITOR_SUMMARY:
        return MonitorSummaryOutput(
            summary_text=_build_rule_summary(summary_input),
            provider=provider or "mock",
            summary_focus=summary_input.summary_focus,
            fallback_used=True,
            error="feature_disabled",
        )

    try:
        if provider == "mock":
            text = _mock_generate_summary(summary_input)
        else:
            raise ValueError(f"Unsupported LLM_MONITOR_SUMMARY_PROVIDER: {provider}")

        return MonitorSummaryOutput(
            summary_text=text,
            provider=provider or "mock",
            summary_focus=summary_input.summary_focus,
            fallback_used=False,
            error="",
        )
    except Exception as exc:
        return MonitorSummaryOutput(
            summary_text=_build_rule_summary(summary_input),
            provider=provider or "mock",
            summary_focus=summary_input.summary_focus,
            fallback_used=True,
            error=str(exc)[:200],
        )
