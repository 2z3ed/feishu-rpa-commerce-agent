# P14-C 开发主线文档：LLM 异常原因解释

## 一、阶段名称

P14-C：LLM 异常原因解释

## 二、当前背景

P14-A 已完成并收口，系统已经可以在规则未命中时通过 LLM intent fallback 解析用户意图。

P14-B 已完成并收口，系统已经可以基于 P13 监控对象数据生成价格监控运营总结，并支持：

- 总体总结
- 健康度检查
- 重点处理对象总结
- provider 失败降级
- 飞书实机验收

当前 P14-C 不继续增强总结能力。

P14-C 要做的是：

把 P13 已有的诊断字段翻译成老板能看懂的异常原因解释。

例如：

- mock_price 是什么意思
- fallback_mock 为什么不能直接用
- 为什么这个对象价格不准
- 为什么这些对象低可信
- search_page / listing_page 为什么要换 URL
- 为什么需要人工接管
- 为什么不建议自动处理

## 三、本轮唯一目标

只做：

LLM 异常原因解释。

固定链路：

飞书自然语言消息  
→ A 项目接收  
→ 识别异常解释类 intent  
→ A 调 B 获取已有监控对象与诊断字段  
→ A 组织 explanation 输入  
→ 调用 LLM 生成老板可读解释  
→ LLM 失败时降级为规则解释  
→ 返回飞书  
→ task_steps 留痕  

## 四、P14-C 定位

LLM 负责：

- 把技术字段翻译成业务语言
- 解释异常原因
- 解释对价格判断的影响
- 解释为什么需要人工处理
- 给出保守处理建议

LLM 不负责：

- 自动执行
- 自动刷新
- 自动重试
- 自动替换 URL
- 自动删除对象
- 自动改价
- 自动告警
- 自动调用 RPA
- 重新计算 B 项目诊断字段
- 判断真实价格

## 五、A / B 项目边界

A 项目负责：

- 识别异常解释类 intent
- 调用 B 获取已有监控对象与诊断字段
- 整理 explanation 输入
- 调用 LLM explanation service
- 生成飞书文本返回
- task_steps 留痕

B 项目负责：

- monitor target 数据
- 价格采集状态
- 价格可信度
- 页面类型
- 异常状态
- 异常原因
- URL 治理状态
- 决策建议字段

固定原则：

A 只解释和展示。  
B 才做业务数据生成。  
LLM 不重新计算 B 的诊断字段。

## 六、P14-C 优先使用字段

优先使用 P13 已有字段：

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

如果字段名与仓库实际不一致，以仓库真实代码为准。

## 七、本轮允许做

允许做：

- 新增异常解释类 intent
- 新增 LLM anomaly explanation service
- 新增 mock provider
- 新增 explanation 输入 schema
- 新增 explanation 输出文本
- 新增 LLM 失败降级规则解释
- 新增 task_steps 留痕
- 新增飞书文本返回
- 新增测试
- 更新 .env.example
- 明确提示真实 .env 需要人工同步

## 八、本轮禁止做

禁止做：

- 不做 P14-D 操作计划
- 不做 P15 OCR
- 不做发票识别
- 不做自动刷新
- 不做自动重试
- 不做自动替换 URL
- 不做自动删除对象
- 不做自动改价
- 不做主动通知
- 不做真正告警系统
- 不做 Playwright
- 不做浏览器渲染
- 不做代理池
- 不处理 Amazon 反爬
- 不改 B 采集逻辑
- 不重构 P14-A
- 不重构 P14-B
- 不破坏 P13-I 诊断字段
- 不破坏 P13-K 决策建议字段
- 不破坏 P12 卡片交互层

## 九、异常解释输出要求

P14-C 最终返回给飞书的应该是老板可读文本，不是 JSON 原文。

建议结构：

1. 当前问题是什么
2. 为什么会出现这个问题
3. 对价格判断有什么影响
4. 建议怎么处理
5. 自动处理提醒

示例：

这个对象当前价格可信度较低。

主要原因是系统采集到的页面更像搜索页或列表页，不是稳定的商品详情页。因此页面里的价格可能不是目标商品价格，不能直接作为真实价格判断。

建议优先替换为商品详情页 URL 后重新采集。如果重新采集后仍然低可信，再人工确认该链接是否可用。

系统不会自动替换 URL，也不会自动改价，需要人工确认后再执行。

## 十、LLM 输出约束

LLM 异常解释必须遵守：

