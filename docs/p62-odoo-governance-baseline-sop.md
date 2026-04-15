# P6.2 SOP：Odoo `warehouse.adjust_inventory` 治理复制基线与门禁前置输出

> 范围锁定：本轮只覆盖 Odoo 高风险写动作 `warehouse.adjust_inventory`。不扩动作、不扩平台、不重写 confirm、不进入 P6.3。

## 1) 本轮落地内容

- 固化 `action_executed.detail` 的最小治理字段集合，并覆盖三条路径：
  - 成功路径（confirm 放行 + 写后核验通过）
  - 阻断路径（confirm 上下文校验失败）
  - verify 失败路径（写后核验失败）
- 新增最小统计脚本：`script/p62_odoo_adjust_inventory_governance_summary.py`
- 新增 P6.2 回归测试资产，确保字段口径和统计口径不回归
- 第二轮补充：新增最小门禁前置判定输出（`gate_status / gate_reason / risk_flags / summary_counts`）

## 2) 最小治理字段集合（硬检查项）

围绕 `warehouse.adjust_inventory`，`action_executed.detail` 至少检查这些键值：

- `provider_id`
- `capability`
- `execution_mode`
- `confirm_backend`
- `operation_result`
- `verify_passed`
- `verify_reason`
- `failure_layer`
- `target_task_id`
- `confirm_task_id`
- `original_update_task_id`
- `readiness_status`
- `endpoint_profile`
- `session_injection_mode`

## 3) 三条路径如何取证

### 3.1 成功路径（写后核验通过）

看确认任务 `/api/v1/tasks/{confirm_task_id}/steps` 的 `action_executed.detail`：

- `operation_result=write_adjust_inventory`
- `verify_passed=True`
- `failure_layer=`（空）
- `confirm_backend=internal_sandbox`
- `provider_id=odoo`
- `capability=warehouse.adjust_inventory`
- `target_task_id / confirm_task_id / original_update_task_id` 三个关联字段齐全

### 3.2 阻断路径（confirm 阻断）

看确认任务 `/steps`：

- `operation_result=confirm_blocked_noop`
- `failure_layer` 在以下口径之一：
  - `confirm_context_missing`
  - `confirm_context_invalid_json`
  - `confirm_context_invalid_shape`
  - `confirm_context_incomplete`
- `verify_passed=False`
- `verify_reason` 与阻断层级一致

### 3.3 verify 失败路径（写后核验失败）

看确认任务 `/steps`：

- `operation_result=write_adjust_inventory_verify_failed`
- `failure_layer=verify_failed`
- `verify_passed=False`
- `verify_reason` 包含核验失败原因（如 `forced_verify_failure ...` 或 mismatch 说明）

## 4) 最小统计口径（P6.2）

脚本：`python3 script/p62_odoo_adjust_inventory_governance_summary.py --base-url http://127.0.0.1:8000`

输出字段：

- `initiated_high_risk_tasks`：已发起高风险任务数（`[warehouse.adjust_inventory]`）
- `awaiting_confirmation_count`：当前待确认任务数
- `confirm_released_count`：confirm 已放行进入受控写链次数
- `confirm_blocked_count`：confirm 阻断次数（`confirm_blocked_noop`）
- `verify_pass_count`：写后核验通过数
- `verify_fail_count`：写后核验失败数
- `block_reason_distribution`：阻断原因分布
- `verify_reason_distribution`：核验失败原因分布

## 5) 最小门禁前置表达（P6.3 前置）

本轮固定的阻断/失败表达：

- 缺 `risk_context`：`failure_layer=confirm_context_missing`
- JSON 非法：`failure_layer=confirm_context_invalid_json`
- 缺关键字段：`failure_layer=confirm_context_incomplete`
- 写后核验失败：`operation_result=write_adjust_inventory_verify_failed` + `failure_layer=verify_failed`
- readiness 不满足（若发生）通过 `readiness_status` 与 `verify_reason/failure_layer` 联合取证，不新增独立系统

## 6) verify 失败样本的稳定构造

为避免随机失败，本轮引入受控样本开关（仅测试样板链使用）：

- 在目标任务 `risk_context` 中设置：`"force_verify_fail": true`
- confirm 执行后会稳定产生：
  - `operation_result=write_adjust_inventory_verify_failed`
  - `failure_layer=verify_failed`
  - `verify_passed=False`
  - `verify_reason=forced_verify_failure ...`

## 7) 手动复验步骤

1. 跑定向测试：
   - `pytest -q tests/test_p61_odoo_adjust_inventory_flow.py`
   - `pytest -q tests/test_p62_odoo_adjust_inventory_governance_summary.py`
2. 启动服务后执行脚本：
   - `python3 script/p62_odoo_adjust_inventory_governance_summary.py --base-url http://127.0.0.1:8000`
   - `python3 script/p62_odoo_adjust_inventory_governance_summary.py --base-url http://127.0.0.1:8000 --with-gate`
3. 抽样一个成功/阻断/verify失败的确认任务，查看 `/tasks/{id}/steps` 的 `action_executed.detail` 是否满足第 2、3 节。

## 8) 最小审计清单（交接用）

- 成功路径：`write_adjust_inventory + verify_passed=True`
- 阻断路径：`confirm_blocked_noop + failure_layer=confirm_context_*`
- verify 失败：`write_adjust_inventory_verify_failed + failure_layer=verify_failed`
- 三类路径均具备关联字段：
  - `target_task_id`
  - `confirm_task_id`
  - `original_update_task_id`
