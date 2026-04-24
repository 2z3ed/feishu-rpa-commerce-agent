from __future__ import annotations

from urllib.parse import urlparse


def _safe_domain(url: str) -> str:
    try:
        host = (urlparse(url).netloc or "").strip()
        return host or "-"
    except Exception:
        return "-"


def build_discovery_candidates_card(*, query: str, batch_id: int | str, candidates: list[dict], max_items: int = 5) -> dict:
    items = candidates[: max(0, int(max_items))]

    elements: list[dict] = []
    for idx, c in enumerate(items, start=1):
        title = str(c.get("title") or c.get("name") or "未命名候选")
        url = str(c.get("url") or "")
        domain = _safe_domain(url) if url else "-"
        line: str
        if url:
            line = f"{idx}. [{title}]({url})（{domain}）"
        else:
            line = f"{idx}. {title}（{domain}）"
        elements.append({"tag": "div", "text": {"tag": "lark_md", "content": line}})
        elements.append(
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "type": "primary",
                        "text": {"tag": "plain_text", "content": "加入监控"},
                        "value": {
                            "action": "add_from_candidate",
                            "batch_id": int(batch_id) if str(batch_id).isdigit() else batch_id,
                            "candidate_index": idx,
                            "query": query,
                        },
                    }
                ],
            }
        )

    if not elements:
        elements.append({"tag": "div", "text": {"tag": "lark_md", "content": "（无候选项）"}})

    md = "\n".join(
        [
            f"**Query**：{query}",
            f"**Batch**：{batch_id}",
            "",
            "**候选（前几条）**：点击每条下方按钮可直接纳管",
        ]
    )

    return {
        "config": {"wide_screen_mode": True},
        "header": {"title": {"tag": "plain_text", "content": f"搜索结果：{query}"}},
        "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": md}}, {"tag": "hr"}, *elements, {"tag": "hr"}, {"tag": "note", "elements": [{"tag": "lark_md", "content": "也可继续回复：**加入监控第 N 个**"}]}],
    }

