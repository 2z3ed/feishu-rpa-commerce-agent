# P14-A 收口总结：LLM 意图解析 fallback

## 1. 阶段名称

P14-A：LLM 意图解析 fallback

## 2. 本轮目标

在不破坏 P12/P13 既有链路的前提下，实现并验证：

- 规则命中时继续走旧规则链路，不调用 LLM。
- 规则未命中时触发 LLM intent fallback（当前使用 mock provider）。
- fallback 输出经过 allowlist 与 confidence 校验后才可进入现有安全链路。
- 低置信度返回澄清问题，不强行执行。
- 不允许危险 intent（如删除类）直接执行。
- 高风险改价意图不绕过确认链路。
- 全过程在 `task_steps` 可追踪。

## 3. 实际完成内容

- 新增 P14-A 结构化输出 schema 与 fallback service（mock provider）。
- 在 `resolve_intent` 规则未命中分支接入 fallback，并补齐 steps 留痕：
  - `llm_intent_fallback_started`
  - `llm_intent_fallback_succeeded`
  - `llm_intent_fallback_low_confidence`
  - `llm_intent_fallback_failed`
  - `llm_intent_fallback_skipped`
- 增加 allowlist 与 confidence 阈值控制。
- `system.confirm_task` 已从 fallback allowlist 移除，避免由模糊自然语言授权确认执行。
- 保留 `product.update_price` fallback 解析能力，但继续走原确认链，最终进入 `awaiting_confirmation`。
- 启动脚本补齐 `.env` 变量加载，确保实机进程环境与配置一致。

## 4. 自动化测试结果

- `tests/test_p14a_llm_intent_fallback.py`：9 passed
- `tests/test_p10_b_query_integration.py` + `tests/test_resolve_intent_multi_platform.py`：52 passed

## 5. 飞书实机验收结果

### 5.1 旧规则链路验证

- 文案：`查看当前监控对象`
- `task_id=TASK-20260427-390392`
- 结果：成功返回监控对象列表，旧规则链路正常。

### 5.2 fallback 成功：异常对象查询

- 文案：`帮我看看哪些商品不太对`
- `task_id=TASK-20260427-293300`
- steps 关键记录：
  - `llm_intent_fallback_started`
  - `llm_intent_fallback_succeeded`
  - `intent=ecom_watch.monitor_diagnostics_query`
  - `confidence=0.82`
  - `allowed=true`

### 5.3 fallback 成功：失败对象重试

- 文案：`失败的那些再跑一遍`
- `task_id=TASK-20260427-948675`
- steps 关键记录：
  - `llm_intent_fallback_started`
  - `llm_intent_fallback_succeeded`
  - `intent=ecom_watch.retry_price_probes`
  - `confidence=0.86`
  - `allowed=true`

### 5.4 fallback 低置信度澄清

- 文案：`处理一下那个有问题的`
- `task_id=TASK-20260427-AC1296`
- steps 关键记录：
  - `llm_intent_fallback_started`
  - `llm_intent_fallback_low_confidence`
  - `intent=ecom_watch.monitor_diagnostics_query`
  - `confidence=0.62`
  - `threshold=0.75`
- 结果：返回澄清问题，没有强行执行。

### 5.5 危险删除命令拦截

- 文案：`把异常商品都删掉`
- `task_id=TASK-20260427-E5D75D`
- steps 关键记录：
  - `llm_intent_fallback_started`
  - `llm_intent_fallback_failed`
  - `intent=unknown`
  - `confidence=0.42`
  - `allowed=false`
  - `reason=intent_not_allowed`
- 结果：未执行删除动作。

### 5.6 改价命令确认链保护

- 文案：`帮我把 SKU A001 的价格改成 99`
- `task_id=TASK-20260427-AF5862`
- steps 关键记录：
  - `llm_intent_fallback_started`
  - `llm_intent_fallback_succeeded`
  - `intent=product.update_price`
  - `confidence=0.90`
  - `allowed=true`
- 结果：任务进入 `awaiting_confirmation`，未直接 `succeeded`。

## 6. 安全边界验证

- `system.confirm_task` 不允许由 fallback 生成并执行。
- `product.update_price` 即使 fallback 命中，仍必须进入确认链，不绕过高风险确认。
- 低置信度不执行，仅澄清。
- 非 allowlist / 危险语义不执行。
- steps detail 未出现 API Key、token、密钥或超长 prompt。

## 7. 当前限制

- 当前仅完成 mock provider 的飞书实机验证。
- **未接入真实外部大模型 API**，不应对外表述为“真实 LLM 已接入”。
- fallback 覆盖范围按 P14-A 验收句与当前 allowlist 控制，不做额外扩展。

## 8. 后续阶段建议

- 下一阶段可进入 P14-B（运营总结）前，先冻结 P14-A 代码与验收证据。
- 若后续接入真实模型，应在独立阶段完成：
  - provider 连接与超时/异常治理
  - 输出一致性与安全回退策略
  - 实机回归与审计留痕复核

## 9. 是否允许收口

允许收口。

结论依据：

- 自动化测试通过。
- 飞书实机 6 组验收通过。
- 高风险动作与危险语义安全边界符合 P14-A 要求。
- 规则命中与旧链路未退化。
