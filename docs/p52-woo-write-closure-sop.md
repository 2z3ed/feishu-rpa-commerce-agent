## P5.2 Woo 受控写链最小闭环 SOP

本 SOP 仅覆盖 P5.2 第一轮目标：

- intent：`product.update_price` + `system.confirm_task`
- 平台：仅 Woo
- 强约束：必须先 `awaiting_confirmation`，再由 `system.confirm_task` 唯一放行
- 写链：受控后台（非真实生产写），写后只读核验必须可复验

### 1) 固定环境（必须同一 venv）

```bash
source venv/bin/activate
export USE_SQLITE=true
export ENABLE_INTERNAL_SANDBOX_API=true
export PLAYWRIGHT_BROWSERS_PATH=0
python3 -c "from app.db.session import engine; print(engine.url)"
python -m playwright install chromium
```

### 2) 启动服务

启动 API：

```bash
source venv/bin/activate
export USE_SQLITE=true
export ENABLE_INTERNAL_SANDBOX_API=true
export PLAYWRIGHT_BROWSERS_PATH=0
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

启动 worker：

```bash
source venv/bin/activate
export USE_SQLITE=true
export ENABLE_INTERNAL_SANDBOX_API=true
export PLAYWRIGHT_BROWSERS_PATH=0
python -m celery -A app.workers.celery_app worker -l info
```

### 3) 触发高风险动作（必须进入 awaiting_confirmation）

通过任一入口触发 `product.update_price`（示例文本，确保包含 SKU 与目标价格）：

- `修改 SKU A001 价格到 39.9`

然后检查该任务：

```bash
curl -s "http://127.0.0.1:8000/api/v1/tasks/<update_task_id>"
curl -s "http://127.0.0.1:8000/api/v1/tasks/<update_task_id>/steps"
```

预期：
- `/tasks/<update_task_id>` 返回 200
- `status == "awaiting_confirmation"`

### 4) 放行确认（唯一入口 system.confirm_task）

使用确认命令确认原始任务：

- `确认执行 <update_task_id>`

这条命令应解析为 `system.confirm_task`，并生成一个新的 confirm 任务（记为 `<confirm_task_id>`）。

检查 confirm 任务：

```bash
curl -s "http://127.0.0.1:8000/api/v1/tasks/<confirm_task_id>"
curl -s "http://127.0.0.1:8000/api/v1/tasks/<confirm_task_id>/steps"
```

### 5) 写后核验怎么看（单一事实源）

单一事实源字段来自写链执行输出的 `parsed_result`（最终会透传到 `/steps` 的 `action_executed.detail` 映射展示）：

- `parsed_result.verify_passed`
- `parsed_result.verify_reason`
- `parsed_result.old_price`
- `parsed_result.new_price`
- `parsed_result.post_save_price`
- `parsed_result.operation_result`

### 6) 成功标准（写死）

必须同时满足：

1) 原始 update 任务进入 `awaiting_confirmation`  
2) `system.confirm_task` 放行成功  
3) confirm 后真实进入受控写入路径（页面进入编辑态、写入、保存）  
4) 写后核验成功：
   - `verify_passed == true`
   - `verify_reason == "ok"`（或受控约定的通过原因）
   - `post_save_price` 与目标价一致（在 tolerance 内）
5) 可通过 `/api/v1/tasks/{task_id}` 与 `/steps` 自证闭环：
   - `/steps` 中 `action_executed.detail` 可看到 `failure_layer/verify_* / old_price/new_price/post_save_price/operation_result`

### 7) 失败排查顺序（最小）

优先看：
- `/api/v1/tasks/<confirm_task_id>` 的 `status/result_summary/error_message`
- `/api/v1/tasks/<confirm_task_id>/steps` 的 `action_executed.detail`

写链失败 taxonomy（单一事实源 `parsed_result.failure_layer`，其余仅映射展示）至少包括：
- `confirm_target_invalid`
- `edit_mode_not_entered`
- `sku_not_hit`
- `current_price_read_failed`
- `new_price_fill_failed`
- `save_button_unavailable`
- `save_feedback_failed`
- `post_write_verify_mismatch`
- `unknown_exception`

### 8) P5.2 第二轮稳定化口径（固定）

`parsed_result` 是写后核验与失败分层的单一事实源。以下字段在 success / fail 样本中都必须可读（允许 `null` 语义，不允许字段缺失）：

- `old_price`
- `new_price`
- `post_save_price`
- `verify_passed`
- `verify_reason`
- `operation_result`
- `failure_layer`

`result_summary`、`error_message`、`/steps.action_executed.detail` 只做映射展示，不再自行判定一套不同结论。

### 9) 成功闭环怎么验（第二轮）

确认任务成功后，至少同时检查：

1. `/api/v1/tasks/<confirm_task_id>`: `status=succeeded`
2. `/api/v1/tasks/<confirm_task_id>/steps`: 存在 `detail_before_edit`、`detail_after_input`、`detail_after_submit`、`verification_result_recorded`
3. `action_executed.detail` 含：
   - `verify_passed=True`
   - `verify_reason=ok`
   - `operation_result=write_update_price`
   - `old_price/new_price/post_save_price`

### 10) 失败闭环怎么验（第二轮）

安全失败样本优先走 `confirm_target_invalid`（如确认不存在 task_id），避免主动破坏受控写环境。

检查：

1. `/api/v1/tasks/<confirm_task_id>`: `status=failed`
2. `/api/v1/tasks/<confirm_task_id>/steps`: `action_executed.detail` 含 `failure_layer=confirm_target_invalid`
3. `parsed_result` 必有：
   - `old_price/new_price/post_save_price`
   - `verify_passed/verify_reason`
   - `operation_result/failure_layer`

### 11) 重复回归怎么跑（固定标准）

第二轮固定最小回归标准：

- 至少 `3` 次真实成功闭环（同环境、同命令模板、同 SKU、同字段检查）
- 至少 `1` 个安全失败样本（建议 `confirm_target_invalid`）

回归汇总必须输出：

- 总次数 / 成功次数 / 失败次数
- 失败 taxonomy 分布
- 成功样本中 6 个核验字段的一致性结果

### 12) 失败归因优先级

先按以下优先级归因，避免误判：

1. **环境类**：readiness、会话缺失、配置缺失（如 `rpa_target_readiness_failed`）
2. **页面/写流逻辑类**：`edit_mode_not_entered`、`new_price_fill_failed`、`save_button_unavailable`、`save_feedback_failed`
3. **核验不一致类**：`post_write_verify_mismatch`

`unknown_exception` 仅作兜底，不作为常规回归目标。

### 13) 失败样本落点统一（P5.2 第三轮）

统一规则（强制）：

1. `parsed_result.failure_layer` 是失败 taxonomy 的单一事实源
2. `result_summary`、`error_message`、`/steps.action_executed.detail` 只能做映射展示
3. 同一任务在不同观测面必须映射到同一个 `failure_layer`

最小检查项：

- `/api/v1/tasks/<confirm_task_id>` 里可读到 `parsed_result.failure_layer`
- `result_summary` 与 `error_message` 的标签与 `parsed_result.failure_layer` 一致
- `/api/v1/tasks/<confirm_task_id>/steps` 的 `action_executed.detail` 里 `failure_layer=` 与上面一致

### 14) 失败聚合脚本（P5.2 第三轮）

脚本：`scripts/p52_woo_write_failure_summary.py`

默认只读 API（不默认回退 sqlite）：

- `/api/v1/tasks`
- `/api/v1/tasks/{task_id}`
- `/api/v1/tasks/{task_id}/steps`

运行方式：

```bash
source venv/bin/activate
python scripts/p52_woo_write_failure_summary.py \
  --base-url "http://127.0.0.1:8000" \
  --limit 50 \
  --task-prefix "TASK-P52"
```

固定输出字段（验收必须包含）：

- `total_tasks`
- `succeeded_tasks`
- `failed_tasks`
- `failure_distribution`
- `recent_failed_tasks`

其中 `recent_failed_tasks` 至少包含：

- `task_id`
- `failure_layer`

### 15) 第三轮准生产验收判定（固定）

本轮通过必须同时满足：

1. **成功样本路径不回归**：至少 1 轮真实成功闭环可复验（`awaiting_confirmation -> confirm -> succeeded`）
2. **失败样本可沉淀可统计**：聚合脚本可读出现有失败样本，并输出固定字段
3. **失败分类可判读**：
   - 环境类优先：`rpa_target_readiness_failed` 等
   - 页面写流类：`edit_mode_not_entered`、`new_price_fill_failed`、`save_button_unavailable`、`save_feedback_failed`
   - 核验不一致类：`post_write_verify_mismatch`

不允许为了造失败而主动做危险写操作；优先复用历史安全失败样本（如 `confirm_target_invalid`）。
