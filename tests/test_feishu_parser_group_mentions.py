"""Group chat: only @ current bot (mention_event.id.open_id) should parse."""
import json

import pytest

from app.core.config import settings
from app.services.feishu.parser import parse_p2_im_message_receive_v1


class MockUserId:
    def __init__(self, open_id: str):
        self.open_id = open_id
        self.union_id = ""
        self.user_id = ""


class MockMentionEvent:
    """Aligns with lark_oapi MentionEvent: key, id(UserId), name, tenant_key."""

    def __init__(self, key: str, open_id: str, name: str = ""):
        self.key = key
        self.id = MockUserId(open_id)
        self.name = name
        self.tenant_key = ""


class MockMessage:
    def __init__(
        self,
        message_id,
        chat_id,
        create_time,
        content_json_text,
        message_type="text",
        chat_type="group",
        mentions=None,
    ):
        self.message_id = message_id
        self.chat_id = chat_id
        self.create_time = create_time
        self.message_type = message_type
        self.chat_type = chat_type
        self.content = content_json_text
        self.mentions = mentions


class MockSender:
    def __init__(self, open_id: str):
        self.sender_id = type("UserId", (), {"open_id": open_id, "user_id": ""})()


class MockEvent:
    def __init__(self, message, sender):
        self.message = message
        self.sender = sender


class MockP2ImMessageReceiveV1:
    def __init__(self, event):
        self.event = event

    def to_dict(self):
        return {}


@pytest.fixture
def bot_open_id(monkeypatch):
    monkeypatch.setattr(settings, "FEISHU_BOT_OPEN_ID", "ou_fixture_bot_open_id")


def test_group_at_other_user_does_not_trigger(bot_open_id):
    text = "@_user_1 查询 SKU X1"
    mock_msg = MockMessage(
        message_id="m1",
        chat_id="cg",
        create_time="1",
        content_json_text=json.dumps({"text": text}),
        chat_type="group",
        mentions=[MockMentionEvent("@_user_1", "ou_someone_else")],
    )
    req = MockP2ImMessageReceiveV1(MockEvent(mock_msg, MockSender("u1")))
    assert parse_p2_im_message_receive_v1(req) is None


def test_group_text_prefix_only_no_mentions_does_not_trigger(bot_open_id):
    mock_msg = MockMessage(
        message_id="m2",
        chat_id="cg",
        create_time="1",
        content_json_text=json.dumps({"text": "@_user_1 hello"}),
        chat_type="group",
        mentions=None,
    )
    req = MockP2ImMessageReceiveV1(MockEvent(mock_msg, MockSender("u1")))
    assert parse_p2_im_message_receive_v1(req) is None


def test_group_at_bot_triggers(bot_open_id):
    text = "@_user_1 查询 SKU X1"
    mock_msg = MockMessage(
        message_id="m3",
        chat_id="cg",
        create_time="1",
        content_json_text=json.dumps({"text": text}),
        chat_type="group",
        mentions=[MockMentionEvent("@_user_1", "ou_fixture_bot_open_id")],
    )
    req = MockP2ImMessageReceiveV1(MockEvent(mock_msg, MockSender("u1")))
    out = parse_p2_im_message_receive_v1(req)
    assert out is not None
    assert "查询 SKU X1" in out.text


def test_group_skipped_when_bot_open_id_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "FEISHU_BOT_OPEN_ID", "")
    mock_msg = MockMessage(
        message_id="m4",
        chat_id="cg",
        create_time="1",
        content_json_text=json.dumps({"text": "@_user_1 hi"}),
        chat_type="group",
        mentions=[MockMentionEvent("@_user_1", "ou_any")],
    )
    req = MockP2ImMessageReceiveV1(MockEvent(mock_msg, MockSender("u1")))
    assert parse_p2_im_message_receive_v1(req) is None
