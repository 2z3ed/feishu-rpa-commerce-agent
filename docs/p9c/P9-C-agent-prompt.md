# P9-C 当前阶段约束文档（Agent 必须先读）

你现在接手的是 feishu-rpa-commerce-agent 项目。

当前不要发散，也不要误判主线。

## 一、你必须先接受的当前真实状态

当前阶段不是继续做 P9-B，也不是继续做影刀执行层验证。

当前已经成立的是：

- P8 已收口
- P9 已完成“影刀执行层验证”
- P9-B 已完成“主系统留痕回接（SQLite 验证版）”
- 当前 SQLite 真相源已成立
- `/api/v1/tasks/`
- `/api/v1/tasks/{task_id}`
- `/api/v1/tasks/{task_id}/steps`
  已可查
- `task_records`
- `task_steps`
- `action_executed.detail`
  已可留痕
- success baseline 已固定成立：A001 从 100 -> 105

当前唯一主线已经切换为：

P9-C：飞书多维表异步回写接入（SQLite 真相源版）

## 二、开始前必须先读

开始任何开发前，必须先读：

### 先读 P9-B 收口材料
1. docs/p9b/p9b-handoff.md
2. docs/p9b/p9b-closure-report.md
3. docs/p9b/p9b-bitable-schema.md
4. docs/p9b/p9b-sqlite-acceptance-sop.md

### 再读 P9-C 当前阶段文件
5. docs/p9c/p9c-project-plan.md
6. docs/p9c/P9-C-agent-prompt.md

如果 docs/p9b 或 docs/p9c 中存在文件名漂移，
先 `ls -la` 确认真实文件名，再继续。
不要因为文件名不一致而停在“找文件”这一步空转。

## 三、当前唯一目标

把已经存在于主系统中的 success 结果，
由主系统异步追加到飞书多维表：

RPA执行证据台账

当前只补这一层：

主系统 → 飞书多维表

不要回头再补：

- 影刀会不会点
- done/outbox 会不会回
- SQLite 留痕会不会落
- `/tasks` `/steps` 能不能查

这些已经不是当前主线。

## 四、当前技术原则（必须继承）

以下原则必须继承，不得推翻：

1. 数据库 = 真相源
2. 飞书多维表 = 业务台账 / 协同层
3. ShadowBot = 页面执行器
4. ShadowBot 不直接写飞书 / 多维表
5. 主系统负责写：
   - task_records
   - task_steps
   - action_executed.detail
   - 回飞书
   - 多维表
6. 本轮仍使用 SQLite 做首验收
7. 保留原业务台账主表
8. 本轮只接新建的：
   RPA执行证据台账

## 五、当前固定表结构（必须对齐）

你要写入的表已经建好。
不要擅自改字段名。

固定字段如下：

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

## 六、本轮只允许先做 success 样本

当前只做：

- `warehouse.adjust_inventory`
- `rpa_runtime_success`
- A001：100 -> 105

固定建议值：

- `provider_id = yingdao_local`
- `capability = warehouse.adjust_inventory`
- `execution_mode = rpa`
- `runtime_state = done`

不要一上来就扩：

- `rpa_runtime_failed`
- 第二个动作
- 第二张表
- 主表联动追加
- PostgreSQL 回归

## 七、当前你要做的事

### P9-C.0：写入环境锚定
你需要先确认：

- 当前 venv 可用
- 当前 `lark_oapi` 依赖是否存在
- 当前飞书 app 配置读取位置
- 当前多维表 app_token / table_id / 写入开关
- 当前写入位置应该挂在主系统哪里
- 当前写入失败是否能做到非阻塞

### P9-C.1：最小写入接入
你只需要先打通：

主系统 success 样本
→ 组装 bitable payload
→ 追加 1 条到 RPA执行证据台账

### P9-C.2：一致性验收
你需要核对：

- `/api/v1/tasks/{task_id}`
- `/api/v1/tasks/{task_id}/steps`
- `action_executed.detail`
- 飞书多维表记录

这四者的字段口径是否一致。

### P9-C.3：非阻塞告警固定
你需要固定：

- 写表失败不影响主链 success
- 写表异常只作为告警 / warning / detail 附加信息
- 不回退 SQLite 真相源结果

## 八、当前明确不要做

当前禁止做：

- 不切 PostgreSQL 作为首验收环境
- 不扩第二个动作
- 不切到 `product.update_price`
- 不深挖 ShadowBot failure
- 不继续打 failure 副本
- 不修改 ShadowBot success 主流程
- 不让 ShadowBot 直接写飞书多维表
- 不把飞书多维表当真相源
- 不重构既有任务系统主链
- 不把 P9-C 做成大而全的通用台账框架
- 不回头重做 P8 / P9 / P9-B 收口文档

## 九、当前工作方式要求

你必须先检查仓库真实状态，再做最小改动。

每完成一小段，都必须按这个格式回报：

A. 本轮做了什么
B. 改了哪些文件
C. 如何启动 / 复验
D. 是否通过
E. 下一步建议

不允许：

- 只给计划，不给结果
- 只贴 diff，不给中文结论
- 自由发挥输出其他语言

## 十、输出语言要求

强制要求：

- 只允许使用简体中文输出
- 不要输出越南语、英语段落、德语、俄语等其他语言
- 命令、路径、代码可保留原文
- 解释、结论、汇报必须全部使用简体中文

## 十一、下一条回复格式（必须严格遵守）

下一条只允许按下面格式回复：

A. 先读了哪些文件
B. 当前写表环境锚定结果
C. 本轮实际执行了哪些命令
D. 改了哪些文件
E. success 样本是否已真正写入多维表
F. 主系统结果与多维表结果是否一致
G. 当前阶段结论
H. 下一步建议

判断标准只有 3 个：

- 可复验
- 可查询
- 可回写

## 十二、P9-C.3 收口冻结补充（必须继承）

### 1) 干净进程样本（固定）

- run_id：`P92-1776872728677-f3aef2aa`
- confirm_task_id：`TASK-P9B-ODOO-ADJ-CFM-P92-1776872728677-f3aef2aa`
- baseline：`A001 100 -> 105`

### 2) 通过依据（固定）

- `/api/v1/tasks/{confirm_task_id}` 为 `succeeded`
- `/api/v1/tasks/{confirm_task_id}/steps` 包含：
  - `bitable_write_started`
  - `bitable_write_succeeded`
  - `record_id=recvhxeZuXxPWr`
- 飞书多维表 `RPA执行证据台账` 可回读该 record，字段与主系统一致

### 3) 本轮风险冻结（固定口径）

- 本地 `lark_oapi` stub 遮蔽 `lark_oapi.api` 属已知风险
- bitable 已接 HTTP fallback，保障写入与非阻塞
- 本轮不扩展为 SDK 重构任务，不阻塞收口

### 4) 配置项决策（固定）

- 当前按表名解析 `RPA执行证据台账` 可用
- `FEISHU_RPA_EVIDENCE_TABLE_ID` 作为下一轮最小增强项，不阻塞 P9-C 收口