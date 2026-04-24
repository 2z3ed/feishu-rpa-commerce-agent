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

    lines: list[str] = []
    for idx, c in enumerate(items, start=1):
        title = str(c.get("title") or c.get("name") or "未命名候选")
        url = str(c.get("url") or "")
        domain = _safe_domain(url) if url else "-"
        if url:
            lines.append(f"{idx}. [{title}]({url})（{domain}）")
        else:
            lines.append(f"{idx}. {title}（{domain}）")

    if not lines:
        lines.append("（无候选项）")

    md = "\n".join(
        [
            f"**Query**：{query}",
            f"**Batch**：{batch_id}",
            "",
            "**候选（前几条）**：",
            *lines,
            "",
            "继续回复：**加入监控第 N 个**",
        ]
    )

    return {
        "config": {"wide_screen_mode": True},
        "header": {"title": {"tag": "plain_text", "content": f"搜索结果：{query}"}},
        "elements": [
            {"tag": "div", "text": {"tag": "lark_md", "content": md}},
            {"tag": "hr"},
            {
                "tag": "note",
                "elements": [{"tag": "lark_md", "content": "本轮仅展示卡片，不提供按钮；后续纳管仍走文本编号命令。"}],
            },
        ],
    }

