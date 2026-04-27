# AGENTS.md

> 本文件是本仓库对编码智能体（如 Codex / Cursor / OpenCode）的强约束执行规范。
> 当前仓库不是“大而全平台”开发阶段，而是“最小闭环收口阶段”。
> 除非用户明确要求修改，否则不得擅自扩展业务范围、改写主线、替换核心叙事。

---

# 0. 当前阶段唯一目标

本仓库当前唯一目标不是继续铺大平台，不是继续扩四岗位，不是继续加第二第三平台。

当前阶段唯一目标是：

> 做出一个“飞书入口 + 任务留痕 + 高风险确认 + 执行层 + 结果回写”的最小可演示闭环，
> 让项目能面试讲清楚、能本地演示、能通过 coding agent 稳定推进。

这是一个“业务闭环优先”的阶段，不是“平台能力铺满”的阶段。

---

# 1. 当前项目定位

## 1.1 项目名称
Feishu RPA Commerce Agent

## 1.2 当前阶段项目本质
这是一个面向电商后台自动化的 AI 应用 / Agent 落地项目。

但在当前阶段，它不是完整平台，不追求覆盖全部后台岗位；
它首先要证明一件事：

- 飞书可以作为业务入口
- 自然语言可以进入任务系统
- 高风险动作不能直接执行，必须先确认
- 执行层可以调用 mock / API / RPA
- 结果可以回写并留痕
- 整条链路可观测、可复盘、可演示

## 1.3 当前阶段对外主叙事
当前阶段对外主叙事固定为：

> 用户在飞书发起一个高风险后台动作，
> 系统将自然语言转成任务，
> 进入任务状态机，
> 通过飞书确认卡片做人机确认，
> 确认后进入执行层，
> 最终将结果回写到飞书和任务系统中。

不要把当前阶段叙事改写成：
- 四岗位全覆盖平台
- 多平台统一运营中台
- 多智能体实验项目
- 泛化型 Agent 框架

---

# 2. 当前阶段唯一主线

## 2.1 主故事冻结
当前阶段唯一主故事冻结为：

- `product.update_price`
- `system.confirm_task`

也就是：

1. 用户在飞书发起改价请求
2. 系统识别为高风险动作
3. 原任务进入 `awaiting_confirmation`
4. 系统发送飞书确认卡片
5. 用户点击确认 / 拒绝
6. 系统触发 `system.confirm_task` 或拒绝分支
7. 执行层返回结果
8. `/tasks` 与 `/steps` 可查
9. 飞书消息 / 卡片显示最终状态
10. 如已有稳定基础，可选写入 Bitable 台账

## 2.2 当前阶段次要执行验证分支
允许存在一个“执行层验证分支”：

- `warehouse.adjust_inventory`

它的角色是：
- 验证 Yingdao / bridge / real_nonprod_page / mock executor / 真点击链路
- 证明“执行层可以接 RPA”

但它不是当前阶段对外主故事，
不得抢占 `product.update_price + confirm card` 这条主线。

---

# 3. 当前阶段 In Scope（必须实现）

当前阶段只要求实现以下能力，不得擅自扩大：

## 3.1 飞书入口层
必须实现：

- 飞书消息事件接收
- 基本文本回执
- 飞书确认卡片发送
- 飞书卡片交互回调
- 至少一种高风险动作从飞书进入任务系统

## 3.2 任务系统
必须实现：

- message_id 幂等
- task_records
- task_steps
- Celery 异步执行
- `/api/v1/tasks`
- `/api/v1/tasks/{task_id}`
- `/api/v1/tasks/{task_id}/steps`

## 3.3 业务动作
当前阶段只强制要求这两个动作稳定成立：

- `product.update_price`
- `system.confirm_task`

说明：
- `product.update_price` 是高风险动作主故事
- `system.confirm_task` 是确认放行入口
- 不要求当前阶段同时做满其它业务动作

## 3.4 状态流转
至少必须稳定支持这些状态：

- `pending`
- `processing`
- `awaiting_confirmation`
- `succeeded`
- `failed`
- `cancelled` 或 `rejected`

## 3.5 执行层
当前阶段执行层允许以下实现之一或组合：

- mock 执行
- API 执行
- Yingdao bridge 文件链执行
- Yingdao 真点击执行

但要求：

- 执行层必须是“可插拔”的
- 不允许把执行层写死成只有一种后端
- 当前主故事优先保证闭环稳定，不优先追求执行后端花样

