from app.services.feishu.cards.monitor_targets import build_monitor_target_delete_confirm_card
from app.services.feishu.longconn import FeishuLongConnListener


class _FakeEvent:
    def __init__(self, payload: dict):
        self._payload = payload

    def to_dict(self):
        return self._payload


def test_build_delete_confirm_card_contains_required_fields():
    card = build_monitor_target_delete_confirm_card(
        target={"target_id": 7, "name": "商品A", "status": "active", "url": "https://a.example"}
    )
    text_blob = "\n".join(
        elem.get("text", {}).get("content", "")
        for elem in card["elements"]
        if isinstance(elem, dict) and elem.get("tag") == "div"
    )
    assert "对象名称：商品A" in text_blob
    assert "对象ID：7" in text_blob
    assert "https://a.example" in text_blob
    assert "当前状态：active" in text_blob
    assert "删除后，该对象将不再进入监控列表" in text_blob

    actions = [elem for elem in card["elements"] if elem.get("tag") == "action"]
    assert len(actions) == 1
    buttons = actions[0]["actions"]
    assert buttons[0]["text"]["content"] == "确认删除"
    assert buttons[0]["value"]["action"] == "delete_monitor_target_confirm"
    assert buttons[0]["value"]["target_id"] == 7
    assert buttons[1]["text"]["content"] == "取消"
    assert buttons[1]["value"]["action"] == "delete_monitor_target_cancel"
    assert buttons[1]["value"]["target_id"] == 7


def test_delete_request_sends_confirm_card_not_delete(monkeypatch):
    listener = FeishuLongConnListener()
    calls: list[tuple[str, int]] = []
    sent_cards: list[tuple[str, str, dict]] = []

    monkeypatch.setattr(
        "app.services.feishu.longconn.BServiceClient.get_monitor_targets",
        lambda _self: {"targets": [{"target_id": 7, "name": "商品A", "status": "active", "url": "https://a.example"}]},
    )
    monkeypatch.setattr(
        "app.services.feishu.longconn.BServiceClient.delete_monitor_target",
        lambda _self, target_id: calls.append(("delete", target_id)) or {"ok": True},
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
            "action": {
                "value": {
                    "action": "delete_monitor_target_request",
                    "target_id": 7,
                    "source": "monitor_list_card",
                }
            },
        }
    }
    listener._handle_card_action_event(_FakeEvent(payload))

    assert calls == []
    assert len(sent_cards) == 1
    _, receive_id_type, card = sent_cards[0]
    assert receive_id_type == "chat_id"
    card_text = "\n".join(
        elem.get("text", {}).get("content", "")
        for elem in card["elements"]
        if isinstance(elem, dict) and elem.get("tag") == "div"
    )
    assert "确认删除监控对象" not in card_text  # title 在 header，不在 body
    assert "对象ID：7" in card_text


def test_delete_confirm_calls_b_delete(monkeypatch):
    listener = FeishuLongConnListener()
    calls: list[tuple[str, int]] = []
    sent_messages: list[str] = []

    monkeypatch.setattr(
        "app.services.feishu.longconn.BServiceClient.delete_monitor_target_raw_response",
        lambda _self, target_id: calls.append(("delete", target_id))
        or {"ok": True, "data": {"deleted": True}, "error": None},
    )
    monkeypatch.setattr(
        "app.services.feishu.longconn.BServiceClient.get_monitor_targets",
        lambda _self: {"targets": [{"target_id": 2, "name": "其他对象", "status": "active"}]},
    )
    monkeypatch.setattr(
        "app.services.feishu.longconn.feishu_client.send_text_message",
        lambda receive_id, text, receive_id_type="open_id": sent_messages.append(text) or True,
    )

    payload = {
        "event": {
            "chat_id": "chat-1",
            "operator": {"open_id": "ou_123"},
            "action": {
                "value": {
                    "action": "delete_monitor_target_confirm",
                    "target_id": 7,
                    "source": "delete_confirm_card",
                }
            },
        }
    }
    listener._handle_card_action_event(_FakeEvent(payload))

    assert calls == [("delete", 7)]
    assert sent_messages
    assert "已删除监控对象" in sent_messages[0]


def test_delete_confirm_verify_exists_returns_unconfirmed(monkeypatch):
    listener = FeishuLongConnListener()
    sent_messages: list[str] = []

    monkeypatch.setattr(
        "app.services.feishu.longconn.BServiceClient.delete_monitor_target_raw_response",
        lambda _self, _target_id: {"ok": True, "data": {"deleted": True}, "error": None},
    )
    monkeypatch.setattr(
        "app.services.feishu.longconn.BServiceClient.get_monitor_targets",
        lambda _self: {"targets": [{"target_id": 7, "name": "商品A", "status": "active"}]},
    )
    monkeypatch.setattr(
        "app.services.feishu.longconn.feishu_client.send_text_message",
        lambda *args, **kwargs: sent_messages.append(str(kwargs.get("text") or (args[1] if len(args) > 1 else ""))) or True,
    )

    payload = {
        "event": {
            "chat_id": "chat-1",
            "operator": {"open_id": "ou_123"},
            "action": {
                "value": {
                    "action": "delete_monitor_target_confirm",
                    "target_id": 7,
                    "source": "delete_confirm_card",
                }
            },
        }
    }
    listener._handle_card_action_event(_FakeEvent(payload))
    assert sent_messages
    assert "删除未确认，请稍后重试或检查服务状态" in sent_messages[0]
    assert "当前状态：active" in sent_messages[0]


def test_delete_cancel_does_not_call_b_delete(monkeypatch):
    listener = FeishuLongConnListener()
    calls: list[tuple[str, int]] = []
    sent_messages: list[str] = []

    monkeypatch.setattr(
        "app.services.feishu.longconn.BServiceClient.delete_monitor_target",
        lambda _self, target_id: calls.append(("delete", target_id)) or {"ok": True},
    )
    monkeypatch.setattr(
        "app.services.feishu.longconn.feishu_client.send_text_message",
        lambda receive_id, text, receive_id_type="open_id": sent_messages.append(text) or True,
    )

    payload = {
        "event": {
            "chat_id": "chat-1",
            "operator": {"open_id": "ou_123"},
            "action": {
                "value": {
                    "action": "delete_monitor_target_cancel",
                    "target_id": 7,
                    "source": "delete_confirm_card",
                }
            },
        }
    }
    listener._handle_card_action_event(_FakeEvent(payload))

    assert calls == []
    assert sent_messages
    assert "已取消删除" in sent_messages[0]
