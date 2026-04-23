# P9-D 开发主线文档
## 阶段名称
P9-D：飞书多维表配置稳态化（最小增强版）

## 阶段状态（已收口）

P9-D 已通过并收口，最终验收样本冻结如下：

- task_id：`TASK-P9B-ODOO-ADJ-CFM-P92-1776917966037-2692c457`
- bitable record_id：`recvhAiNwDV8JR`
- baseline：`A001 100 -> 105`

本阶段最终确认：

1. `FEISHU_RPA_EVIDENCE_TABLE_ID` 显式 table_id 优先生效
2. 缺省时按表名解析仍可回退
3. `sku` 已稳定写入 `RPA执行证据台账` 独立列
4. 写表失败仍保持非阻塞边界
5. 首验收边界仍为 SQLite 真相源

## 一、阶段背景

P9-C 已完成并收口。

当前已经成立的能力：

- SQLite 真相源已成立
- 主系统留痕闭环已成立
- `/api/v1/tasks/`
- `/api/v1/tasks/{task_id}`
- `/api/v1/tasks/{task_id}/steps`
  已可查询
- 飞书多维表 RPA执行证据台账 已可真实写入
- success baseline 已固定成立：A001 从 100 -> 105
- 写表失败不回退主链 success 的非阻塞边界已成立

但当前仍有两个稳定性问题：

1. 当前 RPA执行证据台账 table_id 主要依赖“按表名解析”
   - 可用
   - 但抗表名漂移能力弱

2. 当前存在本地 `lark_oapi` stub 遮蔽真实 SDK 的风险
   - 本轮已通过 HTTP fallback 绕开
   - 但尚未做最小稳态化收口

因此，P9-D 的目标不是扩能力，而是把 P9-C 已经跑通的链路做成更稳的配置方案。

## 二、本阶段唯一目标

把飞书多维表回写从“已打通”推进到“更稳定可重复”的状态。

本轮只做两件事：

1. 增加显式配置：
   `FEISHU_RPA_EVIDENCE_TABLE_ID`
2. 固定解析优先级：
   - 优先使用显式 table_id
   - 回退到按表名解析

同时保持以下原则不变：

- SQLite 仍是真相源
- 飞书多维表仍是业务台账 / 协同层
- 写表失败仍然非阻塞
- ShadowBot 仍不直接写飞书 / 多维表
- 仍只围绕 `warehouse.adjust_inventory`
- 仍只围绕 success baseline

## 三、当前冻结前提（必须继承）

以下内容必须继承，不得推翻：

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
7. 不切 PostgreSQL 做首验收
8. 不扩第二个动作
9. 不扩 failure 分支
10. 不回头改 P9-B / P9-C 已收口主链

## 四、本阶段核心改动点

### 1. 显式配置增加
新增环境变量：

- `FEISHU_RPA_EVIDENCE_TABLE_ID`

当前目标：

- 当该值存在时，直接写入对应 table_id
- 当该值缺失时，仍允许按表名解析 `RPA执行证据台账`
- 不因缺失该 env 而破坏当前已打通链路

### 2. table_id 解析优先级冻结
优先级固定为：

1. `FEISHU_RPA_EVIDENCE_TABLE_ID`
2. 按表名解析 `RPA执行证据台账`
3. 若仍失败，则进入 bitable 写入告警，但不回退主链 success

### 3. SDK 风险最小收口
当前已知风险：

- 本地 `lark_oapi` stub 遮蔽真实 SDK 导入路径

本轮原则：

- 不做 SDK 大重构
- 不大改现有 fallback 机制
- 只做“最小可控修复”或“风险冻结说明”
- 只要不影响主链与回写稳定性，即可通过

## 五、本阶段分段目标

### P9-D.0：配置锚定
目标：
锚定 `FEISHU_RPA_EVIDENCE_TABLE_ID` 的配置、读取位置和优先级。

需要完成：
- 在 config 中增加 env
- 在写表逻辑中读取该 env
- 明确优先级顺序
- 保持回退逻辑可用

### P9-D.1：最小代码接入
目标：
让显式 table_id 优先于按表名解析。

需要完成：
- 修改 bitable 写入逻辑
- 保持 P9-C 已有 success 样本不回退
- 保持非阻塞边界不变

### P9-D.2：稳态验收
目标：
验证显式配置优先后，主链仍成立。

需要完成：
- 继续使用 SQLite
- 继续跑固定 baseline：A001 100 -> 105
- 验证 `/tasks`、`/steps`、`action_executed.detail`
- 验证飞书多维表真实写入
- 验证写表字段与主系统一致

### P9-D.3：最小收口
目标：
固定当前配置策略、风险边界和后移项。

需要完成：
- 明确是否保留按表名解析作为长期回退
- 明确 `lark_oapi` 风险当前如何冻结
- 更新阶段文档
- 给出下一阶段候选方向

## 六、本阶段最低通过标准

P9-D 最低通过标准只定这么窄：

1. 成功读取 `FEISHU_RPA_EVIDENCE_TABLE_ID`
2. 写表时显式 table_id 优先
3. 缺少显式 table_id 时，仍可回退按表名解析
4. success baseline 至少再跑通 1 次
5. 多维表真实写入成功
6. 写表失败仍不影响主链 success
7. 不破坏 P9-C 已收口结果

## 七、本阶段明确不做什么

本轮不做：

- 不切 PostgreSQL 首验收
- 不扩第二个动作
- 不扩 failure 分支
- 不切到 `product.update_price`
- 不重构飞书 SDK 全链路
- 不处理 IM 回复路径的全部 SDK 风险
- 不改 ShadowBot success 主流程
- 不改 P9-B / P9-C 已冻结的 baseline
- 不把 bitable 接入扩成通用框架

## 八、建议实现原则

1. 先显式配置，再回退表名解析
2. 先稳定已有单表单动作链路，再考虑扩展
3. SDK 风险只做最小治理，不开大重构
4. 任何 bitable 异常都不得污染 SQLite 真相源结果
5. 当前阶段判断标准只有：
   - 可复验
   - 可查询
   - 可回写