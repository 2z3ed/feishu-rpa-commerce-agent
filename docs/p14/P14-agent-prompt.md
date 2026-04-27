# P14-A Agent 开发约束：LLM 意图解析 fallback

## 一、当前唯一主线

当前唯一主线是：

P14-A：LLM 意图解析 fallback

本轮只做：

规则未命中时，用 LLM 解析 intent / slots。

## 二、当前已完成基础

P13 已完成：

- 监控对象管理
- 查询语义统一
- 刷新结果摘要
- refresh run 留痕
- 定时刷新
- HTML 价格采集
- 采集状态治理
- 手动重试
- 价格诊断
- URL 替换 + 重采集闭环
- 决策建议系统

不要回头重做 P13。

## 三、必须先读

开始开发前，必须先读：

1. AGENTS.md 当前阶段入口
2. docs/p14/p14-project-plan.md
3. docs/p14/P14-agent-prompt.md
4. docs/p14/p14-boss-demo-sop.md
5. docs/p14/p14-acceptance-checklist.md

如果文件不存在，先创建文档，不要直接写业务代码。

## 四、A / B 边界

A 项目负责：

- 飞书入口
- intent 解析
- LLM fallback
- task 编排
- steps 留痕
- 老板交互展示

B 项目负责：

- 监控对象
- 价格采集
- 诊断字段
- URL 治理
- 决策建议字段

固定原则：

A 只展示和调用。  
B 才做业务逻辑。

本轮原则上不改 B 项目。

## 五、本轮允许做

允许做：

- 新增 LLM intent fallback service
- 新增 LLM 输出 schema
- 新增 mock provider
- 新增环境变量开关
- 在规则未命中后接入 fallback
- 增加 intent allowlist
- 增加 confidence 阈值
- 增加低置信度澄清问题
- 增加 task_steps 留痕
- 增加测试

## 六、本轮禁止做

禁止做：

- 不做 P14-B 运营总结
- 不做 P14-C 异常解释
- 不做 P14-D 操作计划
- 不做 P15 OCR
- 不做发票识别
- 不做 Playwright
- 不做浏览器渲染
- 不做代理池
- 不处理 Amazon 反爬
- 不自动 URL 修复
- 不自动修改监控对象
- 不自动删除监控对象
- 不自动触发 RPA
- 不自动决定告警
- 不新增复杂业务动作
- 不新增平台
- 不重构飞书入口层
- 不重构 LangGraph 主链
- 不破坏 P12 / P13 已完成链路

## 七、核心规则

### 1. 规则命中，不调用 LLM

现有规则能识别的命令，必须继续走旧链路。

### 2. 规则未命中，才调用 LLM

只有 unknown / unclear intent 才进入 LLM fallback。

### 3. LLM 默认关闭

必须支持：

```env
ENABLE_LLM_INTENT_FALLBACK=false
```

默认关闭时，系统行为必须和旧版一致。

### 4. 必须有 mock provider

第一轮不要依赖真实模型 key。

必须支持：

```env
LLM_INTENT_PROVIDER=mock
```

### 5. 必须有 allowlist

LLM 返回的 intent 必须在 allowlist 内。

不在 allowlist：

- 不执行
- 留痕
- 返回澄清或 unknown

### 6. 必须有 confidence 阈值

建议：

- >= 0.75：可进入现有链路
- 0.5 到 0.75：返回澄清问题
- < 0.5：unknown

### 7. 高风险动作不绕过确认

即使 LLM confidence 高，也不能绕过原来的确认链路。

## 八、LLM 输出结构

LLM fallback 必须输出结构化 JSON：

```json
{
  "intent": "existing_intent_code",
  "slots": {},
  "confidence": 0.82,
  "needs_confirmation": false,
  "clarification_question": "",
  "reason": "用户想查询异常监控对象"
}
```

要求：

- intent 必须是已有 intent
- slots 必须能被旧链路使用
- confidence 必须是 0 到 1
- needs_confirmation 不能绕过确认链路
- clarification_question 用于低置信度或缺参
- reason 只用于日志

## 九、steps 留痕

至少支持：

- llm_intent_fallback_started
- llm_intent_fallback_succeeded
- llm_intent_fallback_failed
- llm_intent_fallback_skipped
- llm_intent_fallback_low_confidence

禁止在 steps detail 中写入：

- API Key
- token
- 密钥
- 超长 prompt

## 十、建议实现位置

先锚定仓库真实结构，再决定文件位置。

优先检查：

- app/graph/nodes/resolve_intent.py
- app/graph/nodes/execute_action.py
- app/tasks/ingress_tasks.py
- app/core/config.py
- task_steps 写入方式
- tests 目录结构

建议新增：

- app/services/llm/intent_fallback.py
- app/schemas/llm_intent.py
- tests/test_p14a_llm_intent_fallback.py

如果仓库已有类似目录，以现有目录为准。

## 十一、测试要求

至少覆盖：

- 规则命中不调用 LLM
- 规则未命中触发 LLM
- 高置信度进入现有链路
- 低置信度返回澄清
- 非法 intent 被拦截
- LLM 异常安全回退
- 开关关闭不影响旧链路
- P12 / P13 回归不退化

## 十二、完成后回报格式

完成后必须回报：

A. 先读了哪些文件  
B. 当前 resolve_intent / unknown intent 锚定结果  
C. LLM fallback 接入位置  
D. 本轮实际执行了哪些命令  
E. 改了哪些文件  
F. LLM 输出 schema  
G. allowlist 如何设计  
H. 低置信度如何处理  
I. steps 如何留痕  
J. 测试结果  
K. 是否可以进入飞书实机验收  