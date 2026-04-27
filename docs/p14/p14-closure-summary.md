# P14 总收口总结：LLM 智能增强层

## 1. 阶段总览（P14-Z）

本文档用于 P14-A / P14-B / P14-C / P14-D 的统一收口与交接，供下一个 GPT / agent / 人工开发者继续推进后续阶段。

P14 的定位不是“让 LLM 自动执行后台动作”，而是：

- 在既有规则闭环上增强自然语言理解能力（P14-A）
- 增强监控总结能力（P14-B）
- 增强异常解释能力（P14-C）
- 增强计划生成能力（P14-D）

核心原则保持不变：

- 高风险动作仍走既有确认链路
- LLM 输出是“理解/说明/建议”，不是“自动执行”
- 失败时必须可降级，不中断主流程

---

## 2. P14-A 收口摘要（LLM intent fallback）

已完成能力：

- 规则未命中时触发 `intent fallback`
- 输出包含 `intent / slots / confidence / clarification_question`
- 增加 `allowlist` 校验
- 增加 `confidence` 阈值控制
- 低置信度返回澄清问题，不强行执行

安全边界已落实：

- `system.confirm_task` 禁止由 LLM fallback 生成
- `product.update_price` 即使 fallback 命中，也不绕过确认链路，仍进入 `awaiting_confirmation`

验收结论：

- 飞书实机验收通过（详见 P14-A 阶段验收记录）

---

## 3. P14-B 收口摘要（LLM monitor summary）

已完成能力：

- 新增 intent：`ecom_watch.monitor_summary`
- 支持 `summary_focus=overview / health_check / priority_targets`
- 生成老板可读监控总结文本

可靠性策略：

- LLM provider 失败时降级为规则摘要

验收结论：

- 飞书实机验收通过（详见 P14-B 阶段验收记录）

---

## 4. P14-C 收口摘要（LLM anomaly explanation）

已完成能力：

- 新增 intent：`ecom_watch.anomaly_explanation`
- 支持 `explanation_focus=overview / low_confidence / mock_source / manual_review`
- 将诊断字段翻译为业务可读异常解释

可靠性策略：

- LLM provider 失败时降级为规则解释

验收结论：

- 飞书实机验收通过（详见 P14-C 阶段验收记录）

---

## 5. P14-D 收口摘要（LLM action plan）

已完成能力：

- 新增 intent：`ecom_watch.action_plan`
- 支持 `plan_focus=overview / priority / manual_review_first / retry_url_mix`
- 基于既有诊断与建议字段生成“下一步处理计划”

可靠性策略：

- LLM provider 失败时降级为规则计划

验收结论：

- 飞书实机验收通过（详见 P14-D 阶段验收记录）

---

## 6. 新增 intent 清单（P14 汇总）

P14 新增/强化后的 intent 重点如下：

- `ecom_watch.monitor_summary`
- `ecom_watch.anomaly_explanation`
- `ecom_watch.action_plan`

说明：

- P14-A 本质是 fallback 增强（规则未命中时的理解增强），不是“单一新增业务 intent 阶段”。

---

## 7. 新增环境变量清单（P14 汇总）

以下变量为 P14 关键开关与 provider 配置：

- `ENABLE_LLM_INTENT_FALLBACK`
- `LLM_INTENT_PROVIDER`
- `ENABLE_LLM_MONITOR_SUMMARY`
- `LLM_MONITOR_SUMMARY_PROVIDER`
- `ENABLE_LLM_ANOMALY_EXPLANATION`
- `LLM_ANOMALY_EXPLANATION_PROVIDER`
- `ENABLE_LLM_ACTION_PLAN`
- `LLM_ACTION_PLAN_PROVIDER`

配置原则：

- 真实 `.env` 不应提交到 git
- `.env.example` 仅作为样例模板
- 飞书实机验收前，必须确认 API / worker 进程已实际加载对应环境变量

---

## 8. task_steps 留痕清单（P14 汇总）

### 8.1 P14-A（intent fallback）

- `llm_intent_fallback_started`
- `llm_intent_fallback_succeeded`
- `llm_intent_fallback_failed`
- `llm_intent_fallback_skipped`
- `llm_intent_fallback_low_confidence`

### 8.2 P14-B（monitor summary）

- `llm_monitor_summary_started`
- `llm_monitor_summary_succeeded`
- `llm_monitor_summary_failed`
- `llm_monitor_summary_fallback_used`

### 8.3 P14-C（anomaly explanation）

- `llm_anomaly_explanation_started`
- `llm_anomaly_explanation_succeeded`
- `llm_anomaly_explanation_failed`
- `llm_anomaly_explanation_fallback_used`

### 8.4 P14-D（action plan）

- `llm_action_plan_started`
- `llm_action_plan_succeeded`
- `llm_action_plan_failed`
- `llm_action_plan_fallback_used`

---

## 9. 飞书实机验收摘要

当前收口结论：

- P14-A 飞书实机验收通过
- P14-B 飞书实机验收通过
- P14-C 飞书实机验收通过
- P14-D 飞书实机验收通过

说明：

- 本文档不新增、不编造 task_id，具体验收样本与细节以各阶段验收记录为准。

---

## 10. 安全边界（必须保持）

P14 阶段明确不做自动执行，必须保持以下边界：

- 不自动刷新
- 不自动重试
- 不自动替换 URL
- 不自动删除
- 不自动改价
- 不自动调用 RPA
- 不绕过确认链路

补充说明：

- LLM 仅输出解释、总结、计划或澄清，不直接触发高风险业务动作落地。

---

## 11. 未阻塞问题（已知）

已知历史问题：

- 全量 `pytest` 仍可能出现 `test_im_service.py` / `test_message_service.py` 的 `Client.im` 既有收集错误。

结论：

- 该问题与 P14 收口无直接关系，可作为独立事项后续跟踪处理。

---

## 12. 下一步建议（进入 P15）

建议下一阶段进入：

- **P15 OCR：发票 / 票据识别**

范围说明：

- 本文档仅给出下一步方向，不包含任何 P15 功能开发内容。

---

## 13. 交接提醒（给下一个执行者）

- 先复核四阶段文档与验收清单，再进入新阶段开发。
- 继续坚持“规则主链 + LLM 增强 + 安全边界不放松”的策略。
- 新阶段若引入新能力，优先保持可降级、可留痕、可复盘。
