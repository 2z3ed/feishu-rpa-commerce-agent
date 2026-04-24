from app.services.feishu.cards.discovery_candidates import build_discovery_candidates_card
from app.services.feishu.longconn import FeishuLongConnListener


class _FakeEvent:
    def __init__(self, payload: dict):
        self._payload = payload

    def to_dict(self):
        return self._payload


def test_discovery_candidates_card_contains_add_buttons():
    card = build_discovery_candidates_card(
        query="重力毯",
        batch_id=12,
        candidates=[
            {"candidate_id": 1001, "title": "重力毯 A", "url": "https://a.example"},
            {"candidate_id": 1002, "title": "重力毯 B", "url": "https://b.example"},
        ],
    )
    actions = [elem for elem in card["elements"] if elem.get("tag") == "action"]
    assert len(actions) == 2
    first_value = actions[0]["actions"][0]["value"]
    assert first_value["action"] == "add_from_candidate"
    assert first_value["batch_id"] == 12
    assert first_value["candidate_index"] == 1
    assert first_value["query"] == "重力毯"


def test_parse_card_action_payload():
    raw = {
        "event": {
            "action": {
                "value": {
                    "action": "add_from_candidate",
                    "batch_id": 9,
                    "candidate_index": 2,
                    "query": "重力毯",
                }
            }
        }
    }
    action_name, batch_id, candidate_index, query = FeishuLongConnListener._parse_card_action_payload(raw)
    assert action_name == "add_from_candidate"
    assert batch_id == 9
    assert candidate_index == 2
    assert query == "重力毯"


def test_card_action_handler_reuses_add_from_candidates(monkeypatch):
    listener = FeishuLongConnListener()
    sent_messages: list[tuple[str, str, str]] = []

    monkeypatch.setattr(
        "app.services.feishu.longconn._load_latest_discovery_context",
        lambda **_: {
            "batch_id": 12,
            "source_type": "discovery",
            "candidates": [{"candidate_id": 1001, "title": "重力毯 A", "url": "https://a.example"}],
        },
    )
    monkeypatch.setattr(
        "app.services.feishu.longconn.execute_action",
        lambda state: {"status": "succeeded", "result_summary": f"已加入监控。\n- 选择编号：第 {state['slots']['index']} 个"},
    )
    monkeypatch.setattr(
        "app.services.feishu.longconn.feishu_client.send_text_message",
        lambda receive_id, text, receive_id_type="open_id": sent_messages.append((receive_id, text, receive_id_type)) or True,
    )

    payload = {
        "event": {
            "chat_id": "chat-1",
            "operator": {"open_id": "ou_123"},
            "open_message_id": "om_123",
            "action": {
                "value": {
                    "action": "add_from_candidate",
                    "batch_id": 12,
                    "candidate_index": 1,
                    "query": "重力毯",
                }
            },
        }
    }
    listener._handle_card_action_event(_FakeEvent(payload))
    assert sent_messages
    assert sent_messages[0][0] == "chat-1"
    assert "已加入监控" in sent_messages[0][1]
    assert sent_messages[0][2] == "chat_id"


def test_card_action_handler_invalid_action_does_not_trigger(monkeypatch):
    listener = FeishuLongConnListener()
    sent_messages: list[tuple[str, str, str]] = []
    monkeypatch.setattr(
        "app.services.feishu.longconn.feishu_client.send_text_message",
        lambda receive_id, text, receive_id_type="open_id": sent_messages.append((receive_id, text, receive_id_type)) or True,
    )
    payload = {
        "event": {
            "chat_id": "chat-1",
            "operator": {"open_id": "ou_123"},
            "action": {
                "value": {
                    "action": "noop",
                    "batch_id": 12,
                    "candidate_index": 1,
                    "query": "重力毯",
                }
            },
        }
    }
    listener._handle_card_action_event(_FakeEvent(payload))
    assert sent_messages == []

