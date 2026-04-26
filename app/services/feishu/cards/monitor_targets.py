from __future__ import annotations


def _normalize_target(item: dict) -> dict | None:
    if not isinstance(item, dict):
        return None
    raw_id = item.get("target_id")
    if raw_id in (None, ""):
        raw_id = item.get("id") or item.get("product_id")
    if raw_id in (None, ""):
        return None
    try:
        target_id = int(raw_id)
    except Exception:
        return None
    name = str(item.get("name") or item.get("product_name") or item.get("title") or "未命名对象")
    status = str(item.get("status") or ("active" if item.get("is_active", True) else "inactive")).strip().lower()
    if status in {"deleted", "archived"}:
        return None
    if status not in {"active", "inactive"}:
        status = "active"
    url = str(item.get("url") or item.get("product_url") or "").strip()
    current_price = item.get("current_price")
    last_price = item.get("last_price")
    price_delta = item.get("price_delta")
    price_delta_percent = item.get("price_delta_percent")
    price_changed = bool(item.get("price_changed", False))
    last_checked_at = item.get("last_checked_at")
    price_source = str(item.get("price_source") or "").strip()
    price_probe_status = str(item.get("price_probe_status") or "unknown").strip().lower()
    price_probe_error = str(item.get("price_probe_error") or "").strip().lower()
    price_probe_checked_at = item.get("price_probe_checked_at")
    price_confidence = str(item.get("price_confidence") or "unknown").strip().lower() or "unknown"
    price_page_type = str(item.get("price_page_type") or "unknown").strip().lower() or "unknown"
    price_anomaly_status = str(item.get("price_anomaly_status") or "unknown").strip().lower() or "unknown"
    price_anomaly_reason = str(item.get("price_anomaly_reason") or "").strip()
    price_action_suggestion = str(item.get("price_action_suggestion") or "").strip()
    action_priority = str(item.get("action_priority") or "unknown").strip().lower() or "unknown"
    action_category = str(item.get("action_category") or "unknown").strip().lower() or "unknown"
    manual_review_required = bool(item.get("manual_review_required", False))
    alert_candidate = bool(item.get("alert_candidate", False))
    action_suggestion = str(item.get("action_suggestion") or "").strip()
    return {
        "target_id": target_id,
        "name": name,
        "status": status,
        "url": url,
        "current_price": current_price,
        "last_price": last_price,
        "price_delta": price_delta,
        "price_delta_percent": price_delta_percent,
        "price_changed": price_changed,
        "last_checked_at": last_checked_at,
        "price_source": price_source,
        "price_probe_status": price_probe_status or "unknown",
        "price_probe_error": price_probe_error or None,
        "price_probe_checked_at": price_probe_checked_at,
        "price_confidence": price_confidence,
        "price_page_type": price_page_type,
        "price_anomaly_status": price_anomaly_status,
        "price_anomaly_reason": price_anomaly_reason or None,
        "price_action_suggestion": price_action_suggestion or None,
        "action_priority": action_priority,
        "action_category": action_category,
        "manual_review_required": manual_review_required,
        "alert_candidate": alert_candidate,
        "action_suggestion": action_suggestion or None,
    }


def _sanitize_page_limit(page: int, limit: int) -> tuple[int, int]:
    safe_page = int(page) if isinstance(page, int) else 1
    safe_limit = int(limit) if isinstance(limit, int) else 5
    if safe_page <= 0:
        safe_page = 1
    if safe_limit <= 0:
        safe_limit = 5
    if safe_limit > 20:
        safe_limit = 20
    return safe_page, safe_limit


