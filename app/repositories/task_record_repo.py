from typing import Optional
from sqlalchemy.orm import Session

from app.db.models import TaskRecord
from app.core.constants import TaskStatus


class TaskRecordRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_task_id(self, task_id: str) -> Optional[TaskRecord]:
        return self.db.query(TaskRecord).filter(TaskRecord.task_id == task_id).first()

    def get_by_message_id(self, message_id: str) -> Optional[TaskRecord]:
        return self.db.query(TaskRecord).filter(TaskRecord.source_message_id == message_id).first()

    def create(self, task_record: TaskRecord) -> TaskRecord:
        self.db.add(task_record)
        self.db.commit()
        self.db.refresh(task_record)
        return task_record

    def update_status(self, task_id: str, status: TaskStatus) -> Optional[TaskRecord]:
        record = self.get_by_task_id(task_id)
        if record:
            record.status = status.value
            self.db.commit()
            self.db.refresh(record)
        return record

    def update_result(self, task_id: str, result_summary: str) -> Optional[TaskRecord]:
        record = self.get_by_task_id(task_id)
        if record:
            record.result_summary = result_summary
            self.db.commit()
            self.db.refresh(record)
        return record