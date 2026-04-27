# P14-D 开发主线文档：LLM 操作计划生成

## 一、阶段名称

P14-D：LLM 操作计划生成

## 二、当前背景

P14-A 已完成并收口，系统已经可以在规则未命中时通过 LLM intent fallback 解析用户意图。

P14-B 已完成并收口，系统已经可以基于 P13 监控对象数据生成价格监控运营总结。

P14-C 已完成并收口，系统已经可以基于 P13 诊断字段生成异常原因解释。

当前 P14-D 不继续增强总结和解释能力。

P14-D 要做的是：

基于 P13 已有诊断字段、决策建议字段，以及 P14-B / P14-C 已证明可用的 LLM 文案能力，生成老板可读的“下一步处理计划”。

示例命令：

- 这些异常商品下一步怎么处理
- 给我一个处理计划
- 低可信对象接下来怎么处理
- 帮我安排一下处理顺序
- 哪些先人工复核，哪些先重试
- 给我一份今天价格监控的处理步骤

## 三、本轮唯一目标

只做：

LLM 操作计划生成。

固定链路：

飞书自然语言消息  
→ A 项目接收  
→ 识别操作计划类 intent  
→ A 调 B 获取已有监控对象、诊断字段、决策建议字段  
→ A 组织 action plan 输入  
→ 调用 LLM 生成老板可读操作计划  
→ LLM 失败时降级为规则计划  
→ 返回飞书  
→ task_steps 留痕  

## 四、P14-D 定位

LLM 负责：

- 根据已有字段归纳处理顺序
- 把对象分成不同处理组
- 生成下一步处理计划
- 说明每一步为什么这样排
- 标注需要人工确认的节点
- 给出保守执行建议

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
- 直接调用任何处理接口

## 五、A / B 项目边界

A 项目负责：

- 识别操作计划类 intent
- 调用 B 获取已有监控对象、诊断字段、决策建议字段
- 整理 action plan 输入
- 调用 LLM action plan service
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

A 只生成计划和展示。  
B 才做业务数据生成。  
LLM 不重新计算 B 的诊断字段和决策建议字段。  
LLM 不自动执行计划。

## 六、P14-D 优先使用字段

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

- 新增操作计划类 intent
- 新增 LLM action plan service
- 新增 mock provider
- 新增 action plan 输入 schema
- 新增 action plan 输出文本
- 新增 LLM 失败降级规则计划
- 新增 task_steps 留痕
- 新增飞书文本返回
- 新增测试
- 更新 .env.example
- 明确提示真实 .env 需要人工同步

## 八、本轮禁止做

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
- 不做 Playwright
- 不做浏览器渲染
- 不做代理池
- 不处理 Amazon 反爬
- 不改 B 采集逻辑
- 不重构 P14-A
- 不重构 P14-B
- 不重构 P14-C
- 不破坏 P13-I 诊断字段
- 不破坏 P13-K 决策建议字段
- 不破坏 P12 卡片交互层

## 九、操作计划输出要求

P14-D 最终返回给飞书的应该是老板可读文本，不是 JSON 原文。

建议结构：

1. 当前处理优先级判断
2. 第一批：必须先人工复核的对象
3. 第二批：建议替换 URL 的对象
4. 第三批：建议手动重试采集的对象
5. 第四批：可暂缓观察的对象
6. 人工确认点
7. 不会自动执行提醒

示例：

当前建议按“高优先级 + 人工接管优先”的顺序处理。

第一步：先处理高优先级且需要人工接管的对象。  
这些对象价格可信度低，不能直接用于价格决策，建议人工确认页面是否为商品详情页。

第二步：处理 URL 质量问题。  
如果对象来自搜索页、列表页或 mock_price，建议先替换为商品详情页 URL 后重新采集。

第三步：处理采集失败对象。  
对采集失败对象先手动重试；如果重试后仍失败，再人工检查页面结构或链接有效性。

