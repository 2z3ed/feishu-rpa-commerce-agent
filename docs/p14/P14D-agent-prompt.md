# P14-D Agent 开发约束：LLM 操作计划生成

## 一、当前唯一主线

当前唯一主线是：

P14-D：LLM 操作计划生成

本轮只做：

基于 P13 已有采集状态、诊断字段和决策建议字段，生成老板可读的下一步操作计划。

## 二、当前已完成基础

P14-A 已完成并收口：

- 规则未命中时可触发 LLM fallback
- 有 allowlist
- 有 confidence 阈值
- 低置信度会澄清
- system.confirm_task 不允许由 LLM fallback 生成
- product.update_price 不绕过确认
- 飞书实机验收通过

P14-B 已完成并收口：

- LLM 监控对象运营总结
- overview / health_check / priority_targets
- provider 失败降级
- 飞书实机验收通过

P14-C 已完成并收口：

- LLM 异常原因解释
- overview / low_confidence / mock_source / manual_review
- provider 失败降级
- 飞书实机验收通过

P13 已完成：

- 监控对象管理
- 采集状态治理
- 价格诊断
- URL 替换 + 重采集闭环
- 决策建议系统

不要回头重做 P13 / P14-A / P14-B / P14-C。

## 三、必须先读

开始开发前，必须先读：

1. AGENTS.md 当前阶段入口
2. docs/p14/p14d-project-plan.md
3. docs/p14/P14D-agent-prompt.md
4. docs/p14/p14d-boss-demo-sop.md
5. docs/p14/p14d-acceptance-checklist.md

如果文件不存在，先创建文档，不要直接写业务代码。

## 四、A / B 边界

A 项目负责：

- 识别操作计划类 intent
- 调用 B 获取已有监控对象、诊断字段、决策建议字段
- 组织 action plan 输入
- 调用 LLM action plan service
- 返回老板可读文本
- task_steps 留痕

B 项目负责：

- 监控对象
- 价格采集
- 采集状态
- 诊断字段
- URL 治理字段
- 决策建议字段

固定原则：

A 只生成计划和展示。  
B 才做业务数据生成。  
LLM 不重新计算 B 的诊断字段和建议字段。  
LLM 不自动执行计划。

## 五、本轮允许做

允许做：

- 新增操作计划类 intent
- 新增 LLM action plan service
- 新增 mock provider
- 新增 action plan 输入 schema
- 新增 action plan 输出文本
- 新增 LLM 失败降级
- 新增 task_steps 留痕
- 新增飞书文本返回
- 新增测试
- 更新 .env.example
- 明确真实 .env 需要人工同步的变量

## 六、本轮禁止做

禁止做：

- 不做 P15 OCR
- 不做发票识别
- 不做自动刷新
- 不做自动重试
- 不做自动替换 URL
- 不做自动删除对象
- 不做自动改价
- 不做主动通知
- 不做真正告警系统
- 不做 Playwright / 浏览器渲染
- 不做代理池
- 不处理 Amazon 反爬
- 不改 B 采集逻辑
- 不重构 P14-A
- 不重构 P14-B
- 不重构 P14-C
- 不破坏 P13-I 价格诊断字段
- 不破坏 P13-K 决策建议字段
- 不破坏 P12 卡片交互层

## 七、核心规则

1. LLM 只生成计划，不执行
2. LLM 不重新计算 B 字段
3. LLM 不判断真实价格
4. LLM 不编造不存在的数据
5. LLM 失败必须降级
6. 不允许因为 LLM 失败导致 500
7. 不允许把 traceback 发给飞书用户
8. 不允许在 steps 中写入 key / token / 密钥 / 超长 prompt
9. 不允许擅自修改真实 .env
10. 如果需要真实 .env 同步，必须在回报里明确列出
11. 不允许调用刷新、重试、URL 替换、删除、改价、RPA 执行链路

## 八、action plan 输入字段

优先使用：

- product_name
- product_url
- source_site
- current_price
- last_price
- price_changed
- price_delta
- price_delta_percent
- price_probe_status
- price_probe_error
- price_source
- price_confidence
- price_page_type
- price_anomaly_status
- price_anomaly_reason
- action_priority
- action_category
- manual_review_required
- alert_candidate
- action_suggestion

字段名以仓库真实接口为准。

## 九、action plan 输出格式

飞书返回应该是老板可读文本。

建议结构：

1. 当前处理优先级判断
2. 第一批：必须人工复核的对象
3. 第二批：建议替换 URL 的对象
4. 第三批：建议手动重试采集的对象
5. 第四批：可暂缓观察的对象
6. 人工确认点
7. 不会自动处理的提醒

输出要求：

- 简洁
- 业务语言
- 不堆字段名
- 不编造
- 不承诺自动处理
- 不说“已经处理”除非数据明确显示
- 不把建议说成系统已经执行

## 十、典型计划口径

manual_review_required=true：

优先放入“人工复核”批次，不建议自动处理。

action_priority=high：

优先排在前面，提醒老板先看。

action_category=url_fix：

建议替换为商品详情页 URL 后再重新采集。

action_category=retry：

建议人工确认后执行手动重试采集。

price_source=mock_price / fallback_mock：

说明不能直接用于价格决策，建议人工复核或替换 URL。

price_page_type=search_page / listing_page：

说明页面可能不是商品详情页，建议先修正 URL。

price_probe_status=failed：

建议先重试采集；仍失败再人工检查链接或页面结构。

## 十一、steps 留痕

至少支持：

- llm_action_plan_started
- llm_action_plan_succeeded
- llm_action_plan_failed
- llm_action_plan_fallback_used

detail 可以包含：

- provider
- target_count
- high_priority_count
- manual_review_count
- url_fix_count
- retry_count
- observe_count
- fallback_used
- plan_focus
- plan_length
- error

禁止写入：

- API Key
- token
- 密钥
- 超长 prompt
- 完整敏感原始数据

## 十二、降级规则

LLM 调用失败时，降级为规则计划。

规则计划至少覆盖：

- 高优先级对象先处理
- 人工接管对象先复核
- URL 问题对象建议替换 URL
- 采集失败对象建议重试
- mock_price / fallback_mock 对象建议人工复核
- 低风险对象暂缓观察

## 十三、测试要求

至少覆盖：

- 操作计划类 intent 能识别
- A 能获取诊断字段和建议字段
- mock LLM 能生成操作计划
- LLM 失败能降级
- 无可处理对象返回友好提示
- 高风险建议不会自动执行
- steps 有 action plan 留痕
- P14-A fallback 不回归
- P14-B summary 不回归
- P14-C explanation 不回归
- P13-I / P13-K 字段不回归

## 十四、完成后回报格式

完成后必须回报：

A. 先读了哪些文件  
B. 操作计划数据从哪里获取  
C. 新增了哪个 intent  
D. LLM action plan service 如何设计  
E. action plan 输入字段有哪些  
F. action plan 输出格式是什么  
G. LLM 失败如何降级  
H. steps 如何留痕  
I. 是否修改 .env.example  
J. 真实 .env 需要人工同步哪些变量  
K. 改了哪些文件  
L. 执行了哪些测试  
M. 测试结果  
N. 是否可以进入飞书实机验收  