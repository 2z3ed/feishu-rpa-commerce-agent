-- 初始化数据库脚本
-- 创建数据库 (如果不存在)
-- CREATE DATABASE feishu_rpa;

-- 建表脚本
-- 运行: psql -U postgres -d feishu_rpa -f init_tables.sql

-- 消息幂等表
CREATE TABLE IF NOT EXISTS message_idempotency (
    id SERIAL PRIMARY KEY,
    source_platform VARCHAR(32) NOT NULL,
    message_id VARCHAR(128) NOT NULL UNIQUE,
    idempotency_key VARCHAR(256),
    chat_id VARCHAR(128),
    sender_open_id VARCHAR(128),
    raw_event_type VARCHAR(64),
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    task_id VARCHAR(64),
    raw_payload_json TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_message_idempotency_message_id ON message_idempotency(message_id);
CREATE INDEX idx_message_idempotency_task_id ON message_idempotency(task_id);
CREATE INDEX idx_message_idempotency_chat_id ON message_idempotency(chat_id);
CREATE INDEX idx_message_idempotency_sender_open_id ON message_idempotency(sender_open_id);

-- 任务记录表
CREATE TABLE IF NOT EXISTS task_records (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(64) NOT NULL UNIQUE,
    source_platform VARCHAR(32) NOT NULL,
    source_message_id VARCHAR(128),
    chat_id VARCHAR(128),
    user_open_id VARCHAR(128),
    task_type VARCHAR(64),
    intent_text TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'received',
    result_summary TEXT,
    error_message TEXT,
    accepted_at TIMESTAMP,
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_task_records_task_id ON task_records(task_id);
CREATE INDEX idx_task_records_source_message_id ON task_records(source_message_id);
CREATE INDEX idx_task_records_chat_id ON task_records(chat_id);
CREATE INDEX idx_task_records_user_open_id ON task_records(user_open_id);
CREATE INDEX idx_task_records_status ON task_records(status);