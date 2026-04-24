from app.services.feishu.cards.monitor_targets import build_monitor_targets_card
from app.services.feishu.longconn import FeishuLongConnListener


class _FakeEvent:
    def __init__(self, payload: dict):
        self._payload = payload

    def to_dict(self):
        return self._payload


def _build_targets(count: int) -> list[dict]:
    items: list[dict] = []
    for i in range(1, count + 1):
        items.append(
            {
                "target_id": i,
                "name": f"商品{i}",
                "status": "active" if i % 2 else "inactive",
                "url": f"https://example.com/{i}",
            }
        )
    return items


def test_monitor_targets_card_page1_shows_more_button_and_next_payload():
    card = build_monitor_targets_card(targets=_build_targets(8), page=1, limit=5)
    text_blob = "\n".join(
        elem.get("text", {}).get("content", "")
        for elem in card["elements"]
        if isinstance(elem, dict) and elem.get("tag") == "div"
    )
    assert "商品1" in text_blob
    assert "商品5" in text_blob
    assert "商品6" not in text_blob
    assert "删除" not in text_blob

    more_action = None
    for elem in card["elements"]:
        if elem.get("tag") != "action":
            continue
        first_btn = (elem.get("actions") or [{}])[0]
        value = first_btn.get("value") or {}
        if value.get("action") == "monitor_targets_next_page":
            more_action = value
            break
    assert more_action is not None
    assert more_action["page"] == 2
    assert more_action["limit"] == 5
    assert more_action["source"] == "monitor_list_card"


def test_monitor_targets_card_page2_no_more_button_and_keep_manage_buttons():
    card = build_monitor_targets_card(targets=_build_targets(8), page=2, limit=5)
    text_blob = "\n".join(
        elem.get("text", {}).get("content", "")
        for elem in card["elements"]
        if isinstance(elem, dict) and elem.get("tag") == "div"
    )
    assert "商品6" in text_blob
    assert "商品8" in text_blob
    assert "商品5" not in text_blob

    action_values = []
    for elem in card["elements"]:
        if elem.get("tag") != "action":
            continue
        value = ((elem.get("actions") or [{}])[0]).get("value") or {}
        action_values.append(value.get("action"))
    assert "pause_monitor_target" in action_values
    assert "resume_monitor_target" in action_values
    assert "monitor_targets_next_page" not in action_values


def test_card_action_monitor_targets_next_page_sends_next_card(monkeypatch):
    listener = FeishuLongConnListener()
    sent_cards: list[tuple[str, str, dict]] = []

    monkeypatch.setattr(
        "app.services.feishu.longconn.BServiceClient.get_monitor_targets",
        lambda _self: {"targets": _build_targets(8)},
    )
    monkeypatch.setattr(
        "app.services.feishu.longconn.feishu_client.send_interactive_message",
        lambda receive_id, card, receive_id_type="open_id": sent_cards.append((receive_id, receive_id_type, card)) or True,
    )
    monkeypatch.setattr(
        "app.services.feishu.longconn.feishu_client.send_text_message",
        lambda *_args, **_kwargs: True,
    )

    payload = {
        "event": {
            "chat_id": "chat-1",
            "operator": {"open_id": "ou_123"},
            "action": {"value": {"action": "monitor_targets_next_page", "page": 2, "limit": 5, "source": "monitor_list_card"}},
        }
    }
    listener._handle_card_action_event(_FakeEvent(payload))

    assert len(sent_cards) == 1
    receive_id, receive_id_type, card = sent_cards[0]
    assert receive_id == "chat-1"
    assert receive_id_type == "chat_id"
    text_blob = "\n".join(
        elem.get("text", {}).get("content", "")
        for elem in card["elements"]
        if isinstance(elem, dict) and elem.get("tag") == "div"
    )
    assert "商品6" in text_blob
    assert "商品1" not in text_blob
