import json

from app.core.config import settings
from app.graph.nodes.execute_action import execute_action
from app.schemas.ocr_document import OCRDocumentInput
from app.services.feishu.file_attachment import (
    build_ocr_input_from_downloaded_file,
    download_feishu_file,
    resolve_feishu_attachments,
)
from app.services.feishu.parser import parse_p2_im_message_receive_v1


class _DummySenderId:
    def __init__(self, open_id="bot_open_id"):
        self.open_id = open_id


class _DummySender:
    def __init__(self, open_id="bot_open_id"):
        self.sender_id = _DummySenderId(open_id=open_id)


settings.FEISHU_BOT_OPEN_ID = "bot_open_id"


class _DummyMessage:
    def __init__(self, message_type, content, chat_type="group", message_id="om_test", chat_id="oc_test"):
        self.message_type = message_type
        self.content = content
        self.message_id = message_id
        self.chat_id = chat_id
        self.chat_type = chat_type
        self.create_time = "1710000000"
        self.mentions = []


class _DummyEvent:
    def __init__(self, message):
        self.event = type("E", (), {"message": message, "sender": _DummySender()})()

    def to_dict(self):
        return {"event": {"message": {"message_type": self.event.message.message_type, "content": self.event.message.content}}}


def _image_event_payload() -> dict:
    return {
        "event": {
            "message": {
                "message_id": "om_xxx",
                "message_type": "image",
                "content": json.dumps(
                    {
                        "image_key": "img_key_xxx",
                        "file_name": "invoice.png",
                        "mime_type": "image/png",
                        "file_size": 128,
                    }
                ),
            }
        }
    }


def _post_event_payload() -> dict:
    return {
        "event": {
            "message": {
                "message_id": "om_post_xxx",
                "message_type": "post",
                "content": json.dumps(
                    {
                        "content": [
                            [
                                {"tag": "at", "key": "bot", "id": {"open_id": "bot_open_id"}, "name": "bot"},
                                {"tag": "text", "text": " 识别这张发票"},
                            ],
                            [{"tag": "img", "image_key": "img_post_123", "width": 1920, "height": 1080}],
                        ],
                        "title": "",
                    }
                ),
            }
        }
    }


def _post_nested_event_payload() -> dict:
    return {
        "event": {
            "message": {
                "message_id": "om_post_nested_xxx",
                "message_type": "post",
                "content": json.dumps(
                    {
                        "post": {
                            "zh_cn": {
                                "title": "",
                                "content": [
                                    [
                                        {"tag": "text", "text": "识别这张发票"},
                                        {"tag": "img", "image_key": "img_post_nested_123"},
                                    ]
                                ],
                            }
                        }
                    }
                ),
            }
        }
    }


def _file_event_payload() -> dict:
    return {
        "event": {
            "message": {
                "message_id": "om_yyy",
                "message_type": "file",
                "content": json.dumps(
                    {
                        "file_key": "file_key_xxx",
                        "file_name": "receipt.jpg",
                        "mime_type": "image/jpeg",
                        "file_size": 256,
                    }
                ),
            }
        }
    }


def test_p15d_resolve_image_attachment():
    attachments = resolve_feishu_attachments(_image_event_payload())
    assert len(attachments) == 1
    assert attachments[0].attachment_type == "image"
    assert attachments[0].image_key == "img_key_xxx"


def test_p15d_resolve_post_attachment():
    attachments = resolve_feishu_attachments(_post_event_payload())
    assert len(attachments) == 1
    assert attachments[0].attachment_type == "image"
    assert attachments[0].image_key == "img_post_123"


def test_p15d_resolve_nested_post_attachment():
    attachments = resolve_feishu_attachments(_post_nested_event_payload())
    assert len(attachments) == 1
    assert attachments[0].attachment_type == "image"
    assert attachments[0].image_key == "img_post_nested_123"


def test_p15d_resolve_file_attachment():
    attachments = resolve_feishu_attachments(_file_event_payload())
    assert len(attachments) == 1
    assert attachments[0].attachment_type == "file"
    assert attachments[0].file_key == "file_key_xxx"


def test_p15d_post_message_parser_extracts_text_and_attachment():
    event = _DummyEvent(
        _DummyMessage(
            "post",
            json.dumps(
                {
                    "content": [
                        [
                            {"tag": "at", "key": "bot", "id": {"open_id": "bot_open_id"}, "name": "bot"},
                            {"tag": "text", "text": " 识别这张发票"},
                        ],
                        [
                            {"tag": "img", "image_key": "img_post_123", "width": 1920, "height": 1080}
                        ],
                    ],
                    "title": "",
                }
            ),
        )
    )
    parsed = parse_p2_im_message_receive_v1(event)
    assert parsed is not None
    assert parsed.raw_payload["message_type"] == "post"
    assert parsed.raw_payload["content_raw_type"] == "str"
    assert parsed.raw_payload["content"]["content"][1][0]["image_key"] == "img_post_123"
    assert parsed.text == "识别这张发票"


