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
    if status not in {"active", "inactive"}:
        status = "active"
    url = str(item.get("url") or item.get("product_url") or "").strip()
    return {
        "target_id": target_id,
        "name": name,
        "status": status,
        "url": url,
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
