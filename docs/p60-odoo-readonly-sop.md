# P6.0 第一轮 SOP：Odoo readonly 主线复制验证（`warehouse.query_inventory`）

> 范围边界（锁死）：只做 Odoo readonly 一条主线 `warehouse.query_inventory` 的复制验证；不做写链、不扩第二动作、不动 Woo 已通过主线、不重构 execute mode、不做真实登录/真实生产写。

## 1) 启动方式

### 1.1 基本环境变量（本地）

在仓库根目录执行：

```bash
export USE_SQLITE=true
export ENABLE_INTERNAL_SANDBOX_API=true
export APP_HOST=0.0.0.0
export APP_PORT=8000
```

### 1.2 启动 API（FastAPI）

```bash
uvicorn app.main:app --host "$APP_HOST" --port "$APP_PORT"
```

> 说明：本轮验收不要求启动飞书长连接；我们使用脚本同步跑 ingress 主链，再用 API 的 `/tasks` 与 `/steps` 拉取证据。

## 2) readiness 检查命令（必须）

```bash
curl -s "http://127.0.0.1:8000/api/v1/internal/readiness/unified-provider?provider=odoo&capability=warehouse.query_inventory"
```

预期要点：
- `ready=true`
- `provider_id=odoo`
- `capability=warehouse.query_inventory`

## 3) Odoo readonly 样本触发方式（固定）

### 3.1 运行 P6 样本脚本（推荐）

```bash
export USE_SQLITE=true
export ENABLE_INTERNAL_SANDBOX_API=true
python3 scripts/p60_odoo_readonly_sample.py --sku A001 --base-url http://127.0.0.1:8000
```

脚本 stdout 会输出：
- `task_id`
- 以及两条可取证路径：
  - `GET /api/v1/tasks/{task_id}`
  - `GET /api/v1/tasks/{task_id}/steps`

## 4) /tasks 与 /steps 的检查方式

```bash
TASK_ID="TASK-P60-ODOO-READONLY-SAMPLE-<timestamp>"
curl -s "http://127.0.0.1:8000/api/v1/tasks/${TASK_ID}"
curl -s "http://127.0.0.1:8000/api/v1/tasks/${TASK_ID}/steps"
```

### 4.1 `/api/v1/tasks/{task_id}` 预期要点

- `status` 为 `succeeded`
- `result_summary` 前缀包含 `[warehouse.query_inventory]`
- `result_summary` 关键字段稳定可读，至少包含：
  - `SKU: <sku>`
  - `商品：<string>`
  - `库存：<int>`
  - `平台：odoo`
  - `provider_id：odoo`
  - `capability：warehouse.query_inventory`

### 4.2 `/api/v1/tasks/{task_id}/steps` 预期要点

- 存在 `step_code=action_executed`
- `detail` 至少包含并稳定：
  - `execution_mode=api`
  - `provider_id=odoo`
  - `capability=warehouse.query_inventory`
  - `readiness_status=ready`
  - `endpoint_profile=<non-empty>`
  - `session_injection_mode=<non-empty>`

## 5) 本轮通过标准（P6.0 第一轮）

必须同时满足：
- 至少 1 条 Odoo readonly 样本成功（脚本成功退出，且 `/tasks`、`/steps` 可取证）
- 连续 2~3 次重复回归成功（每次都有不同 task_id）
- `result_summary` 稳定不漂（字段齐、格式一致、值合理）
- `action_executed.detail` 关键字段稳定不漂（字段名一致、非空、口径一致）

## 6) 失败排查顺序（只看这几个入口）

1. **readiness 不通过**：先跑 `GET /api/v1/internal/readiness/unified-provider`，看 `reason/reasons`
2. **脚本失败**：看脚本报错前缀 `[p60_acceptance_failed] ...`
3. **证据缺失**：
   - `/api/v1/tasks/{task_id}` 看 `status/result_summary/error_message`
   - `/api/v1/tasks/{task_id}/steps` 看 `action_executed.detail` 是否字段缺失/为空
   - 重点看 `execution_mode` 是否为 `api`（避免被旧 `mock` 口径误导）
4. **internal sandbox 关闭**：确认 `ENABLE_INTERNAL_SANDBOX_API=true`

