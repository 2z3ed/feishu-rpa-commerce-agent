from app.services.feishu.cards.monitor_targets import build_monitor_targets_card


def _collect_div_text(card: dict) -> str:
    return "\n".join(
        elem.get("text", {}).get("content", "")
        for elem in card.get("elements", [])
        if isinstance(elem, dict) and elem.get("tag") == "div"
    )


def test_monitor_targets_card_price_fields_uncollected() -> None:
    card = build_monitor_targets_card(
        targets=[
            {
                "target_id": 1,
                "name": "商品A",
                "status": "active",
                "url": "https://example.com/a",
                "current_price": None,
                "last_price": None,
                "price_delta": None,
                "price_delta_percent": None,
                "price_changed": False,
                "last_checked_at": None,
                "price_source": None,
            }
        ]
    )
    text = _collect_div_text(card)
    assert "当前价格：暂未采集" in text
    assert "上次价格：暂未采集" in text
    assert "变化：暂未采集" in text
    assert "最后检测：-" in text
    assert "来源：-" in text


def test_monitor_targets_card_price_fields_collected() -> None:
    card = build_monitor_targets_card(
        targets=[
            {
                "target_id": 2,
                "name": "商品B",
                "status": "active",
                "url": "https://example.com/b",
                "current_price": 199,
                "last_price": 209,
                "price_delta": -10,
                "price_delta_percent": -4.78,
                "price_changed": True,
                "last_checked_at": "2026-04-25 17:30",
                "price_source": "mock_price",
            }
        ]
    )
    text = _collect_div_text(card)
    assert "当前价格：199" in text
    assert "上次价格：209" in text
    assert "变化：下降 10.0（-4.78%）" in text
    assert "最后检测：2026-04-25 17:30" in text
    assert "来源：mock_price" in text
