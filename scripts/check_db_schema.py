#!/usr/bin/env python3
"""Minimal DB schema drift checker for key task tables/columns."""
from __future__ import annotations

from pathlib import Path
import sys

from sqlalchemy import inspect

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.session import engine


def main() -> int:
    inspector = inspect(engine)
    failures: list[str] = []

    tables = set(inspector.get_table_names())
    if "task_records" not in tables:
        failures.append("missing table: task_records")
    if "task_steps" not in tables:
        failures.append("missing table: task_steps")

    if "task_records" in tables:
        cols = {c["name"] for c in inspector.get_columns("task_records")}
        if "target_task_id" not in cols:
            failures.append("missing column: task_records.target_task_id")

    if failures:
        print("[check_db_schema] FAILED")
        for item in failures:
            print(f" - {item}")
        return 1

    print("[check_db_schema] OK")
    print(" - task_records.target_task_id exists")
    print(" - task_steps table exists")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
