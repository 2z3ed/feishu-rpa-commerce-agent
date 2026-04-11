-- Migration: Add target_task_id column to task_records table
-- PostgreSQL-safe (idempotent) migration.
-- If you are using SQLite locally, do NOT run this file directly.

ALTER TABLE task_records
  ADD COLUMN IF NOT EXISTS target_task_id VARCHAR(64);

CREATE INDEX IF NOT EXISTS idx_task_records_target_task_id
  ON task_records (target_task_id);
