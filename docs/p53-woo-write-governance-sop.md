## P5.3 Woo 高风险写链治理 SOP

本 SOP 只覆盖 `product.update_price` + `system.confirm_task` 的治理验收，不扩平台、不扩动作。

### 1) 治理目标（固定）

- `system.confirm_task` 对同一 `target_task_id` 只能消费一次确认。
- 重复 confirm 必须被阻止，且返回可审计字段（不能只返回一句“已处理”）。
- 审计字段在 `/tasks`、`/steps`、`result_summary`、bitable（若启用）里口径一致。

### 2) 单一事实源（重复 confirm 拦截）

重复 confirm 是否拦截只看 **原始 update 任务状态**：

- `status == awaiting_confirmation`：允许本次 confirm 放行
- `status != awaiting_confirmation`：阻止重复写（或无效确认）

说明：不依赖 steps 猜测，不新增第二套确认机制。

### 3) 三类治理样本回归

#### A. 正常 confirm 成功闭环

1. 发起 `product.update_price`，任务应进入 `awaiting_confirmation`
2. 发起第一次 `system.confirm_task`
3. 验证：
   - confirm 任务 `status=succeeded`
   - 原始 update 任务最终 `status=succeeded`
   - `action_executed.detail` 可见 `old_price/new_price/post_save_price/verify_*`

#### B. 同一 target 第二次 confirm 被拦截

1. 对同一个 `target_task_id` 再发一次 confirm
2. 验证：
   - 第二次 confirm 任务 `status=failed`
   - `failure_layer=confirm_target_already_consumed`
   - `operation_result=confirm_blocked_noop`
   - 审计字段齐全（见第 4 节）
   - 原始 update 任务的价格结果不再发生二次写入

#### C. confirm 无效 target 安全失败

1. confirm 一个不存在的 task_id
2. 验证：
   - `status=failed`
   - `failure_layer=confirm_target_invalid`
   - 无写执行副作用

### 4) 重复 confirm 拦截的可审计字段（固定）

第二次 confirm（或被阻止样本）至少要稳定可读：

- `failure_layer`
- `target_task_id`
- `original_update_task_id`
- `operation_result`
- `verify_passed`
- `verify_reason`

这些字段允许空语义，但不允许缺字段。

### 5) 取证点（固定）

- `/api/v1/tasks/{confirm_task_id}`
  - `status`
  - `target_task_id`
  - `result_summary`
  - `error_message`
- `/api/v1/tasks/{confirm_task_id}/steps`
  - `action_executed.detail` 中：
    - `failure_layer`
    - `operation_result`
    - `verify_passed`
    - `verify_reason`
    - `target_task_id`
    - `original_update_task_id`
    - `confirm_task_id`

若启用 bitable，检查同一任务的 `task_id/target_task_id/status/result_summary/error_message` 与 tasks 口径一致。

### 6) 成功标准

- 三类治理样本均可复验；
- 重复 confirm 明确被阻止，且有可审计字段；
- 治理补强不破坏已通过的写链成功路径语义。

### 7) 失败标准

- 重复 confirm 仍触发二次写执行；
- 重复 confirm 被拦截但缺少 `failure_layer` 等关键审计字段；
- `/tasks` 与 `/steps` 对同一确认任务给出冲突结论。

### 8) 排查顺序

1. 先看 `target_task_id` 指向是否正确
2. 再看原始 update 任务当时状态是否为 `awaiting_confirmation`
3. 看 confirm 任务 `/steps.action_executed.detail` 的 `failure_layer/operation_result/verify_reason`
4. 最后对照 `result_summary/error_message` 是否同标签映射

### 9) 治理聚合脚本（P5.3 第二轮）

脚本：`script/p53_woo_write_governance_summary.py`

运行：

```bash
source venv/bin/activate
python script/p53_woo_write_governance_summary.py \
  --base-url "http://127.0.0.1:8000" \
  --limit 80 \
  --task-prefix "TASK-" \
  --recent-limit 20
```

固定输出：

- `total_confirm_attempts`
- `successful_confirms`
- `blocked_repeat_confirms`
- `invalid_target_confirms`
- `other_failed_confirms`
- `governance_distribution`
- `recent_governance_events`

统计口径（固定）：

- 只统计 confirm 样本（`intent_text` 以 `确认执行` 开头）
- 不混入 `product.update_price` 样本，避免 confirm 指标失真
- `recent_governance_events` 至少包含：
  - `task_id`
  - `status`
  - `failure_layer`
  - `operation_result`
  - `verify_passed`
  - `verify_reason`
  - `target_task_id`
  - `original_update_task_id`
  - `confirm_task_id`

### 10) 最近治理分布怎么读（固定）

按 `governance_distribution` 先看：

1. `confirm_succeeded`：首次 confirm 正常放行
2. `confirm_target_already_consumed`：重复 confirm 治理拦截
3. `confirm_target_invalid`：无效 target 安全失败
4. `other_failed`：其余失败，进入排查

归因优先级：

1. **环境类**：readiness、会话、依赖不可用
2. **治理类**：重复 confirm / target 无效 / 样本口径不一致
3. **写流类**：页面写入与写后核验失败（非治理拦截）
