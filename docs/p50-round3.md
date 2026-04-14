# P5.0 Round3 Woo Manual Sample

本轮目标仅包含两项收尾：

1. 修复 `app/rpa/real_admin_readonly.py` 的 `_log` 未定义问题。
2. 将手工样板链路的 `source_message_id` 置空，避免手工验收时触发 Feishu `invalid open_message_id` 噪音。

## 脚本

- `scripts/p50_round3_manual_woo_sample.py`

## 运行方式

```bash
python scripts/p50_round3_manual_woo_sample.py --sku A001 --base-url http://127.0.0.1:8000 --poll-seconds 10
```

## Round3 验收点

脚本成功时会输出一个新的任务号，格式为：

- `TASK-P50-R3-MANUAL-WOO-SAMPLE-{YYYYMMDD-HHMMSS}`

并满足：

1. `GET /api/v1/tasks/{task_id}` 返回 `200`
2. `GET /api/v1/tasks/{task_id}/steps` 返回 `200`
3. 任务详情中 `status == succeeded`
4. `action_executed.detail` 中包含：
   - `provider_id=woo`
   - `readiness_status=ready`
   - `endpoint_profile` 非空
   - `session_injection_mode` 非空

## 说明

- Round3 手工样板仍沿用现有 ingress 主链，不直接写 `TaskRecord` / `TaskStep`。
- 仅在手工样板脚本调用 `process_ingress_message.run(...)` 时传空 `source_message_id`，不改变真实飞书消息的回复语义。
