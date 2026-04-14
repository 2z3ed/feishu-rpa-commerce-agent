# P5.0 第二轮验收 SOP（多平台骨架收紧 + Woo 样板证据加固）

> 边界：只做 P5.0 第二轮收紧，不进入 P5.1；不新增平台；不扩 Odoo/Chatwoot 第二动作；不做真实生产写/真实登录/真实后台 DOM 适配。

## 1) docker compose 启动

在仓库根目录执行（按你本地 compose 文件为准）：

```bash
docker compose up -d
docker compose ps
```

## 2) API / worker / feishu 启动

### API（FastAPI）

```bash
export USE_SQLITE=true
export APP_HOST=0.0.0.0
export APP_PORT=8000
uvicorn app.main:app --host "$APP_HOST" --port "$APP_PORT"
```

### worker（Celery）

```bash
celery -A app.workers.celery_app worker -l info
```

### Feishu（如需事件入口）

> 第二轮验收主线不要求重做飞书入口；如要复验飞书入口请按项目既有方式启动（例如 `uvicorn` 同进程已包含 `feishu_events` 路由）。

## 3) unified readiness 检查命令

```bash
curl -s "http://127.0.0.1:8000/api/v1/internal/readiness/unified-provider?provider=woo&capability=product.query_sku_status" | jq
curl -s "http://127.0.0.1:8000/api/v1/internal/readiness/unified-provider?provider=odoo&capability=warehouse.query_inventory" | jq
curl -s "http://127.0.0.1:8000/api/v1/internal/readiness/unified-provider?provider=chatwoot&capability=customer.list_recent_conversations" | jq
```

## 4) Woo Round2 样板脚本运行命令（必须）

该脚本会生成固定格式 task_id：`TASK-P50-R2-MANUAL-WOO-SAMPLE-<timestamp>`

```bash
export USE_SQLITE=true
export ENABLE_INTERNAL_SANDBOX_API=true
python3 scripts/p50_round2_manual_woo_sample.py --sku A001
```

脚本 stdout 会打印：
- 生成的 `task_id`
- 以及两条检查路径：
  - `GET /api/v1/tasks/{task_id}`
  - `GET /api/v1/tasks/{task_id}/steps`

## 5) Odoo / Chatwoot 现有手动触发命令（第一轮能力复验）

> 仍使用自然语言触发方式（不扩动作）。

- **Odoo**：

```bash
# 文本里必须包含 odoo + 库存 + SKU
curl -s -X POST "http://127.0.0.1:8000/api/v1/feishu/events/debug-ingress" \
  -H "content-type: application/json" \
  -d '{"text":"查 Odoo 里 SKU A001 的库存"}' | jq
```

- **Chatwoot**：

```bash
curl -s -X POST "http://127.0.0.1:8000/api/v1/feishu/events/debug-ingress" \
  -H "content-type: application/json" \
  -d '{"text":"查 Chatwoot 最近 5 个会话"}' | jq
```

> 如果你环境没有 `debug-ingress`，请使用你现有的手动触发方式创建任务（例如 CLI/已有脚本/手工插入任务记录后走 worker）。第二轮验收不要求新增 debug API。

## 6) /api/v1/tasks/{task_id} 与 /steps 检查命令

```bash
TASK_ID="TASK-P50-R2-MANUAL-WOO-SAMPLE-<timestamp>"
curl -s "http://127.0.0.1:8000/api/v1/tasks/${TASK_ID}" | jq
curl -s "http://127.0.0.1:8000/api/v1/tasks/${TASK_ID}/steps" | jq
```

## 7) 本轮通过标准（P5.0 第二轮）

- **必须新增 1 条新的 Woo Round2 样板任务**，且在 `action_executed.detail` 中满足：
  - `provider_id=woo`
  - `readiness_status != n/a`
  - `endpoint_profile` 非空
  - `session_injection_mode` 非空
- **第一轮能力不回归**：
  - unified readiness 不回归
  - tasks list/detail/steps 不回归
  - action_executed.detail 固定字段不回归
  - Odoo/Chatwoot 第一轮最小动作不回归

## 8) 失败排查入口（先看哪里）

- **样板脚本失败**：
  - 先看脚本报错的 `[round2_acceptance_failed] ...`
  - 再看对应 `task_id` 的 `/steps` 输出中 `action_executed.detail` 是否字段缺失/为空
- **API 不通**：
  - 确认 `uvicorn` 在监听 `8000`
  - 查看服务启动日志（是否 DB init/依赖加载失败）
- **readiness 不通过**：
  - `GET /api/v1/internal/readiness/unified-provider` 返回的 `reason/reasons` 定位缺什么（credential/sandbox/config）

