# P5.1 Woo Readonly SOP

本 SOP 用于 P5.1（Woo readonly `real_admin_prepared`）的稳定回归与失败诊断。

## 1) 固定环境（必须同一 venv）

```bash
source venv/bin/activate
export USE_SQLITE=true
export ENABLE_INTERNAL_SANDBOX_API=true
export PLAYWRIGHT_BROWSERS_PATH=0
python3 -c "from app.db.session import engine; print(engine.url)"
```

预期看到：`sqlite:///./feishu_rpa.db`

安装/补齐浏览器（一次性）：

```bash
source venv/bin/activate
export USE_SQLITE=true
export ENABLE_INTERNAL_SANDBOX_API=true
export PLAYWRIGHT_BROWSERS_PATH=0
python -m playwright install chromium
```

### 可选：依赖服务

```bash
docker compose -f docker-compose.dev.yml up -d
```

### 启动 API

```bash
source venv/bin/activate
export USE_SQLITE=true
export ENABLE_INTERNAL_SANDBOX_API=true
export PLAYWRIGHT_BROWSERS_PATH=0
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 启动 worker（如本地需要）

```bash
source venv/bin/activate
export USE_SQLITE=true
export ENABLE_INTERNAL_SANDBOX_API=true
export PLAYWRIGHT_BROWSERS_PATH=0
python -m celery -A app.workers.celery_app worker -l info
```

## 2) 成功验证怎么做（固定命令）

1. 触发 readonly 样板：

```bash
source venv/bin/activate
export USE_SQLITE=true
export ENABLE_INTERNAL_SANDBOX_API=true
export PLAYWRIGHT_BROWSERS_PATH=0
python3 scripts/p50_round3_manual_woo_sample.py --sku A001 --base-url http://127.0.0.1:8000 --poll-seconds 12
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
- 成功样本中 `parsed_result` 关键字段稳定可见：
  - `page_status`
  - `page_message`
  - `detail_loaded`
  - `target_sku_hit`
  - `read_source`
  - `evidence_count`

## 3) 失败时先看哪里

先看 `/tasks/<task_id>` 的：
- `status`
- `result_summary`
- `error_message`（如有）

再看 `/steps` 中 `action_executed.detail`，结合 taxonomy 判断层级：

- `browser_start_failed`：Playwright 启动/浏览器层失败（通常是环境问题）
- `page_load_failed:home|catalog|detail`：页面加载层失败
- `readiness_not_ready|session_unavailable`：会话或 readiness 问题
- `sku_not_hit`：SKU 未命中
- `detail_not_loaded`：详情页关键内容未加载
- `selector_or_page_structure_abnormal`：页面结构/selector 异常
- `readback_unstable`：readback 不稳定或不可解析
- `unknown_exception`：未知异常（结合 traceback）

排查顺序固定为：**环境 -> 页面加载 -> 会话/readiness -> SKU 命中 -> 详情加载与读回**。

### 失败层级单一事实源（第三轮固化）

- 单一事实源：`parsed_result.failure_layer`
- 映射展示面（必须与单一事实源一致）：
  - `result_summary` 前缀：`[failure_layer] ...`
  - `error_message` 前缀：`[failure_layer] ...`
  - `steps.detail`：包含 `failure_layer=<value>`
- 若三处标签不一致，视为失败样本沉淀不合格，需先修口径再继续回归。

## 4) 重复回归时重点看哪些字段

每次回归都要记录：

- `task_id`
- `/tasks`：`status`, `result_summary`
- `/steps`：`action_executed.detail`
- `parsed_result.failure_layer`（若失败）
- `parsed_result.detail_loaded` / `target_sku_hit` / `page_status` / `page_message`
- `parsed_result.read_source` / `parsed_result.evidence_count`

## 5) 重复回归固定标准（建议 3~5 次）

- 固定环境：同一 `venv` + 同一环境变量（见第 1 节）
- 固定命令：第 2 节样板命令
- 固定检查：
  - `/tasks` HTTP 200
  - `/steps` HTTP 200
  - `status == succeeded`
  - `action_executed.detail` 四核心字段稳定
  - 成功样本关键字段稳定（`page_status/page_message/detail_loaded/target_sku_hit/read_source/evidence_count`）
- 固定结果汇总：
  - 共跑 N 次
  - 成功 X 次
  - 失败 Y 次
  - 失败 taxonomy 分布（按 `failure_layer` 聚合）

## 6) 失败聚合脚本（API 只读）

脚本：`scripts/p51_woo_readonly_failure_summary.py`

示例命令：

```bash
source venv/bin/activate
python3 scripts/p51_woo_readonly_failure_summary.py --base-url http://127.0.0.1:8000 --limit 50 --task-prefix TASK-P50-R3-MANUAL-WOO-SAMPLE
```

固定输出字段：
- `total_tasks`
- `succeeded_tasks`
- `failed_tasks`
- `failure_distribution`（taxonomy -> count）
- `recent_failed_tasks`（至少 `task_id` + `failure_layer`）

该脚本只读访问：
- `GET /api/v1/tasks`
- `GET /api/v1/tasks/{task_id}`
- `GET /api/v1/tasks/{task_id}/steps`

不写任务、不改状态、不落盘任务系统。
## 7) 环境问题 vs 业务逻辑问题（快速判别）

可优先判定为环境问题：
- `browser_start_failed`
- `page_load_failed:*`（目标站点/网络不可用）
- `session_unavailable`（cookie/header 注入不可用）

可优先判定为业务逻辑/页面语义问题：
- `sku_not_hit`
- `detail_not_loaded`
- `selector_or_page_structure_abnormal`
- `readback_unstable`

`unknown_exception` 需要结合 traceback 与 steps.detail 再归类，不直接判定为平台扩展需求。
