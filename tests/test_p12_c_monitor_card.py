from app.services.feishu.cards.monitor_targets import build_monitor_targets_card
from app.services.feishu.longconn import FeishuLongConnListener


class _FakeEvent:
    def __init__(self, payload: dict):
        self._payload = payload

    def to_dict(self):
        return self._payload


def test_monitor_targets_card_contains_required_fields_and_buttons():
    card = build_monitor_targets_card(
        targets=[
            {"target_id": 7, "name": "商品A", "status": "active", "url": "https://a.example"},
            {"target_id": 8, "name": "商品B", "status": "inactive", "url": "https://b.example"},
        ],
        max_items=5,
    )

    text_blob = "\n".join(
        elem.get("text", {}).get("content", "")
        for elem in card["elements"]
        if isinstance(elem, dict) and elem.get("tag") == "div"
    )
    assert "当前监控对象总数" in text_blob
    assert "商品A" in text_blob
    assert "对象ID：7" in text_blob
    assert "状态：active" in text_blob
    assert "https://a.example" in text_blob
    assert "商品B" in text_blob
    assert "对象ID：8" in text_blob
    assert "状态：inactive" in text_blob
    assert "https://b.example" in text_blob
    actions = [elem for elem in card["elements"] if elem.get("tag") == "action"]
    assert len(actions) == 2
    first_buttons = actions[0]["actions"]
    second_buttons = actions[1]["actions"]
    assert first_buttons[0]["text"]["content"] == "暂停监控"
    assert first_buttons[0]["value"]["action"] == "pause_monitor_target"
    assert first_buttons[0]["value"]["target_id"] == 7
    assert first_buttons[0]["value"]["source"] == "monitor_list_card"
    assert first_buttons[1]["text"]["content"] == "删除监控"
    assert first_buttons[1]["value"]["action"] == "delete_monitor_target_request"
    assert first_buttons[1]["value"]["target_id"] == 7
    assert second_buttons[0]["text"]["content"] == "恢复监控"
    assert second_buttons[0]["value"]["action"] == "resume_monitor_target"
    assert second_buttons[0]["value"]["target_id"] == 8
    assert second_buttons[0]["value"]["source"] == "monitor_list_card"
    assert second_buttons[1]["text"]["content"] == "删除监控"
    assert second_buttons[1]["value"]["action"] == "delete_monitor_target_request"
    assert second_buttons[1]["value"]["target_id"] == 8


def test_card_action_handler_pause_and_resume(monkeypatch):
    listener = FeishuLongConnListener()
    sent_messages: list[tuple[str, str, str]] = []
    called: list[tuple[str, int]] = []

    monkeypatch.setattr(
        "app.services.feishu.longconn.BServiceClient.pause_monitor_target",
        lambda _self, target_id: called.append(("pause", target_id)) or {"ok": True},
    )
    monkeypatch.setattr(
        "app.services.feishu.longconn.BServiceClient.resume_monitor_target",
        lambda _self, target_id: called.append(("resume", target_id)) or {"ok": True},
    )
    monkeypatch.setattr(
        "app.services.feishu.longconn.feishu_client.send_text_message",
        lambda receive_id, text, receive_id_type="open_id": sent_messages.append((receive_id, text, receive_id_type)) or True,
    )

    pause_payload = {
        "event": {
            "chat_id": "chat-1",
            "operator": {"open_id": "ou_123"},
            "action": {"value": {"action": "pause_monitor_target", "target_id": 7, "source": "monitor_list_card"}},
        }
    }
    listener._handle_card_action_event(_FakeEvent(pause_payload))

    resume_payload = {
        "event": {
            "chat_id": "chat-1",
            "operator": {"open_id": "ou_123"},
            "action": {"value": {"action": "resume_monitor_target", "target_id": 7, "source": "monitor_list_card"}},
        }
    }
    listener._handle_card_action_event(_FakeEvent(resume_payload))

    assert called == [("pause", 7), ("resume", 7)]
    assert len(sent_messages) == 2
    assert "已暂停监控" in sent_messages[0][1]
    assert sent_messages[0][2] == "chat_id"
    assert "已恢复监控" in sent_messages[1][1]
    assert sent_messages[1][2] == "chat_id"
