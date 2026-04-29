from dataclasses import dataclass
from typing import Optional
import json
import re

import lark_oapi as lark

from app.core.logging import logger
from app.core.config import settings


def _mention_event_to_dict(mention: object) -> dict:
    """Serialize im.message.receive_v1 的 mention_event（与发消息 API 的 Mention 不同，无 mentioned_type/bot_info）。"""
    if mention is None:
        return {}
    if isinstance(mention, dict):
        return {
            "key": mention.get("key"),
            "id": mention.get("id"),
            "name": mention.get("name"),
            "tenant_key": mention.get("tenant_key"),
        }
    mid = getattr(mention, "id", None)
    id_part: dict | None = None
    if mid is not None:
        id_part = {
            "open_id": getattr(mid, "open_id", None),
            "union_id": getattr(mid, "union_id", None),
            "user_id": getattr(mid, "user_id", None),
        }
    return {
        "key": getattr(mention, "key", None),
        "id": id_part,
        "name": getattr(mention, "name", None),
        "tenant_key": getattr(mention, "tenant_key", None),
    }


def _mention_open_id(mention: object) -> str:
    if mention is None:
        return ""
    if isinstance(mention, dict):
        uid = mention.get("id")
        if isinstance(uid, dict):
            return str(uid.get("open_id") or "").strip()
        return ""
    mid = getattr(mention, "id", None)
    if mid is None:
        return ""
    return str(getattr(mid, "open_id", None) or "").strip()


@dataclass
class FeishuMessageEvent:
    message_id: str
    chat_id: str
    open_id: str
    text: str
    create_time: str
    raw_payload: dict


@dataclass
class _ParsedMessage:
    text: str = ""
    image_key: str = ""
    file_key: str = ""
    file_name: str = ""
    mime_type: str = ""
    file_size: int = 0
    mentions: list[dict] | None = None
    has_mention_bot: bool = False


def _safe_json_loads(content_raw: object) -> dict:
    if isinstance(content_raw, dict):
        return content_raw
    if not isinstance(content_raw, str):
        return {}
    try:
        parsed = json.loads(content_raw)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def build_payload_safe_summary(payload: dict) -> dict:
    content = payload.get("content") if isinstance(payload, dict) else {}
    summary = {
        "message_type": str(payload.get("message_type") or "") if isinstance(payload, dict) else "",
        "content_raw_type": type(content).__name__ if content is not None else "none",
        "content_keys": list(content.keys()) if isinstance(content, dict) else [],
        "has_image_key": False,
        "has_file_key": False,
        "image_key_paths": [],
        "file_key_paths": [],
        "text_preview": str(payload.get("text") or "")[:50] if isinstance(payload, dict) else "",
    }
    def walk(obj, path="$"):
        if isinstance(obj, dict):
            for k, v in obj.items():
                p = f"{path}.{k}"
                if k == "image_key" and isinstance(v, str) and v:
                    summary["has_image_key"] = True
                    summary["image_key_paths"].append(p)
                if k == "file_key" and isinstance(v, str) and v:
                    summary["has_file_key"] = True
                    summary["file_key_paths"].append(p)
                walk(v, p)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                walk(v, f"{path}[{i}]")
    walk(content)
    return summary


def _extract_post_fields(content_obj: dict) -> _ParsedMessage:
    parsed = _ParsedMessage(mentions=[])
    parts: list[str] = []
    content = content_obj.get("content")
    if not isinstance(content, list):
        return parsed
    for row in content:
        if not isinstance(row, list):
            continue
        for item in row:
            if not isinstance(item, dict):
                continue
            tag = str(item.get("tag") or "").strip().lower()
            if tag == "text":
                parts.append(str(item.get("text") or ""))
            elif tag == "at":
                mention = _mention_event_to_dict(item)
                parsed.mentions.append(mention)
                if _mention_open_id(mention):
                    parsed.has_mention_bot = True
            elif tag == "img" and not parsed.image_key:
                parsed.image_key = str(item.get("image_key") or "")
            elif tag == "file" and not parsed.file_key:
                parsed.file_key = str(item.get("file_key") or "")
                parsed.file_name = str(item.get("file_name") or "")
                parsed.mime_type = str(item.get("mime_type") or "")
                try:
                    parsed.file_size = int(item.get("file_size") or item.get("size") or 0)
                except Exception:
                    parsed.file_size = 0
    parsed.text = "".join(parts).strip()
    return parsed


