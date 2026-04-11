from typing import Optional
from sqlalchemy.orm import Session

from app.db.models import MessageIdempotency


class MessageIdempotencyRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_message_id(self, message_id: str) -> Optional[MessageIdempotency]:
        return self.db.query(MessageIdempotency).filter(
            MessageIdempotency.message_id == message_id
        ).first()

    def create(self, idempotency: MessageIdempotency) -> MessageIdempotency:
        self.db.add(idempotency)
        self.db.commit()
        self.db.refresh(idempotency)
        return idempotency

    def update_task_id(self, message_id: str, task_id: str) -> Optional[MessageIdempotency]:
        record = self.get_by_message_id(message_id)
        if record:
            record.task_id = task_id
            self.db.commit()
            self.db.refresh(record)
        return record