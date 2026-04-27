from __future__ import annotations

from app.core.config import settings
from app.schemas.llm_action_plan import ActionPlanInput, ActionPlanOutput


def _display_name(item: dict, idx: int) -> str:
    name = str(item.get("name") or item.get("product_name") or "").strip()
    if name:
        return name
    target_id = item.get("target_id")
    if target_id not in (None, ""):
        return f"对象ID={target_id}"
    return f"对象#{idx}"


def _fallback_action(item: dict) -> str:
    suggestion = str(item.get("action_suggestion") or "").strip()
    if suggestion:
        return suggestion
    category = str(item.get("action_category") or "").strip().lower()
    if category in {"url_fix", "replace_url"}:
        return "建议替换为商品详情页 URL 后再重新采集。"
    if category in {"retry", "retry_probe"}:
        return "建议人工确认后执行手动重试采集。"
    if bool(item.get("manual_review_required")):
        return "建议先人工复核页面和价格来源，再决定下一步动作。"
    return "建议继续观察，并在价格信号异常时人工复核。"


def _pick_by_group(targets: list[dict], *, group: str) -> list[dict]:
    selected: list[dict] = []
    for item in targets:
        if not isinstance(item, dict):
            continue
        category = str(item.get("action_category") or "").strip().lower()
        manual = bool(item.get("manual_review_required"))
        priority = str(item.get("action_priority") or "").strip().lower()
        probe_status = str(item.get("price_probe_status") or "").strip().lower()
        price_source = str(item.get("price_source") or "").strip().lower()
        page_type = str(item.get("price_page_type") or "").strip().lower()

        if group == "manual_review":
            if manual or priority == "high":
                selected.append(item)
        elif group == "url_fix":
            if category in {"url_fix", "replace_url"} or page_type in {"search_page", "listing_page"}:
                selected.append(item)
        elif group == "retry":
            if category in {"retry", "retry_probe"} or probe_status in {"failed", "fallback_mock"}:
                selected.append(item)
        elif group == "observe":
            if (
                not manual
                and category not in {"url_fix", "replace_url", "retry", "retry_probe"}
                and priority not in {"high"}
                and probe_status not in {"failed", "fallback_mock"}
                and price_source not in {"mock_price", "fallback_mock"}
            ):
                selected.append(item)
    return selected


def _format_group_lines(title: str, targets: list[dict], empty_text: str, limit: int = 3) -> list[str]:
    lines = [title]
    if not targets:
        lines.append(f"- {empty_text}")
        return lines
    lines.append(f"- 共 {len(targets)} 个对象，建议优先看前 {min(limit, len(targets))} 个：")
    for idx, item in enumerate(targets[:limit], start=1):
        lines.append(f"  {idx}) {_display_name(item, idx)}：{_fallback_action(item)}")
    return lines


def _build_rule_action_plan(action_plan_input: ActionPlanInput) -> str:
    stats = action_plan_input.stats
    targets = action_plan_input.targets if isinstance(action_plan_input.targets, list) else []
    if stats.target_count <= 0:
        return "当前还没有监控对象，暂时无法生成处理计划。建议先获取监控对象或添加监控链接。"

    manual_targets = _pick_by_group(targets, group="manual_review")
    url_fix_targets = _pick_by_group(targets, group="url_fix")
    retry_targets = _pick_by_group(targets, group="retry")
    observe_targets = _pick_by_group(targets, group="observe")

    lines = [
        "当前处理优先级判断：",
        (
            f"建议按“高优先级 + 人工复核优先”推进。当前共 {stats.target_count} 个对象，"
            f"高优先级 {stats.high_priority_count} 个，人工复核 {stats.manual_review_count} 个。"
        ),
        "",
    ]
    lines.extend(
        _format_group_lines(
            "第一批：必须人工复核的对象",
            manual_targets,
            "暂无必须人工复核对象，但仍建议抽样核对高影响对象。",
        )
    )
    lines.append("")
    lines.extend(
        _format_group_lines(
            "第二批：建议替换 URL 的对象",
            url_fix_targets,
            "暂无明显 URL 问题对象。",
        )
    )
    lines.append("")
    lines.extend(
        _format_group_lines(
            "第三批：建议手动重试采集的对象",
            retry_targets,
            "暂无明显需要重试采集的对象。",
        )
    )
    lines.append("")
    lines.extend(
        _format_group_lines(
            "第四批：可暂缓观察的对象",
            observe_targets,
            "暂无可直接暂缓观察对象，建议先完成前三批处理。",
        )
    )
    lines.extend(
        [
            "",
            "人工确认点：",
            "- 对于 low/unknown 可信度或 mock_price/fallback_mock 对象，先人工确认页面与价格来源。",
            "- 对于 search_page/listing_page 对象，先替换为商品详情页 URL 再考虑后续处理。",
            "",
            "不会自动处理提醒：",
            "本计划仅用于人工决策，系统不会自动刷新、自动重试、自动替换 URL、自动删除对象或自动改价。",
        ]
    )
    return "\n".join(lines)


def run_llm_action_plan(action_plan_input: ActionPlanInput) -> ActionPlanOutput:
    provider = (settings.LLM_ACTION_PLAN_PROVIDER or "mock").strip().lower()
    if not settings.ENABLE_LLM_ACTION_PLAN:
        return ActionPlanOutput(
            plan_text=_build_rule_action_plan(action_plan_input),
            provider=provider or "mock",
            plan_focus=action_plan_input.plan_focus,
            fallback_used=True,
            error="feature_disabled",
        )

    try:
        if provider == "mock":
            text = _build_rule_action_plan(action_plan_input)
        else:
            raise ValueError(f"Unsupported LLM_ACTION_PLAN_PROVIDER: {provider}")
        return ActionPlanOutput(
            plan_text=text,
            provider=provider or "mock",
            plan_focus=action_plan_input.plan_focus,
            fallback_used=False,
            error="",
        )
    except Exception as exc:
        return ActionPlanOutput(
            plan_text=_build_rule_action_plan(action_plan_input),
            provider=provider or "mock",
            plan_focus=action_plan_input.plan_focus,
            fallback_used=True,
            error=str(exc)[:200],
        )
