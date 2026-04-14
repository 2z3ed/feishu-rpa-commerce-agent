# P5.1 Woo Readonly SOP

本 SOP 仅用于 P5.1 第一轮：Woo readonly（`real_admin_prepared`）稳定化与准生产验证。

## 1) 环境启动（同一环境）

```bash
source venv/bin/activate
export USE_SQLITE=true
python3 -c "from app.db.session import engine; print(engine.url)"
```

预期看到：`sqlite:///./feishu_rpa.db`

### 可选：依赖服务

```bash
docker compose -f docker-compose.dev.yml up -d
```

### 启动 API

```bash
source venv/bin/activate
export USE_SQLITE=true
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 启动 worker（如本地需要）

```bash
source venv/bin/activate
export USE_SQLITE=true
celery -A app.workers.celery_app.celery_app worker -l info
```

## 2) 成功验证怎么做

1. 触发 readonly 样板：

```bash
source venv/bin/activate
export USE_SQLITE=true
python3 scripts/p50_round3_manual_woo_sample.py --sku A001 --base-url http://127.0.0.1:8000
```

2. 记录输出 `task_id`（格式：`TASK-P50-R3-MANUAL-WOO-SAMPLE-*`）。
3. 检查任务详情：

```bash
curl -s "http://127.0.0.1:8000/api/v1/tasks/<task_id>"
```

4. 检查步骤：

```bash
curl -s "http://127.0.0.1:8000/api/v1/tasks/<task_id>/steps"
```

### 通过标准（写死）

- `/tasks/<task_id>` 返回 `200`
- `/tasks/<task_id>/steps` 返回 `200`
- `status == "succeeded"`
- `action_executed.detail` 中稳定包含：
  - `provider_id=woo`
  - `readiness_status=ready`
  - `endpoint_profile` 非空
  - `session_injection_mode` 非空

## 3) 失败时先看哪里

先看 `/tasks/<task_id>` 的：
- `status`
- `result_summary`
- `error_message`（如有）

再看 `/steps` 中 `action_executed.detail`，结合 taxonomy 判断层级：

- `page_load_failed:home|catalog|detail`：页面加载层失败
- `session_or_readiness`：会话或 readiness 问题
- `sku_not_hit`：SKU 未命中
- `selector_or_page_structure_abnormal`：页面结构/selector 异常
- `readback_inconsistent`：readback 不一致或不可解析
- 其他：按未知异常处理（结合 traceback）

## 4) 重复回归时重点看哪些字段

每次回归都要记录：

- `task_id`
- `/tasks`：`status`, `result_summary`
- `/steps`：`action_executed.detail`
- `parsed_result.failure_layer`（若失败）
- `parsed_result.detail_loaded` / `target_sku_hit` / `page_status` / `page_message`

建议固定同一条命令连续跑 3 次，统计成功/失败次数与失败层级分布。