## 3.6 结果回写
必须至少回写到以下两个位置：

1. 飞书消息或飞书卡片
2. 任务系统（`task_records` + `task_steps`）

Bitable 在当前阶段是“可选增强项”，不是唯一验收条件。
如果仓库里已有稳定 Bitable 写入基础，可以继续复用；
如果当前改动会拖慢主线，不要为追求 Bitable 完整度破坏主线。

---

# 4. 当前阶段 Out of Scope（禁止扩展）

以下内容当前阶段一律不做，禁止编码智能体擅自加入：

## 4.1 禁止扩平台
- 不扩 Odoo 主线
- 不扩 Chatwoot 主线
- 不扩第二、第三个业务平台
- 不做多平台统一运营大平台

## 4.2 禁止扩岗位
- 不追求四岗位全覆盖
- 不为了“完整”补产品/仓库/客服/财务所有动作
- 不为了“好看”加大量只读动作

## 4.3 禁止扩能力
- 不做多智能体协作
- 不做 deepagents 主框架
- 不做审批流系统
- 不做复杂双向同步 Bitable 平台
- 不做生产级多租户
- 不做 K8s / 集群 / 正式上线架构
- 不做与当前最小闭环无关的 RAG 扩展
- 不做无明确业务价值的抽象重构

## 4.4 禁止改写主叙事
禁止把当前阶段主叙事改写成：

- “完整飞书 ERP 中台”
- “全平台统一 Agent 系统”
- “四岗位自动化平台全部落地”
- “多智能体工作流实验”
- “先补平台能力，闭环以后再说”

---

# 5. 当前阶段固定技术栈

## 5.1 后端
- Python
- FastAPI

## 5.2 编排
- LangGraph（保留现有主链）
- 禁止引入 deepagents 替代主链

## 5.3 存储
- SQLite 允许继续作为当前本地演示与开发方案
- PostgreSQL 可保留兼容，但当前阶段不强制迁移
- 不允许为了“架构更正规”强行切库并打断主线

## 5.4 异步任务
- Celery
- Redis

## 5.5 ORM / 数据层
- SQLAlchemy 或当前仓库已有数据访问层
- 不允许为“统一风格”大改任务表/步骤表结构

## 5.6 配置
- `.env`
- `.env.example`

## 5.7 日志
- 结构化日志优先
- 至少要保证任务创建、确认、执行、失败可查

## 5.8 时区
- Asia/Shanghai

---

# 6. 当前阶段业务动作冻结

## 6.1 当前唯一强制稳定动作
### `product.update_price`
最小参数要求：
- `sku`
- `target_price`

可选：
- `platform`
- `currency`
- `reason`

默认：
- `platform=woo`
- `currency=CNY`

语义冻结：
- 这是高风险动作
- 默认 `confirm_required=true`
- 不允许直接无确认写入成功态
- 必须经过确认链或明确的拒绝链

### `system.confirm_task`
最小参数要求：
- `target_task_id`

可选：
- `confirm_action`

默认：
- `confirm_action=confirm`

语义冻结：
- 只能用于确认 / 拒绝一个已进入 `awaiting_confirmation` 的任务
- 不允许承担普通业务动作
- 不允许重写成新的主业务入口

## 6.2 当前允许保留的执行验证动作
### `warehouse.adjust_inventory`
它当前只作为执行层验证动作使用。

允许用于：
- Yingdao bridge
- mock executor
- real_nonprod_page
- P90 / P91 验证

禁止用于：
- 抢占对外主故事
- 改写当前飞书最小闭环主线

---

# 7. 飞书交互冻结

## 7.1 飞书消息入口
当前阶段必须支持：
- 用户在飞书发文本消息
- 系统能识别出高风险改价请求
- 系统创建任务并回执最小文本结果

## 7.2 飞书确认卡片
当前阶段必须实现：
- 针对 `product.update_price` 发送确认卡片
- 卡片至少展示：
  - `task_id`
  - `sku`
  - `target_price`
  - 风险提示
  - 操作按钮

## 7.3 飞书卡片按钮
至少支持两个动作：
- Confirm / 确认执行
- Reject / 取消或拒绝

## 7.4 飞书卡片回调
回调语义冻结：
- Confirm -> 触发 `system.confirm_task`
- Reject -> 原任务进入 `cancelled` / `rejected`
- 不允许卡片回调绕过任务系统直接写业务结果

