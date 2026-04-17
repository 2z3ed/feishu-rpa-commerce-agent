# Feishu RPA Commerce Agent

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-backend-009688)
![LangGraph](https://img.shields.io/badge/LangGraph-workflow-black)
![RPA](https://img.shields.io/badge/RPA-first-orange)
![RAG](https://img.shields.io/badge/RAG-Milvus-purple)
![License](https://img.shields.io/badge/license-MIT-green)

> A Feishu-driven commerce backoffice agent with RPA-first execution, LangGraph orchestration, RAG memory, and integrations for WooCommerce, Odoo, and Chatwoot.

Feishu RPA Commerce Agent is a backoffice automation system that lets operators trigger real commerce workflows from Feishu using natural language, with LangGraph orchestration, RAG-based rule retrieval, RPA-first execution, API-assisted actions, and full task traceability in Feishu cards and Bitable.

## 中文简介

Feishu RPA Commerce Agent 是一个面向电商后台的智能自动化系统。用户在飞书中通过自然语言下达指令，系统会基于 LangGraph 进行任务编排，结合 RAG 检索规则与历史案例，调用 WooCommerce、Odoo、Chatwoot，并通过 RPA 主执行、API 辅助执行的方式完成真实后台操作，最终将过程与结果回写到飞书消息、飞书卡片和多维表格中。

## 当前阶段状态

- P8 已完成并收口
- `controlled_page` 已人工验证成立
- `real_nonprod_page` 已通过自建 stub 建立
- facts 已入库
- config / bridge / runner 已接通 readiness 路径
- 最小自动化闭环成立
- P83 总演练与阶段收口已完成

## Highlights

- **Feishu-native interaction**: trigger workflows directly from Feishu messages
- **RPA-first execution**: designed for real backoffice actions, not just API demos
- **LangGraph orchestration**: stateful workflow with clear task transitions
- **RAG-enhanced decision layer**: retrieve SOPs, FAQs, rule docs, and historical cases before execution
- **API + RPA hybrid strategy**: support `api`, `rpa`, and `api_then_rpa_verify`
- **Task traceability**: every step is logged, reviewable, and synced to Feishu Bitable
- **Human-in-the-loop for risky actions**: confirmation cards for high-risk operations
- **Multi-platform integration**: WooCommerce, Odoo, Chatwoot

## Scope

This project focuses on **four commerce backoffice roles**:

- Product
- Warehouse
- Customer Service
- Finance

Supported platforms:

- Feishu
- WooCommerce
- Odoo
- Chatwoot

Core architecture:

- FastAPI
- LangGraph
- Milvus
- PostgreSQL
- Celery + Redis
- RPA-first execution layer

## What it can do

### Product
- Query SKU status
- Update product price
- Publish / unpublish products
- Export product list
- Compare WooCommerce and Odoo product data

### Warehouse
- Query pending orders
- Query order status
- Mark orders as processed / shipped
- Fill tracking numbers
- Compare WooCommerce and Odoo inventory

### Customer Service
- Query order status
- List recent conversations
- Summarize a conversation
- Retrieve refund / return rules
- Link conversation with order context

### Finance
- Query daily order summary
- Query sales / refund / cancellation summaries
- Export daily reports
- Reconcile order-side and ERP-side data
- Send report summaries back to Feishu

## Architecture

```text
Feishu Message / Card Action
            │
            ▼
      FastAPI Gateway
            │
            ▼
   Idempotency + Validation
            │
            ▼
      LangGraph Workflow
   ┌────────┼────────┐
   │        │        │
   ▼        ▼        ▼
Intent   RAG       Routing
Parse   Retrieve   Decision
            │
            ▼
   Execution Strategy Layer
   ┌────────┼──────────────┐
   │        │              │
   ▼        ▼              ▼
 API      RPA      API_then_RPA_verify
   │        │              │
   └────────┴──────┬───────┘
                   ▼
       Woo / Odoo / Chatwoot
                   │
                   ▼
     Feishu Message / Card / Bitable
                   │
                   ▼
      PostgreSQL + Milvus + Artifacts

---

# MVP Ingress 快速启动

## 当前模式
本项目当前处于 MVP Ingress 阶段，仅实现飞书长连接消息接收、解析、幂等、入队、回执最小闭环。

## 前置要求

1. Python 3.11+
2. PostgreSQL (本地或远程)
3. Redis (本地或远程)
4. 飞书企业自建应用权限

## 环境配置

1. 复制并配置环境变量:

```bash
cp .env.example .env
```

2. 编辑 `.env` 文件，填写以下关键配置:

```
FEISHU_APP_ID=cli_xxxxx        # 飞书应用 ID
FEISHU_APP_SECRET=xxxxx        # 飞书应用密钥
FEISHU_BOT_NAME=commerce-agent-bot

POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=feishu_rpa
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 启动服务

### 1. 启动 FastAPI 服务

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

服务启动后访问:
- http://localhost:8000/ - 根路径
- http://localhost:8000/api/v1/health - 健康检查

### 2. 启动 Celery Worker

```bash
celery -A app.workers.celery_app worker --loglevel=info
```

### 3. 启动飞书长连接监听器

```bash
python -m app.services.feishu.runner
```

**注意**: 长连接需要能访问公网（连接飞书服务器）。

## 测试流程

1. 在飞书开发者后台配置应用，订阅事件: `im.message.receive_v1`
2. 将应用添加到群聊
3. 在群里 @机器人 发送任意文本消息
4. 预期行为:
   - 机器人回复: "已接收任务，任务号：TASK-20260408-XXXXXX\n当前状态：queued"
   - 日志中显示: message_id, chat_id, open_id, task_id
   - 数据库 task_records 表新增记录，状态从 received -> queued -> processing -> succeeded

## 预留接口 (Webhook 模式)

后续正式环境将切换到 Webhook 模式，预留接口:

- `POST /api/v1/feishu/event` - 飞书事件回调
- `GET /api/v1/feishu/event` - Challenge 验证# feishu-rpa-commerce-agent