- 统计脚本输出 6 个核心计数字段且测试覆盖通过

## 9) P6.2 第二轮：最小门禁前置判定输出

> 说明：这一层是 P6.3 之前的“前置判定层”，不是完整门禁系统。

### 9.1 输出入口

- 命令：`python3 script/p62_odoo_adjust_inventory_governance_summary.py --with-gate`
- 单样本回放：`python3 script/p62_odoo_adjust_inventory_governance_summary.py --task-id <TASK_ID>`
- 输出结构：
  - `summary`：第一轮最小统计口径
  - `gate_precheck`：第二轮最小门禁前置判定输出

### 9.2 `gate_precheck` 字段含义

- `gate_status`：`pass | warn | block`
- `gate_reason`：当前主要判定理由（可复验）
- `allow_adjust_inventory_flow`：是否允许进入当前样板链
- `has_blocking_risk`：是否存在阻断级风险
- `risk_flags`：风险标签列表（如 `confirm_blocked_present`、`verify_fail_present`、`sample_insufficient`）
- `summary_counts`：门禁消费的统计概览
- `latest_samples`：最近样本摘要（便于快速抽样核验）

### 9.2.1 `--task-id` 单样本回放输出

单样本输出（稳定字段）：

- `task_id`
- `capability`
- `provider_id`
- `operation_result`
- `verify_passed`
- `verify_reason`
- `failure_layer`
- `confirm_backend`
- `gate_status`
- `gate_reason`
- `risk_flags`
- `summary_bucket`
- `explain`

解读方式：

- `gate_status/gate_reason/risk_flags`：该样本按当前 gate 规则映射后的最小解释
- `summary_bucket`：该样本在总览统计中的归类口径（例如 `confirm_blocked_count` / `verify_fail_count` / `verify_pass_count`）
- `explain`：用于人工复核映射依据（`operation_result/failure_layer/verify_reason`）

### 9.3 最小规则（固定口径）

- 无异常时：`gate_status=pass`，`gate_reason=no_risk_signal`
- 样本不足（`initiated_high_risk_tasks < 3`）：`gate_status=warn`
- 出现 confirm 阻断（`confirm_blocked_count > 0`）：`gate_status=warn`，`gate_reason=confirm_blocked_present:<primary_reason>`
- 出现 verify 失败（`verify_fail_count > 0`）：`gate_status=block`，`gate_reason=verify_fail_present:<primary_reason>`
- 如出现统计矛盾（例如 `awaiting_confirmation_count > initiated_high_risk_tasks`）：`gate_status=warn`

#### gate_reason 主原因选择优先级（第三轮稳定化）

固定优先级（从高到低）：

1. `verify_fail_present`
2. `confirm_blocked_present`
3. `summary_counts_anomaly`
4. `sample_insufficient`
5. `no_risk_signal`

说明：

- 不使用字典序作为主原因选择依据。
- 多风险并存时，永远按上述优先级选主原因。
- 同类原因内部：
  - `confirm_blocked_present` 的 `primary_reason` 按固定层级优先：  
    `confirm_context_missing` > `confirm_context_invalid_json` > `confirm_context_invalid_shape` > `confirm_context_incomplete` > `provider_readiness_failed` > 其它
  - `verify_fail_present` 的 `primary_reason` 按固定层级优先：  
    `verify_failed` > `provider_readiness_failed` > 其它

#### failure_layer → gate 输出映射（第三轮稳定化）

confirm 阻断类（`gate_status=warn`，`gate_reason=confirm_blocked_present:<failure_layer>`）：

- `confirm_context_missing` → `risk_flags` 包含 `confirm_blocked_present` + `confirm_context_missing_present`
- `confirm_context_invalid_json` → `risk_flags` 包含 `confirm_blocked_present` + `confirm_context_invalid_json_present`
- `confirm_context_invalid_shape` → `risk_flags` 包含 `confirm_blocked_present` + `confirm_context_invalid_shape_present`
- `confirm_context_incomplete` → `risk_flags` 包含 `confirm_blocked_present` + `confirm_context_incomplete_present`
- `provider_readiness_failed`（若出现）→ `risk_flags` 包含 `confirm_blocked_present` + `readiness_failure_present`

verify 失败类（`gate_status=block`，`gate_reason=verify_fail_present:<failure_layer>`）：

- `verify_failed` → `risk_flags` 包含 `verify_fail_present` + `verify_failed_present`
- `provider_readiness_failed`（若出现）→ `risk_flags` 包含 `verify_fail_present` + `readiness_failure_present`

### 9.4 三类典型结果解释

- `pass`：当前样板链无显著风险信号，可继续按 SOP 运行
- `warn`：存在可观察风险信号或样本不足，需人工复核样本
- `block`：存在 verify 失败信号，当前样板链应阻断并先定位原因

多风险同时出现时解释：

- 先看 `gate_reason`（主原因，已按固定优先级选择）
- 再看 `risk_flags`（列出所有并发风险，不丢信息）

### 9.5 单样本回放与总览的一致性关系

- 单样本回放负责解释“这 1 条样本为什么被判成某种 gate 结果”。
- 总览 `gate_precheck` 负责解释“当前批量样本整体应判成 pass/warn/block”。
- 两者使用同一套规则族：
  - `confirm_blocked_noop` -> confirm 阻断口径
  - `write_adjust_inventory_verify_failed / verify_failed` -> verify 失败口径
  - `write_adjust_inventory + verify_passed=True` -> 通过口径

说明：这仍是 P6.2 的前置判定层，不是 P6.3 的全量门禁系统。
