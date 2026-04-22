# P9-C 开发主线文档
## 阶段名称
P9-C：飞书多维表异步回写接入（SQLite 真相源版）

## 一、阶段背景

P9-B 已经完成并收口。

当前已经成立的能力是：

- SQLite 作为本轮真相源已成立
- 主系统留痕闭环已成立
- `task_records`、`task_steps`、`action_executed.detail` 已可落库
- `/api/v1/tasks/`
- `/api/v1/tasks/{task_id}`
- `/api/v1/tasks/{task_id}/steps`
  已可查询
- success baseline 已固定成立：A001 从 100 -> 105

但当前还没有完成的是：

- 主系统异步回写飞书多维表
- RPA执行证据台账在飞书侧的自动追加
- 多维表写入失败与主链成功解耦的稳定收口

因此，P9-C 的目标不是继续补执行层，也不是切 PostgreSQL，而是：

把已经成立的 SQLite 真相源结果，
由主系统异步追加到飞书多维表。

## 二、本阶段唯一目标

让主系统在接住 RPA 执行结果并完成数据库留痕后，
异步把同一轮结果追加到飞书多维表中的：

RPA执行证据台账

并满足以下原则：

1. 数据库仍然是真相源
2. 飞书多维表只是业务台账 / 协同层
3. 写多维表失败不影响主链 success
4. ShadowBot 不直接写多维表
5. 仍只围绕 `warehouse.adjust_inventory`
6. 仍以 SQLite 为本轮首验收环境

## 三、当前冻结前提（必须继承）

以下内容必须继承，不得推翻：

- 数据库 = 真相源
- 飞书多维表 = 业务台账 / 协同层
- ShadowBot = 页面执行器
- ShadowBot 不直接写飞书 / 多维表
- 主系统负责：
  - 写 task_records
  - 写 task_steps
  - 写 action_executed.detail
  - 回飞书
  - 写多维表

保留原业务台账主表；
本轮只接入新建的：

RPA执行证据台账

## 四、本阶段写入对象

本轮固定写入飞书多维表中的表：

RPA执行证据台账

当前字段冻结如下（按既有建表结果）：

1. 台账类型
2. task_id
3. target_task_id
4. run_id
5. provider_id
6. capability
7. execution_mode
8. runtime_state
9. operation_result
10. sku
11. old_inventory
12. target_inventory
13. new_inventory
14. verify_passed
15. verify_reason
16. page_failure_code
17. failure_layer
18. page_steps
19. page_evidence_count
20. screenshot_paths
21. latest_evidence_path
22. result_summary
23. created_at
24. finished_at

## 五、本阶段最小写入口径

本轮先只覆盖：

### 1. success 样本
固定基线：
A001：100 -> 105

### 2. 台账类型
- `rpa_runtime_success`

### 3. 固定字段建议值
- `provider_id = yingdao_local`
- `capability = warehouse.adjust_inventory`
- `execution_mode = rpa`
- `runtime_state = done`

### 4. 主要来源
字段应优先来自以下位置：

- `task_records`
- `task_steps`
- `action_executed.detail`
- RPA evidence 路径
- 当前任务结果摘要

## 六、推荐链路

目标链路为：

主系统入口
→ 建任务
→ confirm 放行
→ YingdaoRunner / bridge / ShadowBot 执行
→ done/outbox 回传
→ 主系统写 `task_records / task_steps / action_executed.detail`
→ 主系统组装 bitable payload
→ 主系统异步追加飞书多维表
→ 写入成功或写入告警，不回滚主链 success

## 七、分阶段计划

### P9-C.0：飞书多维表写入环境锚定
目标：
把多维表写入所需配置、依赖和目标表锚定清楚。

需要完成：
1. 明确本轮仍使用 SQLite
2. 明确飞书 app 配置读取位置
3. 明确多维表 app_token / table_id / 写入开关
4. 明确 `lark_oapi` 依赖是否在当前 venv 可用
5. 明确写入失败时为“非阻塞告警”，不影响主链成功
6. 明确 payload 字段与多维表字段一一映射

本阶段产出：
- 写入配置说明
- 写入字段映射说明
- 非阻塞边界说明

### P9-C.1：主系统异步追加多维表最小接入
目标：
让主系统在 success 样本结束后，真正执行一次多维表追加。

需要完成：
1. 选择主系统内唯一写表位置
2. 从已落库结果组装 payload
3. 只写入 `RPA执行证据台账`
4. 先打通 `rpa_runtime_success`
5. 写入失败时记录 warning / detail，但不让任务回退为失败