def build_monitor_targets_card(
    *,
    targets: list[dict],
    max_items: int = 5,
    page: int = 1,
    limit: int | None = None,
) -> dict:
    normalized: list[dict] = []
    for item in targets:
        target = _normalize_target(item)
        if target is None:
            continue
        normalized.append(target)

    page_size = int(max_items) if limit is None else int(limit)
    safe_page, safe_limit = _sanitize_page_limit(page=page, limit=page_size)
    total = len(normalized)
    start_index = (safe_page - 1) * safe_limit
    end_index = start_index + safe_limit
    shown = normalized[start_index:end_index]
    has_next = end_index < total
    display_start = start_index + 1 if shown else 0
    display_end = start_index + len(shown) if shown else 0
    elements: list[dict] = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "\n".join(
                    [
                        "**监控对象管理**",
                        f"当前监控对象总数：**{total}**",
                        "",
                        f"当前第 {safe_page} 页（每页 {safe_limit} 条）。",
                        (
                            f"本页展示：第 {display_start}-{display_end} 条。"
                            if shown
                            else "本页暂无监控对象。"
                        ),
                    ]
                ),
            },
        },
        {"tag": "hr"},
    ]

    if not shown:
        elements.append({"tag": "div", "text": {"tag": "lark_md", "content": "当前没有监控对象。"}})
    else:
        for local_idx, target in enumerate(shown, start=1):
            idx = start_index + local_idx
            action_name = "pause_monitor_target" if target["status"] == "active" else "resume_monitor_target"
            action_text = "暂停监控" if target["status"] == "active" else "恢复监控"
            url_line = target["url"] if target["url"] else "-"
            current_price = target.get("current_price")
            last_price = target.get("last_price")
            price_delta = target.get("price_delta")
            price_delta_percent = target.get("price_delta_percent")
            price_changed = bool(target.get("price_changed", False))
            last_checked_at = str(target.get("last_checked_at") or "").strip()
            price_source = str(target.get("price_source") or "").strip()
            probe_status = str(target.get("price_probe_status") or "unknown").strip().lower() or "unknown"
            probe_error = str(target.get("price_probe_error") or "").strip().lower()
            probe_checked_at = str(target.get("price_probe_checked_at") or "").strip()

            if current_price is None:
                current_price_line = "暂未采集"
                last_price_line = "暂未采集"
                change_line = "暂未采集"
                checked_line = "-"
                source_line = "-"
            else:
                current_price_line = str(current_price)
                last_price_line = "暂未采集" if last_price is None else str(last_price)
                if price_delta is None:
                    change_line = "暂无变化数据"
                else:
                    trend = "上涨" if float(price_delta) > 0 else ("下降" if float(price_delta) < 0 else "持平")
                    if price_delta_percent is None:
                        change_line = f"{trend} {abs(float(price_delta))}"
                    else:
                        change_line = f"{trend} {abs(float(price_delta))}（{float(price_delta_percent):+.2f}%）"
                checked_line = last_checked_at or "-"
                source_line = price_source or "mock_price"
                if not price_changed and price_delta is None:
                    change_line = "暂无变化数据"
            probe_checked_line = probe_checked_at or checked_line
            confidence_line = str(target.get("price_confidence") or "unknown")
            page_type_line = str(target.get("price_page_type") or "unknown")
            anomaly_status_line = str(target.get("price_anomaly_status") or "unknown")
            anomaly_reason_line = str(target.get("price_anomaly_reason") or "-")
            suggestion_line = str(target.get("price_action_suggestion") or "-")
            action_priority_line = str(target.get("action_priority") or "unknown")
            action_category_line = str(target.get("action_category") or "unknown")
            manual_review_required_line = "是" if bool(target.get("manual_review_required", False)) else "否"
            alert_candidate_line = "是" if bool(target.get("alert_candidate", False)) else "否"
            action_suggestion_line = str(target.get("action_suggestion") or "-")

            elements.append(
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "\n".join(
                            [
                                f"**{idx}. {target['name']}**",
                                f"- 对象ID：{target['target_id']}",
                                f"- 状态：{target['status']}",
                                f"- URL：{url_line}",
                                f"- 当前价格：{current_price_line}",
                                f"- 上次价格：{last_price_line}",
                                f"- 变化：{change_line}",
                                f"- 最后检测：{checked_line}",
                                f"- 来源：{source_line}",
                                f"- 采集状态：{probe_status}",
                                f"- 采集时间：{probe_checked_line}",
                                (f"- 采集原因：{probe_error}" if probe_error else "- 采集原因：-"),
                                f"- 可信度：{confidence_line}",
                                f"- 页面类型：{page_type_line}",
                                f"- 异常状态：{anomaly_status_line}",
                                f"- 异常原因：{anomaly_reason_line}",
                                f"- 建议：{suggestion_line}",
                                f"- 处理优先级：{action_priority_line}",
                                f"- 处理类型：{action_category_line}",
                                f"- 需人工接管：{manual_review_required_line}",
                                f"- 提醒候选：{alert_candidate_line}",
                                f"- 处理建议：{action_suggestion_line}",
                            ]
                        ),
                    },
                }
            )
            elements.append(
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "type": "default",
                            "text": {"tag": "plain_text", "content": action_text},
                            "value": {
                                "action": action_name,
                                "target_id": target["target_id"],
                                "source": "monitor_list_card",
                            },
                        },
                        {
                            "tag": "button",
                            "type": "danger",
                            "text": {"tag": "plain_text", "content": "删除监控"},
                            "value": {
                                "action": "delete_monitor_target_request",
                                "target_id": target["target_id"],
                                "source": "monitor_list_card",
                            },
                        }
                    ],
                }
            )
            if local_idx != len(shown):
                elements.append({"tag": "hr"})

    if has_next:
        elements.append({"tag": "hr"})
        elements.append(
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "type": "primary",
                        "text": {"tag": "plain_text", "content": "查看更多"},
                        "value": {
                            "action": "monitor_targets_next_page",
                            "page": safe_page + 1,
                            "limit": safe_limit,
                            "source": "monitor_list_card",
                        },
                    }
                ],
            }
        )

    elements.append({"tag": "hr"})
    elements.append(
        {
            "tag": "note",
            "elements": [
                {
                    "tag": "lark_md",
                    "content": "也可继续使用文本命令：`暂停监控第 N 个` / `恢复监控第 N 个`。",
                }
            ],
        }
    )

    return {
        "config": {"wide_screen_mode": True},
        "header": {"title": {"tag": "plain_text", "content": "当前监控对象"}},
        "elements": elements,
    }


def build_monitor_target_delete_confirm_card(*, target: dict) -> dict:
    normalized = _normalize_target(target)
    if normalized is None:
        raise ValueError("无效的监控对象，无法生成删除确认卡片")
    url_line = normalized["url"] if normalized["url"] else "-"
    return {
        "config": {"wide_screen_mode": True},
        "header": {"title": {"tag": "plain_text", "content": "确认删除监控对象"}},
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "\n".join(
                        [
                            f"**对象名称：{normalized['name']}**",
                            f"- 对象ID：{normalized['target_id']}",
                            f"- URL：{url_line}",
                            f"- 当前状态：{normalized['status']}",
                            "",
                            "⚠️ 删除后，该对象将不再进入监控列表。",
                        ]
                    ),
                },
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "type": "danger",
                        "text": {"tag": "plain_text", "content": "确认删除"},
                        "value": {
                            "action": "delete_monitor_target_confirm",
                            "target_id": normalized["target_id"],
                            "source": "delete_confirm_card",
                        },
                    },
                    {
                        "tag": "button",
                        "type": "default",
                        "text": {"tag": "plain_text", "content": "取消"},
                        "value": {
                            "action": "delete_monitor_target_cancel",
                            "target_id": normalized["target_id"],
                            "source": "delete_confirm_card",
                        },
                    },
                ],
            },
        ],
    }