系统不会自动刷新、自动重试、自动替换 URL、自动删除对象或自动改价。以上只是处理计划，需要人工确认后再执行。

## 十、LLM 输出约束

LLM 操作计划必须遵守：

- 不编造数据
- 不夸大结论
- 不承诺已经处理
- 不承诺自动处理
- 不判断真实价格
- 不输出 API Key / token / 密钥
- 不输出长 prompt
- 不把建议说成系统已经执行
- 不把 alert_candidate 说成真实告警已发送
- 不把 action_suggestion 当成已执行动作
- 不自动调用任何接口

## 十一、降级策略

LLM 调用失败时，必须降级。

允许降级为规则计划：

- manual_review_required=true：优先人工复核
- action_priority=high：优先处理
- action_category=url_fix：建议替换 URL 后重采集
- action_category=retry：建议手动重试采集
- price_source=mock_price / fallback_mock：建议人工复核，不直接决策
- price_page_type=search_page / listing_page：建议替换为商品详情页 URL
- price_probe_status=failed：建议重试或检查链接有效性

失败时不能：

- 报 500
- 把 traceback 发给飞书用户
- 中断任务系统
- 伪造 LLM 结果
- 自动执行任何动作

## 十二、steps 留痕

至少新增：

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

## 十三、环境变量建议

建议新增：

ENABLE_LLM_ACTION_PLAN=false  
LLM_ACTION_PLAN_PROVIDER=mock  
LLM_ACTION_PLAN_MODEL=  
LLM_ACTION_PLAN_TIMEOUT_SECONDS=10  

要求：

- 默认关闭
- mock provider 可测试
- 真实 provider 后续再接
- 如果需要真实 .env 同步，必须在回报里明确提示人工修改

## 十四、开发拆分

### P14-D.0：仓库锚定

先检查：

- A 侧当前如何获取 monitor targets
- P13-I 诊断字段在哪些接口返回
- P13-K 建议字段在哪些接口返回
- resolve_intent 是否已有计划类意图
- execute_action 如何接新 intent
- task_steps 如何写
- P14-B / P14-C LLM service 是否可复用 provider 结构

### P14-D.1：action plan 数据聚合

基于 B 返回数据生成 action plan input。

要求：

- 不改 B 业务逻辑
- 字段缺失时安全处理
- 统计高优先级数、人工接管数、URL 修正数、重试数、观察数
- 尽量提取前 3 个高优先级对象
- 只生成计划，不执行计划

### P14-D.2：LLM action plan service

新增 service：

- 支持 mock provider
- 支持 timeout
- 支持失败降级
- 输出老板可读文本

### P14-D.3：接入 execute_action

新增操作计划类 intent 对应执行分支。

要求：

- 调 B 获取数据
- 调 action plan service
- 返回飞书文本
- 写 steps
- 不触发任何自动处理动作

### P14-D.4：测试

至少覆盖：

- 操作计划类 intent 能识别
- 有高优先级 / 人工接管 / URL 修正 / 重试对象时生成计划
- LLM 失败时降级规则计划
- 无可处理对象时返回友好提示
- 不触发任何自动执行动作
- steps 有 action plan 留痕
- P14-A 不回归
- P14-B 不回归
- P14-C 不回归
- P13-I / P13-K 字段不回归

## 十五、最低通过标准

P14-D 通过标准：

- 能识别操作计划类命令
- 能获取监控对象、诊断字段、决策建议字段
- 能生成老板可读操作计划
- 操作计划包含处理顺序、对象分组、建议动作、人工确认点、不会自动处理提醒
- LLM 失败可降级
- 不自动执行任何动作
- task_steps 有留痕
- 不破坏 P14-A
- 不破坏 P14-B
- 不破坏 P14-C
- 不破坏 P13-I / P13-K
- .env.example 更新后明确提示真实 .env 需要人工同步

## 十六、完成后回报格式

Agent 完成后必须按以下格式回报：

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