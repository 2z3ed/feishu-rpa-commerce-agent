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

### 11) P5.3 第三轮：历史样本兼容读取（固定优先级）

统一优先级（不可交换）：

1. `parsed_result`（new schema 单一事实源）
2. `action_executed.detail`
3. `result_summary / error_message`
4. `unknown`

执行原则：

- 新样本优先按 `parsed_result` 读取，不回退到旧口径覆盖。
- 旧样本只做兼容解读，不回填数据库，不补造历史字段。
- 证据不足直接归 `unknown`，并输出稳定 `unknown_reason`。

`unknown_reason` 固定枚举（脚本与回放共用）：

- `task_not_found`
- `steps_not_found`
- `missing_parsed_result_and_no_mappable_label`
- `detail_missing_failure_hints`
- `summary_message_not_classifiable`

### 12) 单条治理样本回放（`--task-id`）

脚本：`script/p53_woo_write_governance_summary.py`

运行：

```bash
source venv/bin/activate
python script/p53_woo_write_governance_summary.py \
  --base-url "http://127.0.0.1:8000" \
  --task-id "TASK-XXXX"
```

固定输出字段（最小审计集）：

- `confirm_task_id`
- `target_task_id`
- `original_update_task_id`
- `operation_result`
- `verify_passed`
- `verify_reason`
- `failure_layer`
- `governance_event_type`
- `source_mode`
- `unknown_reason`

说明：`unknown_reason` 无原因时也输出空字符串，不允许缺字段。

### 13) governance_event_type 与 failure_layer 的关系（固定）

`governance_event_type` 固定枚举：

- `confirm_succeeded`
- `confirm_target_already_consumed`
- `confirm_target_invalid`
- `other_failed`
- `unknown`

关系说明：

- `failure_layer` 是失败层级原始标签（更贴近执行侧）。
- `governance_event_type` 是治理统计分桶（更贴近审计看板）。
- 成功样本通常 `failure_layer=""`，但 `governance_event_type=confirm_succeeded`。
- 失败样本优先使用 `failure_layer` 映射治理分桶；无可靠证据时归 `unknown`，避免误导审计。

### 14) task_id 复盘顺序（P5.3 固化）

基于单条 `confirm_task_id` 复盘时按以下顺序：

1. **环境优先**：先看 readiness / 会话 /依赖连通，排除环境噪声。
2. **治理其次**：看 `source_mode`、`governance_event_type`、`unknown_reason`。
3. **写流最后**：只在治理放行后再看写后核验与页面执行细节。

`unknown` 解读原则：

- `unknown` 不是失败重分类，而是“证据不足，不做过度推断”的保守结论。
- 若样本仅有自由文本且无可映射标签，必须保持 `unknown`，不为降低 unknown 比例而强行归类。

### 15) P5.4 发布门禁脚本（最小工程门禁）

脚本：`script/p54_woo_write_gate_check.py`

用途（只编排与判定）：

- 调用关键回归测试（默认：`tests/test_p53_woo_write_governance_summary.py`）
- 调用 `p53` 聚合模式
- 调用 `p53 --task-id` 回放模式
- 汇总并输出 `status` / `blocking_failures` / `warnings`

说明：门禁脚本不复写治理解析，不复写 `source_mode` / `unknown_reason` 判定，不复写 confirm-only 过滤；这些逻辑统一复用 `p53` 脚本输出。

### 16) P5.4 固定门禁阈值与口径（脚本/文档一致）

固定规则（与 `script/p54_woo_write_gate_check.py` 保持一致）：

- `other_failed_confirms > 0`：**阻断**
- `unknown_ratio = unknown_confirms / total_confirm_attempts`
  - `unknown_ratio > 0.2`：**阻断**
  - `0 < unknown_ratio <= 0.2`：**警告**
- `blocked_repeat_confirms == 0`：**警告**（覆盖不足提示，不阻断）
- `invalid_target_confirms > 0`：**警告**（可见但不阻断）

输出分层（固定）：

- `blocking_failures`：必须阻断发布
- `warnings`：允许人工复核后放行

### 17) 发布前最小执行清单（P5.4）

1. 运行门禁脚本（示例）：

