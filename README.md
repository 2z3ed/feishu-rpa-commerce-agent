# feishu-rpa-commerce-agent

一个以飞书为自然语言入口的电商后台智能执行系统。  
当前已完成任务编排主链、查询/确认闭环、Woo 只读主线与任务留痕能力，并正在推进更接近真实后台的非生产执行环境接入。

---

## 项目简介

`feishu-rpa-commerce-agent` 不是聊天机器人 Demo，也不是单纯的问答项目。  
它的目标是让用户在飞书里通过自然语言发起后台操作，由系统完成：

- 消息接收与幂等处理
- 任务创建与异步执行
- LangGraph 编排
- mock / API / confirm / RPA 准备态分层执行
- 任务结果回传
- `/tasks` 与 `/steps` 的全过程留痕

项目长期方向是：

**飞书入口 + 任务系统 + 编排层 + 执行层 + 审计留痕**

---

## 当前项目状态

目前仓库已经不是“从零搭骨架”的阶段，而是已经形成了一条稳定的主链闭环。

### 已完成并验证通过的部分

当前已稳定具备的能力包括：

- 飞书长连接接收消息
- 私聊处理与回复
- 群聊仅在 `@机器人` 时触发
- `message_idempotency` 幂等处理
- `task_records` / `task_steps` 留痕
- Celery 异步执行
- LangGraph 最小状态流
- 任务查询接口：
  - `/api/v1/tasks/`
  - `/api/v1/tasks/{task_id}`
  - `/api/v1/tasks/{task_id}/steps`
- `product.query_sku_status`
- `product.update_price` 的高风险确认 mock 链路
- `system.confirm_task`
- Woo 只读查询主线
- 追加型任务台账 / 审计留痕能力

### 最近已收口的阶段

近期已完成并收口的阶段包括：

- P70：影刀本地 bridge PoC
- P71：受控页面最小执行链
- P72：更像真实后台的受控验证
- P73：单动作治理主线加固
- P93：影刀 real-runtime success 总演练与阶段收口（`warehouse.adjust_inventory`）
  - real-runtime success 演练通过
  - done / outbox / evidence（runtime-result 兜底）已成立
  - 后移项：failure 分支、真实截图增强、incoming latest-file 临时方案回收

### 当前正在推进的主线

当前主线不是“全部完成”，而是继续向更真实的后台执行环境推进。

当前阶段主线为：

**P8：影刀真实非生产页面接入**

注意：

- 这不是生产接入
- 当前不扩第二个业务动作
- 当前仍主要围绕 `warehouse.adjust_inventory`
- 不接影刀控制台 / API Key / Flow
- 不直接放开飞书触发真实生产执行
- 不做大重构

---

## 当前核心能力

### 1. 飞书自然语言入口

支持：

- 飞书消息接收
- 群聊 @ 过滤
- 幂等处理
- 任务入队
- 异步执行
- 结果回飞书

### 2. 任务系统与编排

当前项目已经具备完整的任务承载能力：

- 基于 LangGraph 的最小状态流
- `task_records` / `task_steps` 留痕
- 任务详情、步骤详情可查询
- 高风险动作通过 confirm 链路处理
- 支持后续扩展更真实的执行层

### 3. 查询 / 确认主线

目前已经形成稳定闭环的代表性业务动作：

- `product.query_sku_status`
- `product.update_price`（高风险确认 mock）
- `system.confirm_task`

### 4. Woo 只读主线

当前已经验证过：

- mock / api-like 两条查询路径
- dry-run / fallback / readiness 口径
- 查询链路的可观测字段
- 任务与步骤留痕可查

### 5. 受控页面 / 本地执行桥接

围绕仓库动作，当前已具备：

- 本地 bridge PoC
- controlled_page 最小执行链
- 更像真实后台的受控库存页面
- 页面失败语义与证据链
- 单动作治理主线的阶段性收口

---

## 当前项目边界

为了保证主线清晰，当前 README 不把以下内容写成“已完成生产能力”：

- 真实生产写操作接入
- 真实登录自动化
- 全平台生产可用
- 完整多租户交付能力
- 全量 RAG 稳定基线
- 完整飞书卡片交互系统
- 已完成的真实非生产外部 happy path

也就是说，当前仓库更适合被理解为：

**一个已经具备稳定任务主链与执行分层基础、正在从受控验证推进到更真实非生产环境的项目。**

---

## 项目适合展示什么

如果你是第一次看这个项目，可以这样理解它当前的价值：

### 对工程视角
它已经不只是“能收消息的机器人”，而是具备：

- 任务建模
- 异步执行
- 状态编排
- 高风险确认
- 查询能力
- 留痕能力
- 向真实后台执行层逐步推进的结构

### 对业务视角
它适合展示的是：

- 飞书如何作为后台业务入口
- 一个操作如何被拆成任务与步骤
- 高风险动作如何被确认与审计
- 查询 / 确认 / 执行如何被分层处理
- 为什么电商后台智能体不等于“会聊天”

---

## 技术栈

当前项目主要使用：

- Python
- FastAPI
- LangGraph
- Celery
- Redis
- PostgreSQL / SQLite（开发阶段可切换）
- SQLAlchemy
- Feishu / Lark
- 本地 bridge / controlled page / Yingdao 执行准备链路

---

## 仓库结构

```text
app/        核心服务、API、graph、task、executor、provider 逻辑
docs/       阶段文档、SOP、收口文档、治理文档
lark_oapi/  Feishu / Lark SDK 相关代码
migrations/ 数据库迁移
script/     历史阶段脚本
scripts/    本地开发与验证脚本
tests/      测试与回归验证
tools/      辅助工具
AGENTS.md
LANGGRAPH_IMPLEMENTATION.md
README.md
docker-compose.dev.yml
requirements.txt