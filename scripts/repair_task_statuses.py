#!/usr/bin/env python3
"""Manual repair for historical dirty task statuses.

Default mode is dry-run. Use --apply to persist changes.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import sys

from sqlalchemy import and_

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.time import get_shanghai_now
from app.db.models import TaskRecord
from app.db.session import SessionLocal


SUCCESS_HINTS = ("确认执行成功", "价格修改成功", "执行结果：success")
CONFIRM_INTENT_PATTERN = re.compile(r"确认执行\s*(TASK-\d{8}-[A-Z0-9]+)", re.IGNORECASE)


@dataclass
class RepairStat:
    candidates: int = 0
    updated: int = 0


def _extract_target_task_id(task: TaskRecord) -> str | None:
    """Resolve parent task id from target_task_id or confirmation text."""
    if task.target_task_id:
        return task.target_task_id

    intent_text = task.intent_text or ""
    summary = task.result_summary or ""

    match = CONFIRM_INTENT_PATTERN.search(intent_text)
    if match:
        return match.group(1)

    match = CONFIRM_INTENT_PATTERN.search(summary)
    if match:
        return match.group(1)

    return None


def repair_confirmation_tasks(apply: bool) -> RepairStat:
    """Fix confirmation tasks that are semantically successful but still processing."""
    stat = RepairStat()
    db = SessionLocal()
    try:
        processing_tasks = (
            db.query(TaskRecord)
            .filter(
                and_(
                    TaskRecord.status == "processing",
                    TaskRecord.result_summary.isnot(None),
                )
            )
            .all()
        )
        candidate_tasks: list[TaskRecord] = []

        for task in processing_tasks:
            summary = task.result_summary or ""
            parent_task_id = _extract_target_task_id(task)
            if not parent_task_id:
                continue
            if any(marker in summary for marker in SUCCESS_HINTS):
                candidate_tasks.append(task)

        stat.candidates = len(candidate_tasks)
        for task in candidate_tasks:
            parent_task_id = _extract_target_task_id(task)
            if not parent_task_id:
                continue
            if task.status == "succeeded":
                continue
            summary = task.result_summary or ""
            if any(marker in summary for marker in SUCCESS_HINTS):
                task.status = "succeeded"
                task.target_task_id = parent_task_id
                task.finished_at = task.finished_at or get_shanghai_now()
                stat.updated += 1

        if apply:
            db.commit()
        else:
            db.rollback()
    finally:
        db.close()
    return stat


def sync_parent_task_status(apply: bool) -> RepairStat:
    """If confirmation task succeeded, sync parent task from awaiting/processing to succeeded."""
    stat = RepairStat()
    db = SessionLocal()
    try:
        confirmations = (
            db.query(TaskRecord)
            .filter(TaskRecord.status == "succeeded")
            .all()
        )
        candidate_updates: list[tuple[TaskRecord, TaskRecord]] = []
        seen_parent_ids: set[str] = set()

        for confirmation in confirmations:
            parent_task_id = _extract_target_task_id(confirmation)
            if not parent_task_id:
                continue
            if parent_task_id in seen_parent_ids:
                continue
            parent = (
                db.query(TaskRecord)
                .filter(TaskRecord.task_id == parent_task_id)
                .first()
            )
            if not parent:
                continue
            if parent.status not in {"awaiting_confirmation", "processing"}:
                continue

            seen_parent_ids.add(parent_task_id)
            candidate_updates.append((parent, confirmation))

        stat.candidates = len(candidate_updates)
        for parent, confirmation in candidate_updates:
            parent.status = "succeeded"
            parent.error_message = ""
            if not parent.result_summary:
                parent.result_summary = confirmation.result_summary
            parent.finished_at = parent.finished_at or confirmation.finished_at or get_shanghai_now()
            stat.updated += 1

        if apply:
            db.commit()
        else:
            db.rollback()
    finally:
        db.close()
    return stat


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair historical dirty task statuses.")
    parser.add_argument("--apply", action="store_true", help="Persist repair changes.")
    args = parser.parse_args()

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"[repair_task_statuses] mode={mode}")

    s1 = repair_confirmation_tasks(apply=args.apply)
    print(
        f"[rule1] processing confirmation with success summary: candidates={s1.candidates}, "
        f"updated={s1.updated}"
    )

    s2 = sync_parent_task_status(apply=args.apply)
    print(
        f"[rule2] sync parent status by succeeded confirmation: candidates={s2.candidates}, "
        f"updated={s2.updated}"
    )

    print(
        f"[repair_task_statuses] done mode={mode}, total_updated={s1.updated + s2.updated}"
    )


if __name__ == "__main__":
    main()
