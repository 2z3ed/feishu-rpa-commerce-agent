# P14-A 开发主线文档：LLM 意图解析 fallback

## 一、阶段名称

P14-A：LLM 意图解析 fallback

## 二、当前背景

P13 已完成，系统已经具备监控对象管理、价格刷新、采集状态治理、手动重试、价格诊断、URL 替换重采集、决策建议等能力。

当前系统的问题不是没有业务闭环，而是自然语言入口仍然偏规则化。

例如用户可能会说：

- 帮我看看哪些商品不太对
- 失败的那些再跑一遍
- 哪些价格不可信
- 哪些对象需要人工处理
- 这个链接不准，帮我换成新的

这些表达如果全部靠关键词和正则扩展，会越来越难维护。

所以 P14-A 的目标是：

在不破坏现有规则链路的前提下，为规则未命中的自然语言增加 LLM fallback。

## 三、本轮唯一目标

只做：

规则未命中 → LLM 解析 intent + slots。

固定链路：

飞书自然语言消息  
→ A 项目接收  
→ 现有规则解析  
→ 规则命中：直接走旧链路  
→ 规则未命中：调用 LLM intent fallback  
→ LLM 输出结构化 JSON  
→ 系统校验 intent / slots / confidence  
→ 高置信度：进入现有安全链路  
→ 低置信度：返回澄清问题  
→ 异常：安全回退 unknown  
→ task_steps 留痕  

## 四、P14-A 定位

LLM 只负责理解，不负责执行。

LLM 可以做：

- intent 识别
- slots 提取
- 置信度判断
- 缺参澄清问题生成
- 简短解析原因

LLM 不可以做：

- 直接执行动作
- 修改数据库
- 替换 URL
- 删除监控对象
- 触发 RPA
- 跳过确认链路
- 新增业务动作
- 重新计算 B 项目业务结果

## 五、A / B 项目边界

A 项目负责：

- 飞书入口
- 消息编排
- intent 解析
- LLM fallback
- task 编排
- steps 留痕
- 老板交互展示

B 项目负责：

- monitor target
- 价格采集
- fallback 机制
- probe 状态
- 诊断字段
- URL 治理
- 决策建议字段

固定原则：

A 只展示和调用。  
B 才做业务逻辑。

P14-A 原则上不改 B 项目。

## 六、本轮允许做

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

## 七、本轮禁止做

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
- 不切数据库
- 不重构飞书入口层
- 不重构 LangGraph 主链
- 不破坏 P12 / P13 已完成链路

## 八、LLM 输出结构

LLM fallback 必须输出结构化 JSON。

推荐结构：

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

字段说明：

- intent：必须是仓库已有 intent，不允许凭空发明
- slots：结构化参数，字段名必须对齐现有执行链路
- confidence：0 到 1
- needs_confirmation：是否需要确认，但不能绕过原确认链路
- clarification_question：低置信度或缺参数时给用户的问题
- reason：简短解释为什么这么判断，仅用于日志或 debug

## 九、intent allowlist

P14-A 必须有 allowlist。

LLM 只能返回 allowlist 内的 intent。

allowlist 需要基于仓库现有 intent 设计，不允许凭空发明。

建议优先纳入 P13 已稳定的安全场景：

- 查询监控对象
- 查询异常对象
- 查询低可信对象
- 手动重试失败对象
- URL 替换 / 重采集
- 查看刷新摘要
- 查看决策建议

如果 LLM 返回不在 allowlist 的 intent：

- 不执行
- 写入 steps
- 返回澄清或 unknown

## 十、confidence 规则

建议阈值：

- confidence >= 0.75：允许进入现有链路
- 0.5 <= confidence < 0.75：返回澄清问题
- confidence < 0.5：按 unknown intent 处理

高风险动作即使 confidence 高，也不能绕过原确认链路。

## 十一、环境变量建议

建议新增：

```env
ENABLE_LLM_INTENT_FALLBACK=false
LLM_INTENT_PROVIDER=mock
LLM_INTENT_MODEL=
LLM_INTENT_TIMEOUT_SECONDS=8
LLM_INTENT_CONFIDENCE_THRESHOLD=0.75
```

要求：

- 默认关闭
- mock provider 可测试
- 真实 provider 后续再接
- timeout 必须有限制

## 十二、接入位置建议

建议接入位置：

resolve_intent 节点内部，规则解析失败之后，execute_action 之前。

推荐流程：

规则解析  
→ 命中：返回旧 intent  
→ 未命中：判断开关  
→ 开关关闭：返回 unknown  
→ 开关开启：调用 LLM fallback  
→ 校验 schema / allowlist / confidence  
→ 返回标准 intent / slots 或澄清问题  

不要把 LLM 调用散写到：

- 飞书入口
- execute_action 业务分支
- B service client
- 价格采集服务
- 结果展示层

## 十三、steps 留痕

建议新增 step_code：

- llm_intent_fallback_started
- llm_intent_fallback_succeeded
- llm_intent_fallback_failed
- llm_intent_fallback_skipped
- llm_intent_fallback_low_confidence

detail 建议包含：

- enabled
- provider
- original_text
- llm_intent
- confidence
- allowed
- reason
- error

禁止写入：

- API Key
- token
- 真实密钥
- 超长 prompt

## 十四、开发拆分

### P14-A.0：仓库锚定

先检查：

- resolve_intent 在哪里
- unknown intent 怎么处理
- 现有 intent_code 有哪些
- task_steps 怎么写
- config/env 怎么读
- tests 命名方式
- 是否已有 LLM / RAG 封装

### P14-A.1：schema 与 service

新增：

- LLM intent fallback 输入输出 schema
- mock provider
- allowlist 校验
- confidence 校验
- timeout / 异常处理

### P14-A.2：接入 resolve_intent

只在规则未命中时调用。

要求：

- 规则命中不调用 LLM
- 开关关闭不调用 LLM
- 高置信度返回标准 intent / slots
- 低置信度返回澄清问题
- 异常安全回退

### P14-A.3：steps 留痕

记录 fallback 是否触发、是否成功、为什么失败。

### P14-A.4：测试

至少覆盖：

- 规则命中不调用 LLM
- 规则未命中触发 LLM
- 高置信度进入现有链路
- 低置信度返回澄清
- 非法 intent 被拦截
- LLM 异常安全回退
- 开关关闭不影响旧链路

## 十五、最低通过标准

P14-A 通过标准：

- 默认关闭时旧链路完全不变
- 开启后规则未命中才触发 LLM
- LLM 输出必须校验 schema
- intent 必须在 allowlist 内
- confidence 不达标不能执行
- 低置信度能返回澄清问题
- 非法 intent 不执行
- 高风险动作不绕过确认
- task_steps 有 fallback 留痕
- P12 / P13 回归不退化

## 十六、完成后回报格式

Agent 完成后必须按以下格式回报：

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