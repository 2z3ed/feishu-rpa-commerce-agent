# P9-E 老板演示 SOP

## 一、演示目标

让老板在飞书里直接体验这条最小闭环：

发命令
→ 系统接单
→ 系统要求确认
→ 用户确认执行
→ RPA 真执行
→ 飞书看到最终结果
→ 多维表看到对应记录
→ 后台 task 可查

## 二、演示固定样本

- 动作：warehouse.adjust_inventory
- SKU：A001
- old_inventory：100
- target_inventory：105
- orig_task_id：`TASK-20260423-0D44C4`
- confirm_task_id：`TASK-20260423-28025F`
- bitable record_id：`recvhB4g3W1690`

飞书命令固定使用：

1. 把 A001 的库存改到 105
2. 确认执行 TASK-xxxx

## 三、演示前准备

### 1. 启动 API
确认主系统已启动。

### 2. 启动 worker
确认 celery worker 已启动并可消费。

### 3. 启动飞书 listener
确认飞书侧消息能稳定进入主系统。

### 4. 启动 redis
确认 broker 可用。

### 5. 启动 nonprod stub
确认：
- 127.0.0.1:18081 可访问
- /login 可返回 200
- /admin/inventory/adjust 可访问

### 6. 启动 shadowbot / bridge 运行环境
确认 real-runtime 可用。

### 7. 确认 SQLite / bitable 配置正常
确认：
- SQLite 可写
- RPA执行证据台账 已存在
- FEISHU_RPA_EVIDENCE_TABLE_ID 已配置

## 四、演示步骤

### 第一步：在飞书里发命令
发送：

把 A001 的库存改到 105

### 第二步：展示系统已接收 / 待确认
预期飞书返回至少包含：

- 已接收任务
- task_id
- sku
- target_inventory
- 请回复：确认执行 TASK-xxxx

### 第三步：在飞书里发送确认命令
发送：

确认执行 TASK-xxxx

### 第四步：展示飞书执行中 / 最终结果
预期飞书返回至少包含：

- 执行开始
- 执行成功
- task_id
- SKU
- 旧库存
- 目标库存
- 新库存
- 核验结果

### 第五步：打开飞书多维表
展示：

RPA执行证据台账 中对应 record

重点看这些字段：

- task_id
- run_id
- sku
- old_inventory
- target_inventory
- new_inventory
- verify_passed
- verify_reason
- result_summary

### 第六步：如需补充，打开后台任务接口
展示：

- /api/v1/tasks/{task_id}
- /api/v1/tasks/{task_id}/steps

用于说明后台留痕完整。

## 五、演示成功标准

只要满足以下几点，就算老板演示闭环成立：

1. 飞书命令能创建任务
2. 飞书确认能放行真实执行
3. real-runtime 能完成 A001 100 -> 105
4. 飞书里能看到最终结果文本
5. 多维表里有对应 RPA执行证据台账记录
6. `/tasks` 与 `/steps` 仍可查

## 六、冻结样本复盘（收口口径）

本阶段对外交付固定引用以下样本：

- `orig_task_id = TASK-20260423-0D44C4`
- `confirm_task_id = TASK-20260423-28025F`
- `baseline = A001 100 -> 105`
- 真实飞书 `om_*` 消息送达：已通过
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