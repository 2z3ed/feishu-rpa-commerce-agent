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


def parse_p2_im_message_receive_v1(event: lark.im.v1.P2ImMessageReceiveV1) -> Optional[FeishuMessageEvent]:
    try:
        # ========== 增加调试：打印原始 event 结构 ==========
        event_dict = event.to_dict() if hasattr(event, 'to_dict') else {}
        logger.info("Debug: raw event structure: %s", json.dumps(event_dict, ensure_ascii=False)[:800])
        
        event_obj = event.event
        if not event_obj:
            logger.warning("Event object is None")
            return None

        msg = event_obj.message
        if not msg:
            logger.warning("Message is None")
            return None

        # ========== 检查消息类型 ==========
        message_type = getattr(msg, 'message_type', '') or ""
        if message_type != "text":
            logger.info("Skipping non-text message: message_type=%s, message_id=%s", message_type, getattr(msg, 'message_id', ''))
            return None

        # ========== 提取基础字段 ==========
        message_id = getattr(msg, 'message_id', '') or ""
        chat_id = getattr(msg, 'chat_id', '') or ""
        chat_type = getattr(msg, 'chat_type', '') or ""
        
        # sender_id 是 UserId 对象，需要正确访问 open_id
        sender = event_obj.sender
        open_id = ""
        if sender:
            sender_id = getattr(sender, 'sender_id', None)
            if sender_id:
                # UserId 对象有 open_id, union_id, user_id 属性
                open_id = getattr(sender_id, 'open_id', '') or ""
                if not open_id:
                    open_id = getattr(sender_id, 'user_id', '') or ""
        
        # content 在 msg.content (SDK 已解析好的 content 字段)
        # content 可能是 JSON 字符串 {"text": "xxx"}，需要解析
        content_raw = getattr(msg, 'content', '') or ""
        text = ""
        try:
            # 尝试解析 JSON
            content_obj = json.loads(content_raw)
            text = content_obj.get("text", "") if isinstance(content_obj, dict) else ""
        except:
            # 如果不是 JSON，直接使用
            text = content_raw
        create_time = getattr(msg, 'create_time', '') or ""
        
        # ========== 群聊：仅处理 @ 本应用机器人（im.message.receive_v1 的 mention_event） ==========
        # 官方事件体字段见：https://open.feishu.cn/document/server-docs/im-v1/message/events/receive
        # mentions 元素为 mention_event：key、id(user_id)、name、tenant_key；没有 mentioned_type / bot_info。
        # 判定方式：mentions[].id.open_id 与 FEISHU_BOT_OPEN_ID 一致即为 @ 到当前机器人。
        if chat_type == "group":
            logger.info("Group message detected: message_id=%s, chat_id=%s", message_id, chat_id)

            mentions = getattr(msg, "mentions", None) or []
            mentions_payload = [_mention_event_to_dict(m) for m in mentions]
            logger.info(
                "Group mentions raw (receive_v1 mention_event[]): %s",
                json.dumps(mentions_payload, ensure_ascii=False),
            )

            bot_open_expected = (settings.FEISHU_BOT_OPEN_ID or "").strip()
            if not bot_open_expected:
                logger.warning(
                    "Skip group message: FEISHU_BOT_OPEN_ID is empty, cannot verify @bot. "
                    "message_id=%s",
                    message_id,
                )
                return None

            bot_mentioned = any(_mention_open_id(m) == bot_open_expected for m in mentions)
            if not bot_mentioned:
                logger.info(
                    "Skip group message: no mention with id.open_id=%s message_id=%s",
                    bot_open_expected,
                    message_id,
                )
                return None

            logger.info(
                "Group @bot matched: open_id=%s message_id=%s",
                bot_open_expected,
                message_id,
            )
            text = re.sub(r"^@_user_\d+\s*", "", text).strip()
        
        # ========== 增加调试：打印解析出的关键字段 ==========
        logger.info("Debug: extracted fields - message_id=%s, chat_id=%s, chat_type=%s, open_id=%s, text=%s, create_time=%s",
                    message_id, chat_id, chat_type, open_id, text[:50] if text else "", create_time)

        if not text:
            logger.info("Skipping empty text message: message_id=%s, chat_id=%s", message_id, chat_id)
            return None

        logger.info(
            "PARSER SUCCESS: message_id=%s, chat_id=%s, chat_type=%s, open_id=%s, text=%s, create_time=%s",
            message_id,
            chat_id,
            chat_type,
            open_id,
            text[:50],
            create_time
        )

        return FeishuMessageEvent(
            message_id=message_id,
            chat_id=chat_id,
            open_id=open_id,
            text=text,
            create_time=create_time,
            raw_payload=event.to_dict() if hasattr(event, 'to_dict') else {}
        )

    except Exception as e:
        logger.error("Failed to parse message event: %s", str(e))
        return None