```bash
source venv/bin/activate
python script/p54_woo_write_gate_check.py \
  --base-url "http://127.0.0.1:8000" \
  --limit 80 \
  --task-prefix "TASK-" \
  --recent-limit 20 \
  --replay-task-id "TASK-NEW-SAMPLE" \
  --replay-task-id "TASK-LEGACY-SAMPLE"
```

2. 判定：
   - `status=fail`：阻断
   - `status=pass_with_warnings`：按 warning 做人工复核
   - `status=pass`：通过

3. 人工复核最小流程（warning 场景）：
   - 按 warning 里的 `task_id` 调 `p53 --task-id` 回放
   - 判断是否是预期样本（如 invalid target 测试噪音）
   - 记录复核结论后再决定放行

### 18) P5.4 第二轮：门禁命中后的复核提示输出（固定）

`p54` 门禁输出新增 `review_hints`，用于把“命中规则”直接连接到“下一步复核动作”。

`review_hints` 固定字段：

- `rule_name`
- `recommended_action`
- `recommended_entry`
- `recommended_task_ids`
- `next_step`

固定枚举：

- `recommended_entry` 只能是：
  - `p53_replay_task_id`
  - `tasks_detail`
  - `steps_action_executed`
- `recommended_action` 只能是：
  - `block`
  - `review`
  - `allow`

说明：`p54` 只编排复核提示，不复写 `p53` 的治理解析逻辑；`governance_event_type/source_mode/unknown_reason/confirm-only` 口径全部复用 `p53` 输出。

### 19) recommended_task_ids 选择规则（固定）

- 来源统一：`p53` 聚合输出的 `recent_governance_events`。
- 选择优先级：优先选“最近命中的相关样本”（按 `recent_governance_events` 顺序取）。
- warning 与 blocking 使用同一选择规则，不分叉。
- 返回上限：最多少量样本（当前门禁固定最多 3 条）。
- 没有可推荐样本时：返回空数组 `[]`，不允许缺字段。

### 20) warning/fail 复核与放行最小规则（P5.4 第二轮）

- `other_failed_confirms_gt_0`：
  - `recommended_action=block`
  - 必须先回放对应 `task_id`，未定责前不得放行
- `unknown_ratio_gt_threshold`：
  - `recommended_action=block`
  - 必须先回放 unknown 样本并确认原因，再决定是否恢复放行
- `unknown_confirms_present`（低比例）：
  - `recommended_action=review`
  - 抽样回放后可人工复核放行
- `blocked_repeat_confirms_eq_0`：
  - `recommended_action=review`
  - 需补充重复 confirm 覆盖样本后再放行
- `invalid_target_confirms_present`：
  - `recommended_action=allow`
  - 回放确认属于预期噪音后可放行

### 21) P5.4 第三轮：门禁结果留痕结构（固定）

门禁脚本单次运行结果必须稳定包含（同一对象、同一口径）：

- `gate_run_at`
- `gate_status`
- `blocking_failures`
- `warnings`
- `review_hints`
- `checked_tests`
- `checked_scripts`
- `sample_task_ids`

说明：

- `gate_status` 与 `status` 使用同一事实值，不允许出现双口径分叉。
- `stdout` 输出与 `--output-json` 落盘结构必须完全一致。
- 不额外再造第二份“类似结果对象”。

### 22) 人工复核记录模板（可复制即用，固定结构）

复核模板固定字段（全部必须存在）：

- `gate_run_at`
- `gate_status`
- `rule_name`
- `severity`
- `recommended_action`
- `recommended_entry`
- `reviewed_task_ids`
- `replay_result_summary`
- `final_decision`
- `reviewer`
- `note`

要求：

- 无值时使用空字符串 `""` 或空数组 `[]`，不允许缺字段。
- 仅提供模板与预填值，不做交互式填写、不做审批流、不做自动写回。

### 23) 门禁结果与复核记录最小关联键（固定）

固定最小关联键（仅这三项）：

- `gate_run_at`
- `rule_name`
- `reviewed_task_ids`

用途：

- `gate_run_at`：定位到哪次门禁运行；
- `rule_name`：定位到命中的哪条规则；
- `reviewed_task_ids`：定位复核过哪些样本。

通过这三个键即可把“门禁结果”与“复核记录”稳定对齐，避免依赖人工记忆。
