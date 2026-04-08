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
      PostgreSQL + Milvus + Artifacts# feishu-rpa-commerce-agent