本阶段产出：
- 一条真实追加的飞书多维表记录
- 主链 success 不受写表失败影响的证明

### P9-C.2：验收与查询对齐
目标：
验证多维表追加和主系统查询链路一致，不出现口径漂移。

需要完成：
1. 核对 task_id / run_id / result_summary 一致
2. 核对 old_inventory / target_inventory / new_inventory 一致
3. 核对 verify_passed / verify_reason 一致
4. 核对 screenshot_paths / latest_evidence_path 一致
5. 输出一份最小人工验收记录

本阶段产出：
- 主系统与飞书多维表的一致性记录
- 成功样本对照结果

### P9-C.3：非阻塞失败收口
目标：
把“写表失败不影响主链”的边界固定下来。

需要完成：
1. 明确缺依赖、鉴权失败、字段映射失败的处理方式
2. 保证 bitable 写入异常不会回退主系统 success
3. 明确日志、task_steps 或 detail 中的最小告警落点
4. 更新 P9-C handoff / closure 文档

本阶段产出：
- P9-C 收口依据
- bitable 非阻塞策略固定

## 八、本阶段最低通过标准

P9-C 最低通过标准只定这么窄：

1. 仍只围绕 `warehouse.adjust_inventory`
2. 仍只围绕 RPA执行证据台账
3. 仍使用 SQLite 作为首验收真相源
4. success baseline 至少追加成功 1 条到飞书多维表
5. 该条记录与 `/api/v1/tasks*` 结果一致
6. bitable 写入异常不会让主系统 success 回退失败
7. 不破坏 P9-B 已收口主链

## 九、本阶段明确不做什么

本轮不做：

- 不切 PostgreSQL 作为首验收环境
- 不扩第二个动作
- 不切到 `product.update_price`
- 不深挖 ShadowBot failure
- 不回头改 ShadowBot success 主流程
- 不让 ShadowBot 直接写飞书多维表
- 不把飞书多维表当真相源
- 不重构既有任务系统主链
- 不先做大而全的主表/证据表双写改造
- 不把 bitable 接入扩成通用框架

## 十、建议的实现原则

1. 写表逻辑应挂在主系统，不挂在 ShadowBot / bridge
2. 先 success，后最小告警，不先做 failure 大收口
3. 先单表、单动作、单样本，不先抽象多平台
4. 先保证字段对齐，再考虑通用化
5. 任何 bitable 写入错误都不得破坏 SQLite 真相源结果

## 十一、P9-C.3 收口冻结结果（2026-04-22）

### 1. 干净进程最终样本（冻结）

- run_id：`P92-1776872728677-f3aef2aa`
- orig_task_id：`TASK-P9B-ODOO-ADJ-ORIG-P92-1776872728677-f3aef2aa`
- confirm_task_id：`TASK-P9B-ODOO-ADJ-CFM-P92-1776872728677-f3aef2aa`
- baseline：`A001 100 -> 105`

### 2. 主系统查询冻结依据

- `/api/v1/tasks/{confirm_task_id}` 为 `succeeded`
- `/api/v1/tasks/{confirm_task_id}/steps` 包含：
  - `bitable_write_started`
  - `bitable_write_succeeded`
  - `record_id=recvhxeZuXxPWr`
- `/api/v1/tasks/{orig_task_id}` 为 `succeeded`

### 3. 多维表回写冻结依据

- 目标表：`RPA执行证据台账`
- table_id：`tblJVq5GgBKn8gaA`
- record_id：`recvhxeZuXxPWr`
- 回读关键字段一致：
  - `task_id/run_id/target_task_id`
  - `old_inventory=100`
  - `target_inventory=105`
  - `new_inventory=105`
  - `verify_passed=true`
  - `verify_reason=post_inventory_matches_target`
  - `screenshot_paths/latest_evidence_path`

### 4. 本轮关键风险与冻结处理

- 风险：仓库本地 `lark_oapi` stub 会遮蔽真实 SDK 导入路径（`lark_oapi.api`）。
- 处理：bitable 写入增加 HTTP fallback（使用 tenant_access_token + bitable open api）。
- 结论：本轮不重构 SDK 加载链路，作为已知风险冻结；fallback 已满足“可回写+非阻塞”。

### 5. FEISHU_RPA_EVIDENCE_TABLE_ID 决策

- 当前“按表名自动解析 table_id”可用，但依赖表名稳定不变。
- 增加显式 env 的收益：降低运行时表名依赖，减少误写风险，便于多环境配置。
- 决策：本轮文档冻结，下一轮以最小改动新增 `FEISHU_RPA_EVIDENCE_TABLE_ID`（不阻塞 P9-C 收口）。