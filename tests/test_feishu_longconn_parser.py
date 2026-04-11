import json

from app.services.feishu.parser import parse_p2_im_message_receive_v1


class MockMessage:
    """Aligns with parser: message_type=text, content=JSON string {\"text\": \"...\"}."""

    def __init__(
        self,
        message_id,
        chat_id,
        create_time,
        content_json_text,
        message_type="text",
        chat_type="p2p",
    ):
        self.message_id = message_id
        self.chat_id = chat_id
        self.create_time = create_time
        self.message_type = message_type
        self.chat_type = chat_type
        self.content = content_json_text


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


def test_parse_message_event_success():
    mock_msg = MockMessage(
        message_id="msg_123456",
        chat_id="chat_abc",
        create_time="1700000000",
        content_json_text=json.dumps({"text": "Hello world"}),
    )
    mock_event = MockEvent(mock_msg, sender=MockSender("open_xyz"))
    mock_request = MockP2ImMessageReceiveV1(mock_event)

    result = parse_p2_im_message_receive_v1(mock_request)
    
    assert result is not None
    assert result.message_id == "msg_123456"
    assert result.chat_id == "chat_abc"
    assert result.open_id == "open_xyz"
    assert result.text == "Hello world"
    assert result.create_time == "1700000000"


def test_parse_message_event_non_text():
    mock_msg = MockMessage(
        message_id="msg_123456",
        chat_id="chat_abc",
        create_time="1700000000",
        content_json_text=json.dumps({"text": ""}),
    )
    mock_event = MockEvent(mock_msg, sender=MockSender("open_xyz"))
    mock_request = MockP2ImMessageReceiveV1(mock_event)

    result = parse_p2_im_message_receive_v1(mock_request)
    
    assert result is None


def test_parse_message_event_no_message():
    mock_request = MockP2ImMessageReceiveV1(None)
    result = parse_p2_im_message_receive_v1(mock_request)
    assert result is None