## 7.5 飞书最终反馈
执行完成后必须至少做到以下之一：
- 更新原卡片状态
- 发送一条最终文本消息
- 两者都做更好

但原则不变：
- 用户必须能从飞书侧看到最终状态
- 不允许只在数据库里成功，飞书无反馈

---

# 8. 任务状态机冻结

## 8.1 原任务 `product.update_price`
固定流转：

`pending -> processing -> awaiting_confirmation -> succeeded / failed / cancelled`

## 8.2 确认任务 `system.confirm_task`
固定流转：

`pending -> processing -> succeeded / failed`

## 8.3 拒绝分支
若用户点击拒绝：
- 原任务必须进入 `cancelled` 或 `rejected`
- `/steps` 中必须留下拒绝步骤
- 飞书侧必须可见拒绝结果

## 8.4 幂等要求
以下场景必须考虑幂等：

- 重复消息
- 重复点击确认
- 重复点击拒绝
- 同一任务既被确认又被取消的竞态

当前阶段不要求最复杂的并发治理，
但至少要避免明显重复执行。

---

# 9. 执行层冻结

## 9.1 执行层原则
执行层是“手”，不是“大脑”。

大脑负责：
- 解析
- 任务创建
- 确认链
- 状态流转

执行层负责：
- 实际动作执行
- 返回结果
- 提供证据
- 提供失败原因

## 9.2 当前允许的执行后端
允许存在：

- `mock`
- `api`
- `yingdao_bridge_file`
- `yingdao_real_click`

但注意：
- 当前阶段不能为了某个后端重写全部主链
- 当前阶段优先保证 `product.update_price` 闭环成立
- P90 / P91 属于执行层验证子线，不得反向主导整个仓库结构

## 9.3 Yingdao 相关边界
Yingdao 相关实现允许继续推进，但必须遵守：

- 不改写飞书主故事
- 不把 `warehouse.adjust_inventory` 变成当前唯一主线
- 不因真点击验证破坏 `/tasks`、`/steps`、confirm 语义
- 不伪造“真点击已完成”
- mock / bridge / real click 必须明确区分

---

# 10. RAG 策略冻结

当前阶段：
- RAG 不是唯一验收核心
- 不要求当前所有动作都接入真实 RAG
- 不允许为了补 RAG 而打断飞书最小闭环

允许：
- 保留现有 RAG 结构
- 为后续阶段预留接口

禁止：
- 扩写大量规则库 / FAQ / 向量库逻辑
- 把当前阶段目标改写成“先把 RAG 做完整”
- 让 RAG 成为阻塞飞书卡片闭环的前置条件

---

# 11. Bitable 策略冻结

当前阶段 Bitable 不是唯一必做项，而是“可选增强项”。

## 11.1 若已有稳定基础
允许复用当前 append 台账能力。

## 11.2 当前阶段推荐最小字段
若写入 Bitable，优先只保留：
- `task_id`
- `intent`
- `sku`
- `status`
- `result_summary`
- `created_at`
- `updated_at`

## 11.3 禁止事项
- 不做复杂双向同步
- 不把 Bitable 做成主数据库
- 不为 Bitable 字段完美设计而拖慢主线

---

# 12. 测试与演示冻结

## 12.1 当前阶段必须可演示
至少要能演示：
1. 飞书发起高风险改价
2. 系统进入 `awaiting_confirmation`
3. 飞书确认卡片出现
4. 用户点击确认或拒绝
5. 系统执行并回写结果
6. `/tasks` 与 `/steps` 可查

## 12.2 当前阶段必须至少覆盖的测试
至少要有：

- 一个 `product.update_price` 进入 `awaiting_confirmation` 的测试
- 一个 `system.confirm_task` 成功测试
- 一个拒绝分支测试
- 一个重复点击或幂等测试
- 如果执行层接通，再补一个 success path / 一个 failure path

## 12.3 测试原则
- 优先补主故事测试
- 不为了追求覆盖率去补大量边缘动作
- 不允许跳过主故事而只测底层工具函数

---

# 13. README / 文档策略冻结

当前阶段 README 和文档必须围绕“最小业务闭环”组织。

必须强调：
- 飞书入口
- 高风险确认
- 执行层
- 任务留痕
- 可演示闭环

不要再把 README 主叙事写成：
- 四岗位全量平台
- 全平台统一能力图谱
- 复杂中台路线图

---