- 不编造数据
- 不夸大结论
- 不承诺已经处理
- 不承诺自动处理
- 不判断真实价格
- 不输出 API Key / token / 密钥
- 不输出长 prompt
- 不把规则建议说成系统已经执行
- 不把 alert_candidate 说成真实告警已发送
- 不把 fallback_mock / mock_price 说成真实价格来源

## 十一、降级策略

LLM 调用失败时，必须降级。

允许降级为规则解释：

- price_confidence 低：解释为价格可信度不足，建议人工复核
- price_page_type 是 search_page / listing_page：解释为页面类型不是商品详情页，建议替换 URL
- price_source 是 mock_price / fallback_mock：解释为兜底价格，不应作为真实价格决策
- price_probe_status 是 failed：解释为采集失败，建议重试或人工检查链接
- manual_review_required 为 true：解释为需要人工接管

失败时不能：

- 报 500
- 把 traceback 发给飞书用户
- 中断任务系统
- 伪造 LLM 结果

## 十二、steps 留痕

至少新增：

- llm_anomaly_explanation_started
- llm_anomaly_explanation_succeeded
- llm_anomaly_explanation_failed
- llm_anomaly_explanation_fallback_used

detail 可以包含：

- provider
- target_count
- explained_count
- anomaly_count
- low_confidence_count
- fallback_used
- explanation_focus
- explanation_length
- error

禁止写入：

- API Key
- token
- 密钥
- 超长 prompt
- 完整敏感原始数据

## 十三、环境变量建议

建议新增：

ENABLE_LLM_ANOMALY_EXPLANATION=false  
LLM_ANOMALY_EXPLANATION_PROVIDER=mock  
LLM_ANOMALY_EXPLANATION_MODEL=  
LLM_ANOMALY_EXPLANATION_TIMEOUT_SECONDS=10  

要求：

- 默认关闭
- mock provider 可测试
- 真实 provider 后续再接
- 如果需要真实 .env 同步，必须在回报里明确提示人工修改

## 十四、开发拆分

### P14-C.0：仓库锚定

先检查：

- A 侧当前如何获取 monitor targets
- P13-I 诊断字段在哪些接口返回
- P13-K 建议字段在哪些接口返回
- resolve_intent 是否已有异常解释类意图
- execute_action 如何接新 intent
- task_steps 如何写
- P14-A / P14-B LLM service 是否可复用 provider 结构

### P14-C.1：explanation 数据聚合

基于 B 返回数据生成 explanation input。

要求：

- 不改 B 业务逻辑
- 字段缺失时安全处理
- 统计异常数、低可信数、采集失败数、人工接管数
- 尽量提取前 3 个典型异常对象

### P14-C.2：LLM anomaly explanation service

新增 service：

- 支持 mock provider
- 支持 timeout
- 支持失败降级
- 输出老板可读文本

### P14-C.3：接入 execute_action

新增异常解释类 intent 对应执行分支。

要求：

- 调 B 获取数据
- 调 explanation service
- 返回飞书文本
- 写 steps
- 不触发任何自动处理动作

### P14-C.4：测试

至少覆盖：

- 异常解释类 intent 能识别
- 有低可信 / mock_price / search_page 时生成解释
- LLM 失败时降级规则解释
- 无异常对象时返回友好提示
- 不触发任何自动执行动作
- steps 有 explanation 留痕
- P14-A 不回归
- P14-B 不回归
- P13-I / P13-K 字段不回归

## 十五、最低通过标准

P14-C 通过标准：

- 能识别异常解释类命令
- 能获取监控对象诊断字段
- 能生成老板可读异常解释
- 解释包含问题、原因、影响、建议、不会自动处理提醒
- LLM 失败可降级
- 不自动执行任何动作
- task_steps 有留痕
- 不破坏 P14-A
- 不破坏 P14-B
- 不破坏 P13-I / P13-K
- .env.example 更新后明确提示真实 .env 需要人工同步

## 十六、完成后回报格式

Agent 完成后必须按以下格式回报：

A. 先读了哪些文件  
B. 异常解释数据从哪里获取  
C. 新增了哪个 intent  
D. LLM explanation service 如何设计  
E. explanation 输入字段有哪些  
F. explanation 输出格式是什么  
G. LLM 失败如何降级  
H. steps 如何留痕  
I. 是否修改 .env.example  
J. 真实 .env 需要人工同步哪些变量  
K. 改了哪些文件  
L. 执行了哪些测试  
M. 测试结果  
N. 是否可以进入飞书实机验收  