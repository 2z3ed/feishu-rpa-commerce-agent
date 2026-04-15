# P6.1 SOP：Odoo 最小高风险写链闭环（`warehouse.adjust_inventory`）

> 范围边界（锁死）：只做 Odoo 一条高风险写动作 `warehouse.adjust_inventory` 的最小闭环；不扩第二写动作、不动 Woo 已收口主线、不做真实生产写、不做真实登录自动化、不做大重构。

## 1) 启动方式（本地）

在仓库根目录执行：

```bash
export USE_SQLITE=true
export ENABLE_INTERNAL_SANDBOX_API=true
export APP_HOST=0.0.0.0
export APP_PORT=8000
```

启动 API（FastAPI）：

```bash
uvicorn app.main:app --host "$APP_HOST" --port "$APP_PORT"
```

## 2) readiness 检查（必须）

```bash
curl -s "http://127.0.0.1:8000/api/v1/internal/readiness/unified-provider?provider=odoo&capability=warehouse.adjust_inventory"
```

预期要点：
- `ready=true`
- `provider_name=odoo`
- `capability=warehouse.adjust_inventory`

## 3) 手动样本脚本（固定入口）

```bash
export USE_SQLITE=true
export ENABLE_INTERNAL_SANDBOX_API=true
python3 scripts/p61_odoo_adjust_inventory_sample.py --sku A001 --delta 5 --base-url http://127.0.0.1:8000
```

脚本 stdout 会输出：
- 原始任务 `orig_task_id`
- 确认任务 `confirm_task_id`
- 以及三条可取证路径：
  - `GET /api/v1/tasks/{orig_task_id}`
  - `GET /api/v1/tasks/{confirm_task_id}`
  - `GET /api/v1/tasks/{confirm_task_id}/steps`

## 4) 复验检查项（/tasks 与 /steps）

### 4.1 原始任务 `/api/v1/tasks/{orig_task_id}`

预期要点：
- **先**进入 `awaiting_confirmation`（在确认前）
- 确认执行后，原始任务状态变为 `succeeded`（核验通过）或 `failed`（核验失败）
- `result_summary` 以 `[warehouse.adjust_inventory]` 开头
- summary 至少包含：
  - `SKU:`
  - `写前库存：`
  - `调整量(delta)：`
  - `目标库存：`
  - `任务号：`
  - `请回复：确认执行 <task_id>`

### 4.2 确认任务 `/api/v1/tasks/{confirm_task_id}`

预期要点：
- `status=succeeded`（确认任务自身执行成功）
- `target_task_id` 指向 `orig_task_id`

### 4.3 确认任务 `/api/v1/tasks/{confirm_task_id}/steps`

预期要点：
- 存在 `step_code=action_executed`
- `detail` 至少包含并可读：
  - `provider_id=odoo`
  - `capability=warehouse.adjust_inventory`
  - `confirm_backend=internal_sandbox`（表示 confirm 放行后的受控写链）
  - `operation_result=...`
  - `verify_passed=true|false`
  - `verify_reason=...`
  - `target_task_id=<orig_task_id>`
  - `confirm_task_id=<confirm_task_id>`

## 5) 失败排查顺序（只看这几个入口）

1. **readiness 不通过**：先跑 unified-provider readiness，确认 `capability=warehouse.adjust_inventory` 变为 ready
2. **原始任务不进入 awaiting_confirmation**：看 `/api/v1/tasks/{orig_task_id}` 的 `status/result_summary`
3. **confirm 未执行写链**：看 `/api/v1/tasks/{confirm_task_id}/steps` 的 `action_executed.detail` 是否包含 `operation_result/verify_*`
4. **核验失败**：看 `verify_passed/verify_reason/post_inventory` 等字段

## 6) 负例：目标任务缺少 risk_context（必须明确失败）

目标：证明 confirm **不会**回退到“解析 summary 文案”。

### 6.1 现象（预期）
- confirm 任务 `status=failed`
- `/api/v1/tasks/{confirm_task_id}/steps` 的 `action_executed.detail` 至少包含：
  - `failure_layer=confirm_context_missing`
  - `operation_result=confirm_blocked_noop`
  - `verify_passed=False`
  - `verify_reason=confirm_context_missing`
  - `capability=warehouse.adjust_inventory`
  - `target_task_id=<orig_task_id>`

### 6.2 优先排查
- 先看目标任务 `/steps` 是否存在 `step_code=risk_context` 且 `detail` 为 JSON
- 若缺失，属于预期阻断（confirm 必须失败而非回退解析）

## 7) 负例：risk_context JSON 非法 / 缺关键字段（必须明确失败）

目标：证明 confirm **只接受合法且字段完整** 的结构化上下文。

### 7.1 risk_context JSON 非法（预期）
- confirm 任务 `status=failed`
- `/steps action_executed.detail` 至少包含：
  - `failure_layer=confirm_context_invalid_json`
  - `operation_result=confirm_blocked_noop`
  - `verify_passed=False`
  - `verify_reason=confirm_context_invalid_json`
  - `capability=warehouse.adjust_inventory`

### 7.2 risk_context 缺关键字段（预期）
- confirm 任务 `status=failed`
- `/steps action_executed.detail` 至少包含：
  - `failure_layer=confirm_context_incomplete`
  - `verify_reason=confirm_context_incomplete:missing=...`（列出缺的字段，比如 `sku,delta,target_inventory`）
  - `operation_result=confirm_blocked_noop`
  - `verify_passed=False`
  - `capability=warehouse.adjust_inventory`

### 7.3 优先排查
- 目标任务 `/steps`：
  - 找 `step_code=risk_context`
  - 检查 `detail` 是否为 **JSON dict**
  - 检查是否包含关键字段：`provider_id/capability/sku/delta/target_inventory`