# 14. 编码智能体执行规则

## 14.1 每轮开发的默认顺序
除非用户明确要求，否则开发顺序固定为：

1. 先保证主故事不被破坏
2. 再补飞书确认卡片
3. 再补卡片回调
4. 再补结果回写
5. 再补测试与演示
6. 最后才补增强项（Bitable / Yingdao 验证 / RAG 等）

## 14.2 遇到冲突时的优先级
若出现冲突，优先级固定为：

1. 飞书最小业务闭环
2. 任务状态机与幂等
3. `/tasks` 与 `/steps`
4. 执行层可插拔
5. Bitable
6. RAG
7. 平台扩展

## 14.3 严禁行为
编码智能体严禁：

- 擅自扩大范围
- 擅自改写主故事
- 把验证子线写成主线
- 为了“更优雅”大重构
- 为了“更完整”补四岗位全量动作
- 为了“更像平台”扩 Odoo / Chatwoot / 第三平台
- 把当前阶段写成研究型 Agent 项目

---

# 15. 当前阶段一句话验收标准

只有当下面这句话成立时，才算当前阶段通过：

> 用户可以在飞书中发起一个高风险改价请求，系统会创建任务、进入确认态、发送确认卡片、在确认后进入执行层，并将最终结果稳定回写到飞书与任务系统中，且全过程可通过 `/tasks` 与 `/steps` 追踪。

如果这句话还不成立，
就不要继续扩平台、扩岗位、扩能力。

## P9-B 当前唯一主线（SQLite 留痕回接验证）

### 1. 当前阶段重新定义
当前不要再把 P9 理解为“影刀执行层继续验证”。
影刀执行层 success 主链已经通过，当前真正未收口的是：

- 主系统留痕回接
- `/tasks`、`/steps`、`action_executed.detail`
- 数据库真相源落地
- 飞书多维表台账挂接



当前唯一主线为：

**P9-B：主系统留痕回接（SQLite 验证版）**

### 2. 当前必须继承的真实事实
以下内容已经成立，不要回头重做：

- ShadowBot real-runtime success 真点击链已成立
- self-hosted real_nonprod_page 已真实执行成功
- success 样本已验证 `100 -> 105`
- runtime `done.json` 已成立
- 左侧 `outbox.output.json` 已成立
- `bridge_result_timeout` 在 success 样本中已收住
- evidence 至少已有 runtime-result.json 兜底文件

### 3. 当前不要再做的事
禁止：

- 继续深挖 failure 分支
- 继续修改 ShadowBot success 主流程
- 继续打磨注入式 failure 副本
- 扩第二个动作
- 切到 `product.update_price`
- 接真实生产页
- 做真实截图增强
- 做 latest-file 临时方案回收
- 先上 PostgreSQL 作为第一验证环境
- 让 ShadowBot 直接写飞书多维表
- 重构任务系统主链

### 4. 当前唯一目标
把已经跑通的 real-runtime success 结果，正式回接到主系统数据库留痕。

最低要求：

- `task_records` 有记录
- `task_steps` 有记录
- `action_executed.detail` 有 RPA 字段
- `/tasks` `/tasks/{task_id}` `/tasks/{task_id}/steps` 可查
- 后续再由主系统异步写飞书多维表

### 5. 当前数据库策略
当前阶段固定：

- **先用 SQLite 做主系统留痕回接验证**
- PostgreSQL 回归后移到下一轮

原则：

- 数据库是真相源
- 多维表只是业务台账
- 当前不能把多维表当唯一留痕源

### 6. 当前 RPA 结果留痕字段
本轮 `action_executed.detail` 最小必须包含：

- `rpa_vendor`
- `run_id`
- `operation_result`
- `verify_passed`
- `verify_reason`
- `page_failure_code`
- `failure_layer`
- `page_steps`
- `page_evidence_count`
- `screenshot_paths`

### 7. 当前 Bitable 策略
当前不要把 RPA 留痕直接塞进旧业务逻辑里混写。
建议结构：

- 保留原任务业务台账主表
- 新增一张 `RPA执行证据台账`

当前阶段先定字段，不要求一开始就全部做完。

### 8. 当前 agent 行为约束
agent 本轮只允许做这些事：

1. 起 SQLite 验证环境
2. 让 success 样本结果正式进入主系统数据库
3. 保证 `/tasks` `/steps` `/detail` 可查
4. 设计并冻结 Bitable 的 RPA 执行证据表字段
5. 补对应文档

