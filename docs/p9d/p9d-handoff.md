# P9-D 交接入口（收口后）

当前主线状态：

P9-D：已收口（飞书多维表配置稳态化最小增强版）

## 1. 必读文档顺序

1. `docs/p9d/p9d-project-plan.md`
2. `docs/p9d/P9-D-agent-prompt.md`
3. `docs/p9d/p9d-closure-report.md`

## 2. 当前冻结事实

- 显式 table_id 优先已接入并实机通过
- 固定样本已通过：
  - task_id：`TASK-P9B-ODOO-ADJ-CFM-P92-1776917966037-2692c457`
  - record_id：`recvhAiNwDV8JR`
  - baseline：`A001 100 -> 105`
- `sku` 已稳定写入 `RPA执行证据台账` 独立列
- `/api/v1/tasks*` 与 `action_executed.detail` 仍可查询
- 写表失败非阻塞边界仍成立

## 3. 当前边界（继续禁止扩展）

- 不扩第二动作
- 不扩 failure 分支
- 不切 PostgreSQL 作为首验收
- 不改 ShadowBot success 主流程
- 不重构飞书 SDK 全链路

## 4. 后移项（不阻塞）

1. PostgreSQL 回归继续后移
2. failure 分支继续后移
3. `lark_oapi` 全链路治理继续后移
4. SQLite 仍保持首验收边界

## 5. 下一阶段候选方向（仅方向）

1. P10-A：SQLite 稳定性回归与收口固化  
2. P10-B：PostgreSQL 回归验收（语义不变）  
3. P10-C：failure 分支最小闭环补验  
4. P10-D：`lark_oapi` 风险最小治理  

说明：以上仅为候选方向，不代表本轮开工。