def test_p15d_image_message_parser_defaults_private_to_ocr_command():
    event = _DummyEvent(
        _DummyMessage(
            "image",
            json.dumps({"image_key": "img_private_1", "file_name": "invoice.png", "mime_type": "image/png", "file_size": 128}),
            chat_type="private",
        )
    )
    parsed = parse_p2_im_message_receive_v1(event)
    assert parsed is not None
    assert parsed.raw_payload["message_type"] == "image"
    assert parsed.raw_payload["content"]["image_key"] == "img_private_1"
    assert parsed.text == "识别这张发票"


def test_p15d_image_message_group_without_mention_is_skipped(monkeypatch):
    monkeypatch.setattr(settings, "FEISHU_BOT_OPEN_ID", "bot_open_id")
    message = _DummyMessage(
        "image",
        json.dumps({"image_key": "img_group_1", "file_name": "invoice.png", "mime_type": "image/png", "file_size": 128}),
        chat_type="group",
    )
    message.mentions = []
    event = _DummyEvent(message)
    assert parse_p2_im_message_receive_v1(event) is None


def test_p15d_file_message_parser_keeps_attachment_fields():
    event = _DummyEvent(
        _DummyMessage(
            "file",
            json.dumps({"file_key": "file_x", "file_name": "receipt.jpg", "mime_type": "image/jpeg", "file_size": 256}),
            chat_type="private",
        )
    )
    parsed = parse_p2_im_message_receive_v1(event)
    assert parsed is not None
    assert parsed.raw_payload["message_type"] == "file"
    assert parsed.raw_payload["content"]["file_key"] == "file_x"
    assert parsed.raw_payload["content"]["file_name"] == "receipt.jpg"
    assert parsed.raw_payload["content"]["mime_type"] == "image/jpeg"
    assert parsed.raw_payload["content"]["file_size"] == 256


