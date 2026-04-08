# Feishu RPA Commerce Agent - Code Wiki

## 项目概述

### 项目简介

**Feishu RPA Commerce Agent** 是一个面向电商后台的智能自动化系统。用户在飞书中通过自然语言下达指令，系统会基于 LangGraph 进行任务编排，结合 RAG 检索规则与历史案例，调用 WooCommerce、Odoo、Chatwoot，并通过 RPA 主执行、API 辅助执行的方式完成真实后台操作，最终将过程与结果回写到飞书消息、飞书卡片和多维表格中。

### 项目状态

> ⚠️ **注意**: 当前项目处于规划/设计阶段，仅有设计文档，尚未有代码实现。

### 技术标签

| 技术 | 说明 |
|------|------|
| Python 3.11+ | 主要开发语言 |
| FastAPI | 后端API框架 |
| LangGraph | 工作流编排引擎 |
| Milvus | 向量数据库(RAG) |
| PostgreSQL | 关系型数据库 |
| Celery + Redis | 异步任务队列 |
| RPA | 自动化执行层 |

### 核心特性

1. **Feishu-native interaction**: 直接从飞书消息触发工作流
2. **RPA-first execution**: 专为真实后台操作设计
3. **LangGraph orchestration**: 有状态的工作流，清晰的任务转换
4. **RAG-enhanced decision layer**: 执行前检索SOP、FAQ、规则文档和历史案例
5. **API + RPA hybrid strategy**: 支持 `api`、`rpa`、`api_then_rpa_verify` 三种执行策略
6. **Task traceability**: 每一步都有日志记录，可审查，同步到飞书多维表格
7. **Human-in-the-loop for risky actions**: 高风险操作需要确认卡片
8. **Multi-platform integration**: 集成WooCommerce、Odoo、Chatwoot

---

## 整体架构

### 架构图

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
```

### 架构层次说明

| 层次 | 组件 | 职责 |
|------|------|------|
| 接入层 | FastAPI Gateway | 接收飞书消息/卡片动作，提供HTTP API入口 |
| 验证层 | Idempotency + Validation | 幂等性检查、请求验证 |
| 编排层 | LangGraph Workflow | 状态机工作流编排 |
| 决策层 | Intent Parse / RAG Retrieve / Routing Decision | 意图解析、规则检索、路由决策 |
| 执行层 | Execution Strategy Layer | 执行策略选择与执行 |
| 集成层 | Woo / Odoo / Chatwoot | 外部平台集成 |
| 输出层 | Feishu Message / Card / Bitable | 结果输出到飞书 |
| 存储层 | PostgreSQL + Milvus + Artifacts | 数据持久化与向量检索 |

---

## 主要模块职责

### 1. 接入模块 (Gateway Module)

**职责**: 接收并处理来自飞书的请求

**核心功能**:
- 接收飞书消息事件
- 处理飞书卡片动作回调
- 请求鉴权与验证
- 幂等性控制

**技术栈**: FastAPI

### 2. 编排模块 (Orchestration Module)

**职责**: 基于LangGraph的工作流编排

**核心功能**:
- 状态机管理
- 任务节点编排
- 工作流状态持久化
- 任务转换控制

**技术栈**: LangGraph

### 3. 决策模块 (Decision Module)

**职责**: 智能决策与规则检索

**子模块**:

| 子模块 | 职责 |
|--------|------|
| Intent Parse | 解析用户自然语言意图 |
| RAG Retrieve | 检索SOP、FAQ、规则文档、历史案例 |
| Routing Decision | 决定执行策略和目标平台 |

**技术栈**: LangChain, Milvus, Embedding Models

### 4. 执行模块 (Execution Module)

**职责**: 执行具体的业务操作

**执行策略**:

| 策略 | 说明 | 适用场景 |
|------|------|----------|
| `api` | 纯API调用 | 简单查询、低风险操作 |
| `rpa` | 纯RPA执行 | 无API支持的操作 |
| `api_then_rpa_verify` | API执行后RPA验证 | 需要双重确认的关键操作 |

**技术栈**: RPA Framework, HTTP Client

### 5. 集成模块 (Integration Module)

**职责**: 与外部平台集成

**支持平台**:

| 平台 | 类型 | 集成方式 |
|------|------|----------|
| WooCommerce | 电商平台 | REST API |
| Odoo | ERP系统 | XML-RPC / REST API |
| Chatwoot | 客服系统 | REST API / WebSocket |

### 6. 输出模块 (Output Module)

**职责**: 将结果输出到飞书

**输出形式**:
- 飞书消息 (Message)
- 飞书卡片 (Card)
- 飞书多维表格 (Bitable)

**技术栈**: Feishu Open API

### 7. 存储模块 (Storage Module)

**职责**: 数据持久化与检索

**存储类型**:

| 存储 | 用途 | 技术 |
|------|------|------|
| PostgreSQL | 结构化数据存储 | 关系型数据库 |
| Milvus | 向量检索 | 向量数据库 |
| Artifacts | 文件/日志存储 | 对象存储 |

---

## 业务功能模块

### 产品模块 (Product)

| 功能 | 说明 |
|------|------|
| Query SKU status | 查询SKU状态 |
| Update product price | 更新产品价格 |
| Publish / unpublish products | 上架/下架产品 |
| Export product list | 导出产品列表 |
| Compare WooCommerce and Odoo product data | 对比WooCommerce和Odoo产品数据 |

### 仓库模块 (Warehouse)

| 功能 | 说明 |
|------|------|
| Query pending orders | 查询待处理订单 |
| Query order status | 查询订单状态 |
| Mark orders as processed / shipped | 标记订单为已处理/已发货 |
| Fill tracking numbers | 填写物流单号 |
| Compare WooCommerce and Odoo inventory | 对比WooCommerce和Odoo库存 |

### 客服模块 (Customer Service)

| 功能 | 说明 |
|------|------|
| Query order status | 查询订单状态 |
| List recent conversations | 列出最近对话 |
| Summarize a conversation | 总结对话内容 |
| Retrieve refund / return rules | 获取退款/退货规则 |
| Link conversation with order context | 关联对话与订单上下文 |

### 财务模块 (Finance)

| 功能 | 说明 |
|------|------|
| Query daily order summary | 查询每日订单汇总 |
| Query sales / refund / cancellation summaries | 查询销售/退款/取消汇总 |
| Export daily reports | 导出日报表 |
| Reconcile order-side and ERP-side data | 对账订单侧与ERP侧数据 |
| Send report summaries back to Feishu | 发送报表摘要到飞书 |

---

## 技术栈与依赖

### 核心技术栈

```yaml
语言: Python 3.11+