agent 本轮不允许：

- 修改 ShadowBot 成功主流程
- 继续折腾 failure 副本
- 引入 PostgreSQL 作为首验收依赖
- 改写 README 总叙事
- 扩展额外业务动作
- 对外宣称飞书侧留痕已经完成，除非多维表和主系统链都已人工验收

### 9. 当前验收标准
只有满足下面条件，才算本轮通过：

1. 8000 主系统可启动
2. worker 可启动
3. success 样本经主系统正式执行
4. `task_records` 有记录
5. `task_steps` 有记录
6. `action_executed.detail` 有 RPA 字段
7. `/tasks` `/steps` API 可查
8. success 仍然保持 `100 -> 105`
9. Bitable RPA 执行证据表字段设计已冻结



## 当前阶段入口（必须先读）

当前唯一主线为：

P14-C：LLM 异常原因解释

本轮是 A 项目主导开发，B 项目原则上不改。

A 项目：feishu-rpa-commerce-agent  
定位：飞书入口层、消息编排层、任务编排层、LLM 异常解释层、老板交互层。

B 项目：Ecom-Watch-Agent-Agent  
定位：业务服务层，负责 monitor target、价格采集、采集状态、可信度诊断、异常检测、URL 治理状态、决策建议字段生成。

P14-A 已完成并收口：
- 规则未命中时可触发 LLM intent fallback
- LLM fallback 有 allowlist
- LLM fallback 有 confidence 阈值
- 低置信度会返回澄清
- system.confirm_task 不允许由 LLM fallback 生成
- product.update_price 不绕过确认，只能进入 awaiting_confirmation
- 飞书实机验收已通过

P14-B 已完成并收口：
- 新增 ecom_watch.monitor_summary
- 支持价格监控总体总结
- 支持监控健康度总结
- 支持重点处理对象总结
- 支持 summary_focus=overview / health_check / priority_targets
- 支持 LLM provider 失败降级为规则摘要
- 支持 llm_monitor_summary_* steps 留痕
- 飞书实机验收已通过

当前 P14-C 只做：

LLM 异常原因解释。

固定原则：

- A 负责识别异常解释类 intent
- A 负责调用 B 获取已有监控对象与诊断字段
- A 负责组织 explanation 输入
- A 负责调用 LLM 生成老板可读异常解释
- B 负责生成采集状态、价格可信度、页面类型、异常状态、异常原因、决策建议字段
- LLM 只做解释，不做执行
- LLM 不重新计算 B 的诊断字段
- LLM 不自动刷新
- LLM 不自动重试
- LLM 不自动替换 URL
- LLM 不自动删除对象
- LLM 不自动改价
- LLM 不触发 RPA
- LLM 失败时必须降级为规则解释或友好错误

本轮必须先读以下约束文件：

1. docs/p14/p14c-project-plan.md
2. docs/p14/P14C-agent-prompt.md
3. docs/p14/p14c-boss-demo-sop.md
4. docs/p14/p14c-acceptance-checklist.md

如果以上文件不存在，先创建文档，不要直接开写业务代码。

当前禁止：

- 不做 P14-D 操作计划生成
- 不做 P15 OCR
- 不做发票识别
- 不做自动刷新
- 不做自动重试
- 不做自动替换 URL
- 不做自动删除对象
- 不做自动改价
- 不做主动通知
- 不做真正告警系统
- 不做 Playwright / 浏览器渲染
- 不做代理池
- 不处理 Amazon 反爬
- 不改 B 项目采集逻辑
- 不重构 P14-A
- 不重构 P14-B
- 不破坏 P13-I 价格诊断字段
- 不破坏 P13-K 决策建议字段
- 不破坏 P12 卡片交互层

P14-C 最小通过标准：

- 能识别“为什么价格不准 / 为什么低可信 / 为什么需要人工处理”类命令
- A 能获取监控对象诊断字段
- LLM 能基于已有字段生成老板可读异常解释
- 解释包含：问题是什么、为什么出现、对价格判断的影响、建议怎么处理、不会自动执行提醒
- LLM 不编造不存在的数据
- LLM 不承诺自动处理
- LLM 失败时能降级为规则解释
- task_steps 有 llm_anomaly_explanation_started / succeeded / failed / fallback_used 留痕
- 不破坏 P14-A
- 不破坏 P14-B
- 不破坏 P13-I / P13-K