# P9-E 验收清单

## 一、范围清单

- [x] 只做 warehouse.adjust_inventory
- [x] 只做 A001 100 -> 105
- [x] 只做飞书文本回执
- [x] 只做 RPA执行证据台账
- [x] 只做 SQLite 首验收
- [x] 未扩第二动作
- [x] 未切 PostgreSQL
- [x] 未扩 failure 大收口

## 二、飞书前台验收

### 命令入口
- [x] 飞书私聊命令可进入主系统
- [x] 支持“把 A001 的库存改到 105”
- [x] 支持“调整 A001 库存到 105”

### 待确认
- [x] 飞书能回“已接收任务”
- [x] 飞书能回“等待确认”
- [x] 文本中包含 task_id
- [x] 文本中包含 sku / target_inventory

### 确认执行
- [x] 支持“确认执行 TASK-xxxx”
- [x] 能命中现有 system.confirm_task 主链
- [x] 原始任务 / 确认任务关系可追踪

### 最终结果
- [x] 飞书能回成功结果文本
- [x] 成功文本中有 task_id
- [x] 成功文本中有 SKU
- [x] 成功文本中有旧库存 / 目标库存 / 新库存
- [x] 成功文本中有 verify_passed 或核验摘要

## 三、后台链路验收

- [x] real-runtime 真执行通过
- [x] A001 从 100 -> 105
- [x] task_records 可查
- [x] task_steps 可查
- [x] action_executed.detail 可查
- [x] `/api/v1/tasks/{task_id}` 可查
- [x] `/api/v1/tasks/{task_id}/steps` 可查

## 四、多维表验收

- [x] RPA执行证据台账有对应记录
- [x] task_id 一致
- [x] run_id 一致
- [x] sku 一致
- [x] old_inventory 一致
- [x] target_inventory 一致
- [x] new_inventory 一致
- [x] verify_passed 一致
- [x] verify_reason 一致
- [x] result_summary 一致

## 五、边界验收

- [x] 不破坏 SQLite 真相源边界
- [x] bitable 写失败不阻塞主链 success
- [x] 未改 ShadowBot 主执行逻辑
- [x] 未引入飞书卡片完整版依赖

## 六、冻结样本（收口引用）

- `orig_task_id = TASK-20260423-0D44C4`
- `confirm_task_id = TASK-20260423-28025F`
- `baseline = A001 100 -> 105`
- 真实飞书 `om_*` 消息已通过
- `/steps` 已出现：
  - `controlled_write_started`
  - `controlled_write_succeeded`
  - `action_executed`
  - `result_replied`
  - `bitable_write_started`
  - `bitable_write_succeeded`
- 多维表 `record_id = recvhB4g3W1690`
- 证据文件：
  - `tmp/yingdao_bridge/outbox/TASK-20260423-28025F.output.json`
  - `/mnt/z/yingdao_bridge/evidence/TASK-20260423-28025F-runtime-result.json`
  - `/mnt/z/yingdao_bridge/done/TASK-20260423-28025F.done.json`