后端框架:
  - FastAPI: 高性能异步Web框架

工作流编排:
  - LangGraph: 状态机工作流引擎

向量检索:
  - Milvus: 向量数据库
  - Embedding Models: 文本向量化

数据存储:
  - PostgreSQL: 关系型数据库
  - Redis: 缓存与消息队列

异步任务:
  - Celery: 分布式任务队列
  - Redis: 消息代理

RPA执行:
  - RPA Framework: 自动化执行框架

外部集成:
  - WooCommerce REST API
  - Odoo XML-RPC / REST API
  - Chatwoot REST API
  - Feishu Open API
```

### 预期依赖结构

```
feishu-rpa-commerce-agent/
├── requirements.txt          # Python依赖
├── pyproject.toml           # 项目配置
├── Dockerfile               # Docker构建文件
├── docker-compose.yml       # 容器编排配置
└── src/
    ├── api/                 # FastAPI应用
    ├── workflows/           # LangGraph工作流
    ├── agents/              # 智能代理
    ├── rag/                 # RAG检索模块
    ├── execution/           # 执行策略层
    ├── integrations/        # 外部平台集成
    ├── models/              # 数据模型
    ├── utils/               # 工具函数
    └── config/              # 配置管理
```

---

## 部署与运行

### 环境要求

- Python 3.11+
- PostgreSQL 14+
- Milvus 2.x
- Redis 7+
- Docker & Docker Compose (推荐)

### 预期配置项

```yaml
# 飞书配置
FEISHU_APP_ID: 应用ID
FEISHU_APP_SECRET: 应用密钥

# WooCommerce配置
WOOCOMMERCE_URL: 商店URL
WOOCOMMERCE_CONSUMER_KEY: API密钥
WOOCOMMERCE_CONSUMER_SECRET: API密钥

# Odoo配置
ODOO_URL: Odoo服务URL
ODOO_DB: 数据库名
ODOO_USERNAME: 用户名
ODOO_API_KEY: API密钥

# Chatwoot配置
CHATWOOT_API_URL: API地址
CHATWOOT_API_TOKEN: API令牌

# 数据库配置
POSTGRES_URL: PostgreSQL连接串
MILVUS_HOST: Milvus服务地址
REDIS_URL: Redis连接串

# LLM配置
LLM_PROVIDER: LLM提供商
LLM_API_KEY: API密钥
LLM_MODEL: 模型名称
```

### 预期启动方式

```bash
# 使用Docker Compose
docker-compose up -d

# 或本地开发
pip install -r requirements.txt
uvicorn src.api.main:app --reload
celery -A src.celery worker -l info
```

---

## 项目范围

### 四大业务角色

1. **Product (产品)**: 产品管理相关操作
2. **Warehouse (仓库)**: 仓储物流相关操作
3. **Customer Service (客服)**: 客户服务相关操作
4. **Finance (财务)**: 财务报表相关操作

### 支持平台

- Feishu (飞书)
- WooCommerce
- Odoo
- Chatwoot

---

## 开发路线图

### Phase 1: 基础架构
- [ ] FastAPI项目骨架
- [ ] 数据库模型设计
- [ ] 飞书集成基础

### Phase 2: 核心功能
- [ ] LangGraph工作流实现
- [ ] RAG检索模块
- [ ] 执行策略层

### Phase 3: 平台集成
- [ ] WooCommerce集成
- [ ] Odoo集成
- [ ] Chatwoot集成

### Phase 4: 业务功能
- [ ] 产品模块功能
- [ ] 仓库模块功能
- [ ] 客服模块功能
- [ ] 财务模块功能

### Phase 5: 完善与优化
- [ ] 任务追溯系统
- [ ] 人工确认机制
- [ ] 性能优化

---

## 许可证

MIT License

---

*文档生成时间: 2026-04-08*
*项目状态: 规划阶段*