def test_p15d_download_success_and_build_ocr_input(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "FEISHU_FILE_EVIDENCE_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "FEISHU_FILE_MAX_SIZE_MB", 10)
    attachments = resolve_feishu_attachments(_image_event_payload())
    downloaded = download_feishu_file(
        attachments[0],
        task_id="TASK-P15D-1",
        downloader=lambda message_id, file_key, attachment_type: b"fakepngcontent",
    )
    ocr_input = build_ocr_input_from_downloaded_file(downloaded, requested_by="ou_xxx", hint_document_type="invoice")
    assert downloaded.file_hash
    assert downloaded.file_path
    assert isinstance(ocr_input, OCRDocumentInput)
    assert ocr_input.file_path == downloaded.file_path
    assert ocr_input.source == "feishu"


def test_p15d_missing_attachment_friendly(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_OCR_DOCUMENT_RECOGNIZE", True)
    monkeypatch.setattr(settings, "OCR_DOCUMENT_PROVIDER", "mock")
    monkeypatch.setattr(settings, "ENABLE_FEISHU_FILE_DOWNLOAD", True)
    logs = []
    monkeypatch.setattr("app.graph.nodes.execute_action.log_step", lambda *args: logs.append(args))
    state = execute_action(
        {
            "task_id": "TASK-P15D-MISSING",
            "intent_code": "document.ocr_recognize",
            "slots": {"hint_document_type": "invoice"},
            "source_message_payload": {},
        }
    )
    assert state["status"] == "failed"
    assert "我还没有收到可识别的图片或文件" in state["result_summary"]
    assert "feishu_attachment_missing" in [item[1] for item in logs]


def test_p15d_unsupported_type_friendly(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_OCR_DOCUMENT_RECOGNIZE", True)
    monkeypatch.setattr(settings, "OCR_DOCUMENT_PROVIDER", "mock")
    monkeypatch.setattr(settings, "ENABLE_FEISHU_FILE_DOWNLOAD", True)
    monkeypatch.setattr(settings, "FEISHU_FILE_ALLOWED_MIME_TYPES", "image/png,image/jpeg,application/pdf")
    logs = []
    monkeypatch.setattr("app.graph.nodes.execute_action.log_step", lambda *args: logs.append(args))
    payload = _file_event_payload()
    payload["event"]["message"]["content"] = json.dumps(
        {"file_key": "f1", "file_name": "a.zip", "mime_type": "application/zip", "file_size": 12}
    )
    state = execute_action(
        {
            "task_id": "TASK-P15D-UNSUPPORTED",
            "intent_code": "document.ocr_recognize",
            "slots": {"hint_document_type": "invoice"},
            "source_message_payload": payload,
        }
    )
    assert state["status"] == "failed"
    assert "当前只支持图片文件" in state["result_summary"]
    assert "feishu_file_unsupported_type" in [item[1] for item in logs]


def test_p15d_too_large_friendly(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_OCR_DOCUMENT_RECOGNIZE", True)
    monkeypatch.setattr(settings, "OCR_DOCUMENT_PROVIDER", "mock")
    monkeypatch.setattr(settings, "ENABLE_FEISHU_FILE_DOWNLOAD", True)
    monkeypatch.setattr(settings, "FEISHU_FILE_ALLOWED_MIME_TYPES", "image/png,image/jpeg")
    monkeypatch.setattr(settings, "FEISHU_FILE_MAX_SIZE_MB", 1)
    logs = []
    monkeypatch.setattr("app.graph.nodes.execute_action.log_step", lambda *args: logs.append(args))
    payload = _image_event_payload()
    payload["event"]["message"]["content"] = json.dumps(
        {"image_key": "img", "file_name": "invoice.png", "mime_type": "image/png", "file_size": 2 * 1024 * 1024}
    )
    state = execute_action(
        {
            "task_id": "TASK-P15D-TOO-LARGE",
            "intent_code": "document.ocr_recognize",
            "slots": {"hint_document_type": "invoice"},
            "source_message_payload": payload,
        }
    )
    assert state["status"] == "failed"
    assert "文件超过当前识别大小限制" in state["result_summary"]
    assert "feishu_file_too_large" in [item[1] for item in logs]


def test_p15d_ocr_recognize_uses_downloaded_file_path(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "ENABLE_OCR_DOCUMENT_RECOGNIZE", True)
    monkeypatch.setattr(settings, "OCR_DOCUMENT_PROVIDER", "mock")
    monkeypatch.setattr(settings, "ENABLE_FEISHU_FILE_DOWNLOAD", True)
    monkeypatch.setattr(settings, "FEISHU_FILE_ALLOWED_MIME_TYPES", "image/png,image/jpeg")
    monkeypatch.setattr(settings, "FEISHU_FILE_EVIDENCE_DIR", str(tmp_path))
    logs = []
    monkeypatch.setattr("app.graph.nodes.execute_action.log_step", lambda *args: logs.append(args))
    monkeypatch.setattr(
        "app.services.feishu.client.feishu_client.download_message_resource",
        lambda message_id, file_key, attachment_type: b"p15d_image_data",
    )
    state = execute_action(
        {
            "task_id": "TASK-P15D-OCR",
            "intent_code": "document.ocr_recognize",
            "slots": {"hint_document_type": "invoice"},
            "source_message_payload": _image_event_payload(),
        }
    )
    assert state["status"] == "succeeded"
    assert state["parsed_result"]["attachment_downloaded"] is True
    assert state["parsed_result"]["evidence_relative_path"]
    assert "token" not in json.dumps(state["parsed_result"], ensure_ascii=False).lower()
    codes = [item[1] for item in logs]
    assert "feishu_file_download_started" in codes
    assert "feishu_file_download_succeeded" in codes


def test_p15d_structured_extract_uses_downloaded_file_path(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "ENABLE_OCR_DOCUMENT_RECOGNIZE", True)
    monkeypatch.setattr(settings, "OCR_DOCUMENT_PROVIDER", "mock")
    monkeypatch.setattr(settings, "ENABLE_DOCUMENT_STRUCTURED_EXTRACTION", True)
    monkeypatch.setattr(settings, "DOCUMENT_EXTRACTION_PROVIDER", "rule")
    monkeypatch.setattr(settings, "ENABLE_FEISHU_FILE_DOWNLOAD", True)
    monkeypatch.setattr(settings, "FEISHU_FILE_ALLOWED_MIME_TYPES", "image/png,image/jpeg")
    monkeypatch.setattr(settings, "FEISHU_FILE_EVIDENCE_DIR", str(tmp_path))
    monkeypatch.setattr(
        "app.services.feishu.client.feishu_client.download_message_resource",
        lambda message_id, file_key, attachment_type: b"p15d_image_data",
    )
    state = execute_action(
        {
            "task_id": "TASK-P15D-STRUCTURED",
            "intent_code": "document.structured_extract",
            "slots": {"hint_document_type": "invoice"},
            "source_message_payload": _image_event_payload(),
        }
    )
    assert state["status"] == "succeeded"
    assert state["action_executed_detail"]["attachment_downloaded"] is True
    assert state["action_executed_detail"]["evidence_relative_path"]
    assert state["parsed_result"]["attachment_downloaded"] is True
    assert state["parsed_result"]["formal_write"] is False
    assert state["capability"] == "document.structured_extract"
