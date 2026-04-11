from dataclasses import dataclass
from typing import Optional
import json
import re

import lark_oapi as lark
from lark_oapi import model

from app.core.logging import logger
from app.core.config import settings


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
        
        # ========== 群聊过滤：必须@机器人（双保险判断） ==========
        if chat_type == "group":
            logger.info("Group message detected: message_id=%s, chat_id=%s", message_id, chat_id)
            
            bot_mentioned = False
            
            # 条件 A: 检查 mentions 中是否存在当前机器人
            mentions = getattr(msg, 'mentions', None)
            if mentions:
                for mention in mentions:
                    mentioned_type = None
                    bot_app_id = None
                    
                    # 访问 mentioned_type
                    if hasattr(mention, 'mentioned_type'):
                        mentioned_type = getattr(mention, 'mentioned_type', '')
                    elif isinstance(mention, dict):
                        mentioned_type = mention.get('mentioned_type', '')
                    
                    # 访问 bot_info.app_id
                    if mentioned_type == "bot":
                        bot_info = None
                        if hasattr(mention, 'bot_info'):
                            bot_info = getattr(mention, 'bot_info', None)
                        elif isinstance(mention, dict):
                            bot_info = mention.get('bot_info', {})
                        
                        if bot_info:
                            if hasattr(bot_info, 'app_id'):
                                bot_app_id = getattr(bot_info, 'app_id', '')
                            elif isinstance(bot_info, dict):
                                bot_app_id = bot_info.get('app_id', '')
                            
                            if bot_app_id == settings.FEISHU_APP_ID:
                                bot_mentioned = True
                                logger.info("Bot mentioned detected by mentions: message_id=%s, chat_id=%s", message_id, chat_id)
                                break
            
            # 条件 B: 文本前缀 fallback - 检查是否有@_user_1 等占位符
            if not bot_mentioned and text:
                if re.match(r'^@_user_\d+', text):
                    bot_mentioned = True
                    logger.info("Bot mentioned detected by text prefix fallback: message_id=%s, chat_id=%s", message_id, chat_id)
            
            # 如果两个条件都不满足，直接 skip
            if not bot_mentioned:
                logger.info("Skip group message: bot not mentioned, message_id=%s, chat_id=%s", message_id, chat_id)
                return None
            
            # 清洗群聊文本中的@占位前缀
            text = re.sub(r'^@_user_\d+\s*', '', text).strip()
        
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