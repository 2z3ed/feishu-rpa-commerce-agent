import json
import uuid

from app.db.session import SessionLocal
from app.db.models import MessageIdempotency, TaskRecord
from app.core.constants import SourcePlatform, TaskStatus
from app.core.logging import logger
from app.core.time import get_shanghai_now
from app.utils.task_logger import log_step


class IdempotencyService:
    def check_and_create(self, message_id: str, raw_payload: dict) -> tuple[bool, str | None, str | None]:
        """
        检查消息是否已存在，如果不存在则创建幂等记录和任务记录
        返回: (is_duplicate, existing_task_id, new_task_id)
        """
        db = SessionLocal()
        try:
            existing = db.query(MessageIdempotency).filter(
                MessageIdempotency.message_id == message_id
            ).first()

            if existing:
                logger.info("=== IDEMPOTENCY HIT === message_id=%s, existing_task_id=%s", message_id, existing.task_id)
                return True, existing.task_id, None

            new_task_id = self._generate_task_id()
            now_ts = get_shanghai_now()
            logger.info("=== IDEMPOTENCY CREATE START === message_id=%s, new_task_id=%s", message_id, new_task_id)

            idempotency = MessageIdempotency(
                source_platform=SourcePlatform.FEISHU.value,
                message_id=message_id,
                chat_id=raw_payload.get("chat_id"),
                sender_open_id=raw_payload.get("open_id"),
                raw_event_type="im.message.receive_v1",
                status="pending",
                task_id=new_task_id,
                raw_payload_json=json.dumps(raw_payload),
                created_at=now_ts,
                updated_at=now_ts,
            )
            db.add(idempotency)

            task_record = TaskRecord(
                task_id=new_task_id,
                source_platform=SourcePlatform.FEISHU.value,
                source_message_id=message_id,
                chat_id=raw_payload.get("chat_id"),
                user_open_id=raw_payload.get("open_id"),
                task_type="ingress",
                intent_text=raw_payload.get("text", ""),
                status=TaskStatus.RECEIVED.value,
                created_at=now_ts,
                updated_at=now_ts,
            )
            db.add(idempotency)

            task_record = TaskRecord(
                task_id=new_task_id,
                source_platform=SourcePlatform.FEISHU.value,
                source_message_id=message_id,
                chat_id=raw_payload.get("chat_id"),
                user_open_id=raw_payload.get("open_id"),
                task_type="ingress",
                intent_text=raw_payload.get("text", ""),
                status=TaskStatus.RECEIVED.value,
                created_at=now_ts,
                updated_at=now_ts,
            )
            db.add(task_record)
            
            logger.info("=== IDEMPOTENCY COMMIT START === message_id=%s, new_task_id=%s", message_id, new_task_id)
            db.commit()
            logger.info("=== IDEMPOTENCY COMMIT SUCCESS === message_id=%s, new_task_id=%s", message_id, new_task_id)
            
            # Log initial steps
            log_step(new_task_id, "ingress_received", "success", f"message_id={message_id}")
            log_step(new_task_id, "task_enqueued", "success", "")

            logger.info(
                "Created new task record: message_id=%s, task_id=%s",
                message_id,
                new_task_id
            )
            return False, None, new_task_id

        except Exception as e:
            db.rollback()
            logger.error("Failed to create idempotency record: %s, message_id=%s", str(e), message_id)
            raise
        finally:
            db.close()

    def _generate_task_id(self) -> str:
        from app.core.constants import TASK_ID_PREFIX, TASK_ID_DATE_FMT

        date_str = get_shanghai_now().strftime(TASK_ID_DATE_FMT)
        unique_suffix = uuid.uuid4().hex[:6].upper()
        return f"{TASK_ID_PREFIX}{date_str}-{unique_suffix}"


idempotency_service = IdempotencyService()