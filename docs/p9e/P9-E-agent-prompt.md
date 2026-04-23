# P9-E Agent 提示（收口冻结版）

## 当前阶段状态
P9-E 已通过并冻结，当前只允许做文档收口、复盘、交接，不再扩功能。

## 冻结事实
- 主线动作：`warehouse.adjust_inventory`
- baseline：`A001 100 -> 105`
- 首验收边界：SQLite
- 真实飞书 `om_*` 消息送达：已通过
- `/tasks`、`/steps`、`action_executed.detail`：已成立
- 多维表 `RPA执行证据台账`：已成立

## 固定最终样本
- `orig_task_id = TASK-20260423-0D44C4`
- `confirm_task_id = TASK-20260423-28025F`
- `record_id = recvhB4g3W1690`
- 证据文件：
  - `tmp/yingdao_bridge/outbox/TASK-20260423-28025F.output.json`
  - `/mnt/z/yingdao_bridge/evidence/TASK-20260423-28025F-runtime-result.json`
  - `/mnt/z/yingdao_bridge/done/TASK-20260423-28025F.done.json`

## 必须保持的步骤口径
`/steps` 至少包含：
- `controlled_write_started`
- `controlled_write_succeeded`
- `action_executed`
- `result_replied`
- `bitable_write_started`
- `bitable_write_succeeded`

## 当前禁止事项
- 不改业务代码
- 不补测试
- 不重跑功能链路
- 不扩第二动作
- 不扩 failure 分支
- 不切 PostgreSQL

## 后移项（保持不变）
- PostgreSQL 回归继续后移
- failure 分支继续后移
- `lark_oapi` 全链路治理继续后移
- SQLite 继续作为首验收边界