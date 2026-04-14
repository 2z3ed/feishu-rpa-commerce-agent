## P5.5 Woo 写链发布前全链路演练与阶段收口

本文件用于 P5.5 阶段收口，只覆盖 Woo 写链既有能力串联演练，不扩平台、不扩动作。

### 1) 已完成阶段（收口基线）

- P5.0 ~ P5.4（含第三轮）均已通过。
- 当前主线能力包括：confirm 放行、幂等拦截、兼容读取、单条回放、门禁、复核提示、留痕模板。

### 2) 演练脚本与职责边界

脚本：`script/p55_woo_release_rehearsal.py`

职责（仅编排与留档）：

- 调用 `p53` confirm-only 聚合
- 调用 `p53 --task-id` 回放
- 调用 `p54` 门禁
- 汇总结果并输出固定留档结构

不做：

- 不复写 `p53` 治理解析逻辑
- 不复写 `p54` 门禁判定逻辑
- 不新增业务能力

### 3) 固定 covered_checks 枚举

以下覆盖项固定且脚本/文档一致：

- `update_enters_awaiting_confirmation`
- `first_confirm_succeeds`
- `post_write_verification_present`
- `repeat_confirm_blocked`
- `invalid_target_safe_failure`
- `confirm_only_summary_available`
- `task_id_replay_available`
- `gate_output_available`
- `review_hints_available`
- `review_record_templates_available`

### 4) 演练结果留档核心结构（固定）

核心字段（每次必有）：

- `rehearsal_run_at`
- `environment`
- `covered_checks`
- `key_task_ids`
- `gate_status`
- `review_summary`
- `final_result`

supporting 字段（可扩展但不影响核心结构）：

- `artifacts`
- `notes`
- `links`

要求：

- stdout 与 `--output-json` 完全一致
- 缺值时使用空字符串/空数组/空对象，不缺字段

### 5) key_task_ids 规则（固定）

`key_task_ids` 只记录本次演练真实使用的样本，不混入历史窗口噪音：

- `success_confirm_task_id`
- `repeat_confirm_task_id`
- `invalid_or_unknown_task_id`

### 6) 一次完整演练怎么跑

```bash
source venv/bin/activate
python script/p55_woo_release_rehearsal.py \
  --base-url "http://127.0.0.1:8000" \
  --task-prefix "TASK-" \
  --limit 80 \
  --recent-limit 20 \
  --success-task-id "TASK-SUCCESS-CONFIRM" \
  --repeat-task-id "TASK-REPEAT-BLOCKED" \
  --invalid-or-unknown-task-id "TASK-INVALID-OR-UNKNOWN" \
  --environment "staging_like" \
  --output-json "tmp/p55_rehearsal.json"
```

### 7) 演练通过标准（P5.5）

- `covered_checks` 全部 `passed=true`
- `gate_status` 可读且来自 `p54` 输出
- `review_summary` 可读（包含 hint 汇总）
- `final_result=passed`

### 8) 当前尾巴与收口理由

尾巴：

- 尚未接入 CI 平台与审批流（本阶段明确不做）。

收口理由：

- Woo 写链从执行、治理、门禁、复核到留痕已形成最小闭环；
- 当前最优动作是阶段收口与交接固化，而不是扩展新能力。

### 9) 交接速览（给下一位接手）

- 看状态：先读本文件第 1/7/8 节
- 跑演练：执行第 6 节命令
- 判定通过：看 `final_result` 与 `covered_checks`
- 若失败：回到 `artifacts.p53_replays` 与 `artifacts.p54_gate.review_hints` 做复盘
