import threading
import time
import json
import sys
import re

import lark_oapi as lark
from lark_oapi import EventDispatcherHandler, LogLevel

from app.core.config import settings
from app.core.logging import logger
from app.services.feishu.parser import parse_p2_im_message_receive_v1, FeishuMessageEvent
from app.services.feishu.idempotency import idempotency_service
from app.services.feishu.client import feishu_client
from app.tasks.ingress_tasks import process_ingress_message
from app.core.constants import TaskStatus
from app.db.session import SessionLocal
from app.db.models import TaskRecord


class FeishuLongConnListener:
    def __init__(self):
        self._client = None
        self._running = False
        self._thread = None

    def _handle_message_event(self, data: lark.im.v1.P2ImMessageReceiveV1):
        # ===== 绝对入口日志 =====
        print(f"===========================================>", file=sys.stderr)
        print(f">>> ENTER _handle_message_event with data type: {type(data)}", file=sys.stderr)
        print(f"===========================================>", file=sys.stderr)
        
        try:
            # ========== 强制可见调试：收到任意飞书事件 ==========
            logger.info("=== _handle_message_event CALLED === data_type=%s", type(data))
            
            raw_dict = data.to_dict() if hasattr(data, 'to_dict') else {}
            logger.info("=== FEISHU EVENT RECEIVED === event_type=im.message.receive_v1, raw_payload=%s", 
                        json.dumps(raw_dict, ensure_ascii=False)[:500])

            # ========== 解析消息 ==========
            message_event = parse_p2_im_message_receive_v1(data)
            
            # ========== 调试：打印 parser 结果 ==========
            if not message_event:
                logger.warning("=== PARSER RETURNED NONE === message event is None, skipping")
                return

            # ========== 明确打印 message_id 追踪 ==========
            logger.info("=== PARSER SUCCESS === message_id=%s, chat_id=%s, open_id=%s, text=%s",
                        message_event.message_id, message_event.chat_id, 
                        message_event.open_id, message_event.text[:50] if message_event.text else "")

            payload = {
                "message_id": message_event.message_id,
                "chat_id": message_event.chat_id,
                "open_id": message_event.open_id,
                "text": message_event.text,
                "create_time": message_event.create_time,
            }

            # ========== 幂等检查 ==========
            is_duplicate, existing_task_id, new_task_id = idempotency_service.check_and_create(
                message_id=message_event.message_id,
                raw_payload=payload
            )

            # ========== 幂等命中日志 ==========
            if is_duplicate and existing_task_id:
                logger.info(
                    "Idempotency hit - message already processed: message_id=%s, existing_task_id=%s",
                    message_event.message_id,
                    existing_task_id
                )
                response_text = f"已接收任务，任务号：{existing_task_id}\n当前状态：duplicate (任务已存在)"
                feishu_client.send_text_reply(message_id=message_event.message_id, text=response_text)
                return

            if not new_task_id:
                logger.error("=== TASK_ID CREATE FAILED === message_id=%s", message_event.message_id)
                return

            # ========== 数据库写入成功日志 ==========
            logger.info(
                "=== DATABASE WRITE SUCCESS === message_id=%s, task_id=%s",
                message_event.message_id,
                new_task_id
            )

            # ========== Celery 入队 ==========
            logger.info("=== CELERY ENQUEUE START === task_id=%s", new_task_id)
            task = process_ingress_message.delay(
                new_task_id, 
                message_event.text, 
                message_event.open_id,
                message_event.message_id,
                message_event.chat_id
            )

            # ========== 更新任务状态为 queued ==========
            db = SessionLocal()
            try:
                task_record = db.query(TaskRecord).filter(TaskRecord.task_id == new_task_id).first()
                if task_record:
                    task_record.status = TaskStatus.QUEUED.value
                    db.commit()
            finally:
                db.close()

            # ========== Celery 入队成功日志 ==========
            logger.info(
                "=== CELERY ENQUEUE SUCCESS === task_id=%s, celery_task_id=%s",
                new_task_id,
                task.id
            )

            # ========== 飞书回执 ==========
            logger.info("=== FEISHU REPLY START === message_id=%s, task_id=%s", message_event.message_id, new_task_id)
            is_confirm_cmd = bool(re.search(r"(?:确认执行|确认|执行)\s*TASK-[A-Z0-9][A-Z0-9-]{6,}", message_event.text, re.IGNORECASE))
            if is_confirm_cmd:
                response_text = f"已接收确认请求，任务号：{new_task_id}\n当前状态：执行中"
            else:
                response_text = f"已接收任务，任务号：{new_task_id}\n当前状态：queued"
            reply_success = feishu_client.send_text_reply(
                message_id=message_event.message_id, 
                text=response_text
            )

            # ========== 回执发送结果日志 ==========
            if reply_success:
                logger.info(
                    "=== FEISHU REPLY SUCCESS === message_id=%s, task_id=%s",
                    message_event.message_id,
                    new_task_id
                )
            else:
                logger.error(
                    "=== FEISHU REPLY FAILED === message_id=%s, task_id=%s",
                    message_event.message_id,
                    new_task_id
                )

            logger.info(
                "Message processed successfully: message_id=%s, task_id=%s, celery_task_id=%s",
                message_event.message_id,
                new_task_id,
                task.id
            )

        except Exception as e:
            logger.error("Error handling message event: %s", str(e), exc_info=True)

    def start(self):
        if self._running:
            logger.warning("Long connection listener already running")
            return

        logger.info("Starting Feishu long connection listener... app_id=%s", settings.FEISHU_APP_ID[:10]+"...")

        event_handler = (
            EventDispatcherHandler.builder("", "")
            .register_p2_im_message_receive_v1(self._handle_message_event)
            .build()
        )

        self._client = lark.ws.Client(
            app_id=settings.FEISHU_APP_ID,
            app_secret=settings.FEISHU_APP_SECRET,
            event_handler=event_handler,
            log_level=LogLevel.DEBUG,
        )

        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        
        # 等待一下确认连接成功
        time.sleep(2)
        logger.info("Feishu long connection listener started, thread running")

    def _run(self):
        try:
            logger.info("WebSocket client starting...")
            self._client.start()
        except Exception as e:
            logger.error("Long connection error: %s", str(e), exc_info=True)
            self._running = False

    def stop(self):
        if not self._running:
            return
        self._running = False
        if self._client:
            logger.info("Stopping Feishu long connection listener")


longconn_listener = FeishuLongConnListener()