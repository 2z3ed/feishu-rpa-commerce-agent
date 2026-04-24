# feishu-rpa-commerce-agent

一个以飞书为自然语言入口的电商后台智能执行系统。  
当前已经完成单动作演示闭环：飞书发命令、任务创建、高风险确认、real-runtime 执行、任务留痕、多维表记录与结果回飞书，并正在推进更稳定的标准基线固化。

---

## 项目简介

`feishu-rpa-commerce-agent` 不是聊天机器人 Demo，也不是单纯的问答项目。  
它的目标是让用户在飞书里通过自然语言发起后台操作，由系统完成：

- 消息接收与幂等处理
- 任务创建与异步执行
- LangGraph 编排
- mock / confirm / real-runtime 分层执行
- 任务结果回传
- `/tasks` 与 `/steps` 的全过程留痕
- 飞书多维表执行证据追加

项目长期方向是：

**飞书入口 + 任务系统 + 编排层 + 执行层 + 审计留痕**

---

## 当前项目状态

目前仓库已经不是“从零搭骨架”的阶段，而是已经形成了一条真实可演示的主链闭环。

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
- 飞书多维表 `RPA执行证据台账` 追加型写入
- `warehouse.adjust_inventory` 的 real-runtime 执行链
- 飞书前台命令 → 确认 → 执行 → 留痕 → 多维表 的最小演示闭环

### 最近已收口的阶段

近期已完成并收口的阶段包括：

- P9-B：主系统留痕回接（SQLite 验证版）
- P9-C：飞书多维表异步回写接入
- P9-D：飞书多维表配置稳态化
- P9-E：飞书前台演示闭环

### P12-C 增量说明（监控对象管理卡片）

- monitor list 成功时，优先返回飞书管理卡片
- 卡片最多展示前 5 条监控对象
- `active` / `inactive` 对象支持“暂停监控”/“恢复监控”按钮
- 卡片发送失败时，保留文本 fallback 回复
- 超过 5 条对象的分页 / 查看更多能力后移到 P12-D

其中，当前已真实跑通的固定样本为：

- 动作：`warehouse.adjust_inventory`
- SKU：`A001`
- 基线：`100 -> 105`

### 当前正在推进的主线

当前主线不是继续扩功能，而是先把这条已经跑通的单动作闭环进一步做稳。

当前阶段主线为：

**P10-A：SQLite 真相源下稳定性回归与收口固化**

注意：

- 当前不扩第二个业务动作
- 当前不切 PostgreSQL 首验收
- 当前不扩 failure 分支大收口
- 当前仍围绕 `warehouse.adjust_inventory`
- 当前重点是把现有演示闭环做成更稳定、可重复、可交接的标准基线

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
- `warehouse.adjust_inventory`（real-runtime）

### 4. Woo 只读主线

当前已经验证过：

- mock / api-like 两条查询路径
- dry-run / fallback / readiness 口径
- 查询链路的可观测字段
- 任务与步骤留痕可查

### 5. 真实非生产执行链

围绕仓库动作，当前已具备：

- 本地 bridge PoC
- controlled_page 最小执行链
- 更像真实后台的非生产页面执行
- 页面失败语义与证据链
- `outbox / evidence / done` 执行证据
- 单动作治理主线的阶段性收口

### 6. 飞书前台演示闭环

当前已经能支持一条最小前台演示链：

飞书发送命令  
→ 系统返回待确认文本  
→ 飞书确认执行  
→ real-runtime 执行  
→ 飞书返回最终结果文本  
→ `/tasks`、`/steps` 可查  
→ 多维表 `RPA执行证据台账` 有对应记录

---

## 当前项目边界

为了保证主线清晰，当前 README 不把以下内容写成“已完成生产能力”：

- PostgreSQL 已成为首验收环境
- 第二个真实执行动作
- failure 分支完整闭环
- 真实生产写操作接入
- 真实登录自动化
- 全平台生产可用
- 完整多租户交付能力
- 全量 RAG 稳定基线
- 完整飞书卡片交互系统

也就是说，当前仓库更适合被理解为：

**一个已经具备稳定任务主链、真实非生产执行链与飞书前台最小演示闭环，并正在进入稳定性固化阶段的项目。**

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
- 多维表协同能力
- 向真实执行环境逐步推进的结构

### 对业务视角

它适合展示的是：

- 飞书如何作为后台业务入口
- 一个操作如何被拆成任务与步骤
- 高风险动作如何被确认与审计
- 查询 / 确认 / 执行如何被分层处理
- 为什么电商后台智能体不等于“会聊天”
- 为什么一个单动作闭环就足以证明后台自动化路径成立

---

## 技术栈

当前项目主要使用：

- Python
- FastAPI
- LangGraph
- Celery
- Redis
- PostgreSQL / SQLite（当前首验收以 SQLite 为主）
- SQLAlchemy
- Feishu / Lark
- 本地 bridge / real-runtime / Yingdao 执行链路

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