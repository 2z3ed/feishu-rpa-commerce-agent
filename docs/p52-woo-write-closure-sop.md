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

