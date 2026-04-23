# P9-D 当前阶段约束文档（Agent 必须先读）

## 当前状态（已收口）

P9-D 已完成，不再继续扩功能开发。

冻结样本：

- task_id：`TASK-P9B-ODOO-ADJ-CFM-P92-1776917966037-2692c457`
- bitable record_id：`recvhAiNwDV8JR`
- baseline：`A001 100 -> 105`

冻结结论：

1. 显式 table_id 优先已实机通过
2. real-runtime 基线已重新跑通
3. `sku` 已稳定写入多维表独立列
4. 当前仅允许做文档收口与交接整理

## 当前状态（已收口）

P9-D 已完成，不再继续扩功能开发。

冻结样本：

- task_id：`TASK-P9B-ODOO-ADJ-CFM-P92-1776917966037-2692c457`
- bitable record_id：`recvhAiNwDV8JR`
- baseline：`A001 100 -> 105`

冻结结论：

1. 显式 table_id 优先已实机通过
2. real-runtime 基线已重新跑通
3. `sku` 已稳定写入多维表独立列
4. 当前仅允许做文档收口与交接整理

你现在接手的是 feishu-rpa-commerce-agent 项目。

当前不要发散，也不要误判主线。

## 一、你必须先接受的当前真实状态

当前阶段不是继续做 P9-C 的功能打通，
而是做 P9-C 后的最小配置稳态化。

当前已经成立的是：

- P8 已收口
- P9 已完成“影刀执行层验证”
- P9-B 已完成“主系统留痕回接（SQLite 验证版）”
- P9-C 已完成“飞书多维表异步回写接入（SQLite 真相源版）”
- RPA执行证据台账 已真实写入成功
- success baseline 已固定成立：A001 从 100 -> 105
- `/api/v1/tasks*` 可查
- bitable 写入非阻塞边界已成立

当前唯一主线已经切换为：

P9-D：飞书多维表配置稳态化（最小增强版）

## 二、开始前必须先读

先读上一阶段收口材料：

1. docs/p9b/p9b-handoff.md
2. docs/p9b/p9b-closure-report.md
3. docs/p9c/p9c-handoff.md
4. docs/p9c/p9c-closure-report.md

再读当前阶段文件：

5. docs/p9d/p9d-project-plan.md
6. docs/p9d/P9-D-agent-prompt.md

如果文件名与预期不一致，
先 `ls -la docs/p9b docs/p9c docs/p9d`，
确认真实文件名后继续。
不要停在“找文件”这一步空转。

## 三、当前唯一目标

把当前 bitable 写入链路做成更稳的配置形态：

- 增加 `FEISHU_RPA_EVIDENCE_TABLE_ID`
- 写表时显式 table_id 优先
- 按表名解析保留为回退
- 不破坏当前已成立的 success 回写链路

当前只补这一层：

配置稳态化

不要回头再补：
- ShadowBot 是否执行成功
- SQLite 是否落库
- `/tasks` `/steps` 是否可查
- bitable 是否能首次写入

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
7. 写表失败仍然非阻塞
8. 仍只围绕 `warehouse.adjust_inventory`
9. 仍只围绕 success baseline
10. 不扩第二动作
11. 不扩 failure 分支

## 五、本轮你只允许先做这些事

### P9-D.0：配置锚定
先确认：

- 当前 config 中是否已有 `FEISHU_RPA_EVIDENCE_TABLE_ID`
- 若没有，最小方式补到哪里
- 当前 bitable 写入逻辑在哪
- 当前 table_id 如何解析
- 当前 fallback 是否仍可用

### P9-D.1：最小代码接入
只做：

- 显式 table_id 优先
- 表名解析为回退
- 不改写表主链结构
- 不改 success 主流程

### P9-D.2：稳态验收
继续使用固定 baseline：

A001：100 -> 105

继续核对：

- `/api/v1/tasks/{task_id}`
- `/api/v1/tasks/{task_id}/steps`
- `action_executed.detail`
- 飞书多维表记录

### P9-D.3：最小收口
固定：

- env 优先策略
- 表名回退策略
- `lark_oapi` 风险当前边界
- 后移项清单

## 六、当前明确不要做

当前禁止做：

- 不切 PostgreSQL 作为首验收环境
- 不扩第二个动作
- 不切到 `product.update_price`
- 不扩 failure 分支
- 不深挖 ShadowBot failure
- 不修改 ShadowBot success 主流程
- 不重构飞书 SDK 全链路
- 不处理全部 IM 回复路径问题
- 不把 bitable 接入扩成通用大框架
- 不回头重做 P9-B / P9-C 收口文档

## 七、工作方式要求

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
- 输出其他语言

## 八、输出语言要求

强制要求：

- 只允许使用简体中文输出
- 命令、路径、代码可保留原文
- 解释、结论、汇报必须全部使用简体中文

## 九、下一条回复格式（必须严格遵守）

下一条只允许按下面格式回复：

A. 先读了哪些文件
B. 当前配置锚定结果
C. 本轮实际执行了哪些命令
D. 改了哪些文件
E. 显式 table_id 优先是否已接入
F. 主系统结果与多维表结果是否仍一致
G. 当前阶段结论
H. 下一步建议

判断标准只有 3 个：

- 可复验
- 可查询
- 可回写