def parse_p2_im_message_receive_v1(event: lark.im.v1.P2ImMessageReceiveV1) -> Optional[FeishuMessageEvent]:
    try:
        event_obj = event.event
        if not event_obj:
            logger.warning("Event object is None")
            return None

        msg = event_obj.message
        if not msg:
            logger.warning("Message is None")
            return None

        message_type = str(getattr(msg, "message_type", "") or "").strip().lower()
        message_id = str(getattr(msg, "message_id", "") or "")
        chat_id = str(getattr(msg, "chat_id", "") or "")
        chat_type = str(getattr(msg, "chat_type", "") or "")
        create_time = str(getattr(msg, "create_time", "") or "")

        sender = getattr(event_obj, "sender", None)
        open_id = ""
        if sender:
            sender_id = getattr(sender, "sender_id", None)
            if sender_id:
                open_id = str(getattr(sender_id, "open_id", "") or getattr(sender_id, "user_id", "") or "")

        content_raw = getattr(msg, "content", "") or ""
        content_obj = _safe_json_loads(content_raw)
        parsed = _ParsedMessage()
        if message_type == "text":
            parsed.text = str(content_obj.get("text") or content_raw or "").strip()
        elif message_type == "post":
            parsed = _extract_post_fields(content_obj)
        elif message_type == "image":
            parsed.image_key = str(content_obj.get("image_key") or "").strip()
            parsed.file_name = str(content_obj.get("file_name") or "feishu_image.png").strip()
            parsed.mime_type = str(content_obj.get("mime_type") or "image/png").strip()
            try:
                parsed.file_size = int(content_obj.get("file_size") or content_obj.get("size") or 0)
            except Exception:
                parsed.file_size = 0
        elif message_type == "file":
            parsed.file_key = str(content_obj.get("file_key") or "").strip()
            parsed.file_name = str(content_obj.get("file_name") or "feishu_file").strip()
            parsed.mime_type = str(content_obj.get("mime_type") or "application/octet-stream").strip()
            try:
                parsed.file_size = int(content_obj.get("file_size") or content_obj.get("size") or 0)
            except Exception:
                parsed.file_size = 0
        else:
            logger.info("Skipping unsupported message_type=%s, message_id=%s", message_type, message_id)
            return None

        if chat_type == "group":
            mentions = getattr(msg, "mentions", None) or []
            if not mentions and parsed.mentions:
                mentions = parsed.mentions
            bot_open_expected = (settings.FEISHU_BOT_OPEN_ID or "").strip()
            if bot_open_expected:
                bot_mentioned = any(_mention_open_id(m) == bot_open_expected for m in mentions)
            else:
                bot_mentioned = len(mentions) > 0
            if not bot_mentioned:
                if bot_open_expected:
                    logger.info("Skip group message: no mention with id.open_id=%s message_id=%s", bot_open_expected, message_id)
                else:
                    logger.info("Skip group message: no mention found message_id=%s", message_id)
                return None
            parsed.has_mention_bot = parsed.has_mention_bot or bot_mentioned
            if not parsed.text:
                parsed.text = re.sub(r"^@_user_\d+\s*", "", str(content_obj.get("text") or "")).strip()

        if message_type == "image":
            if chat_type != "private" and not parsed.has_mention_bot:
                logger.info("Skip image message without bot mention in group: message_id=%s", message_id)
                return None
            if not parsed.text:
                parsed.text = "识别这张发票"
        elif message_type == "file":
            if chat_type != "private" and not parsed.has_mention_bot:
                logger.info("Skip file message without bot mention in group: message_id=%s", message_id)
                return None
            if not parsed.text:
                parsed.text = "识别这个文件"
        elif message_type == "post":
            if not parsed.text:
                logger.info("Skipping empty post message: message_id=%s, chat_id=%s", message_id, chat_id)
                return None
            if parsed.image_key and chat_type != "private" and not parsed.has_mention_bot:
                logger.info("Skip post message without bot mention in group: message_id=%s", message_id)
                return None

        text = re.sub(r"^@_user_\d+\s*", "", parsed.text).strip()
        if not text:
            logger.info("Skipping empty text message: message_id=%s, chat_id=%s", message_id, chat_id)
            return None

        source_payload = {
            "message_id": message_id,
            "message_type": message_type,
            "chat_id": chat_id,
            "open_id": open_id,
            "content": content_obj if isinstance(content_obj, dict) else {},
            "content_raw_type": "dict" if isinstance(content_raw, dict) else "str" if isinstance(content_raw, str) else "none",
            "text": text,
        }
        if parsed.image_key:
            source_payload["image_key"] = parsed.image_key
        if parsed.file_key:
            source_payload["file_key"] = parsed.file_key
        if parsed.file_name:
            source_payload["file_name"] = parsed.file_name
        if parsed.mime_type:
            source_payload["mime_type"] = parsed.mime_type
        if parsed.file_size:
            source_payload["file_size"] = parsed.file_size

        logger.info(
            "PARSER SUCCESS: message_id=%s, chat_id=%s, chat_type=%s, message_type=%s, open_id=%s, text=%s, image_key=%s, file_key=%s, mentions=%s, create_time=%s",
            message_id,
            chat_id,
            chat_type,
            message_type,
            open_id,
            text[:50],
            bool(parsed.image_key),
            bool(parsed.file_key),
            len(parsed.mentions or []),
            create_time,
        )

        logger.info(
            "PARSER PAYLOAD SUMMARY === %s",
            build_payload_safe_summary(source_payload),
        )

        return FeishuMessageEvent(
            message_id=message_id,
            chat_id=chat_id,
            open_id=open_id,
            text=text,
            create_time=create_time,
            raw_payload=source_payload,
        )

    except Exception as e:
        logger.error("Failed to parse message event: %s", str(e), exc_info=True)
        return None
