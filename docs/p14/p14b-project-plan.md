# P14-B 开发主线文档：LLM 监控对象运营总结

## 一、阶段名称

P14-B：LLM 监控对象运营总结

## 二、当前背景

P14-A 已完成并收口。

当前系统已经具备：

- 规则未命中时触发 LLM intent fallback
- allowlist
- confidence 阈值
- 低置信度澄清
- system.confirm_task 禁止由 LLM fallback 生成
- product.update_price 不绕过确认
- 飞书实机验收通过

P14-B 不继续增强 intent fallback。

P14-B 要做的是：

让老板通过飞书一句话获取当前价格监控整体情况总结。

示例命令：

- 总结一下当前价格监控情况
- 帮我看一下现在监控整体怎么样
- 当前有哪些商品需要重点处理
- 给我汇总一下价格监控状态
- 今天价格监控有什么问题

## 三、本轮唯一目标

只做：

LLM 监控对象运营总结。

固定链路：

飞书自然语言消息  
→ A 项目接收  
→ 识别总结类 intent  
→ A 调 B 获取已有监控对象状态数据  
→ A 组织 summary 输入  
→ 调用 LLM 生成老板可读总结  
→ 失败时降级为规则摘要  
→ 返回飞书  
→ task_steps 留痕  

## 四、P14-B 定位

LLM 负责：

- 汇总现状
- 分组归纳
- 提炼风险
- 解释整体情况
- 给出下一步建议

LLM 不负责：

- 自动执行
- 自动刷新
- 自动重试
- 自动替换 URL
- 自动删除对象
- 自动改价
- 自动告警
- 自动调用 RPA
- 重新计算 B 项目业务字段

## 五、A / B 项目边界

A 项目负责：

- 识别总结类 intent
- 调用 B 获取监控对象状态数据
- 整理 summary 输入
- 调用 LLM summary service
- 生成飞书文本返回
- task_steps 留痕

B 项目负责：

- monitor target 数据
- 价格采集状态
- 价格诊断字段
- URL 治理状态
- 决策建议字段

固定原则：

A 只汇总和展示。  
B 才做业务数据生成。  
LLM 不重新计算 B 的业务字段。

## 六、P14-B 优先使用字段

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

- 新增监控总结类 intent
- 新增 LLM monitor summary service
- 新增 mock provider
- 新增 summary 输入 schema
- 新增 summary 输出 schema
- 新增 LLM 失败降级规则摘要
- 新增 task_steps 留痕
- 新增飞书文本返回
- 新增测试
- 更新 .env.example
- 明确提示真实 .env 需要人工同步

## 八、本轮禁止做

禁止做：

- 不做 P14-C 异常解释
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
- 不做阈值配置 UI
- 不做 Playwright
- 不做浏览器渲染
- 不做代理池
- 不处理 Amazon 反爬
- 不改 B 采集逻辑
- 不重构 P14-A
- 不破坏 P13-K 决策建议字段
- 不破坏 P12 卡片交互层

## 九、summary 输出要求

P14-B 最终返回给飞书的应该是老板可读文本，不是 JSON 原文。

建议结构：

1. 当前总体情况
2. 重点风险
3. 需要人工处理的对象
4. 建议下一步动作
5. 不建议自动处理的提醒

示例：

当前共有 12 个监控对象。

整体看，价格监控状态一般，有 3 个对象需要优先处理。

其中 2 个对象价格可信度较低，主要原因是页面类型疑似为搜索页或列表页，建议优先替换为商品详情页 URL。

另外有 1 个对象采集失败，建议先手动重试；如果仍失败，再人工确认链接有效性。

当前不建议自动处理，建议先处理高优先级和人工接管对象。

## 十、LLM 输出约束

LLM 总结必须遵守：

- 不编造数据
- 不夸大结论
- 不承诺已经处理
- 不承诺自动处理
- 不暴露过多内部字段名
- 不输出 API Key / token / 密钥
- 不输出长 prompt
- 不把规则建议说成系统已经执行
- 不把 alert_candidate 说成真实告警已发送

## 十一、降级策略

LLM 调用失败时，必须降级。

允许降级为规则摘要：

- 当前监控对象总数
- 异常对象数量
- 低可信对象数量
- 人工接管对象数量
- 高优先级对象数量
- 简单建议

失败时不能：

- 报 500
- 把 traceback 发给飞书用户
- 中断任务系统
- 伪造 LLM 结果

## 十二、steps 留痕

至少新增：

- llm_monitor_summary_started
- llm_monitor_summary_succeeded
- llm_monitor_summary_failed
- llm_monitor_summary_fallback_used

detail 可以包含：

- provider
- target_count
- anomaly_count
- low_confidence_count
- manual_review_count
- high_priority_count
- summary_length
- fallback_used
- error

禁止写入：

- API Key
- token
- 密钥
- 超长 prompt
- 完整敏感原始数据

## 十三、环境变量建议

建议新增：

```env
ENABLE_LLM_MONITOR_SUMMARY=false
LLM_MONITOR_SUMMARY_PROVIDER=mock
LLM_MONITOR_SUMMARY_MODEL=
LLM_MONITOR_SUMMARY_TIMEOUT_SECONDS=10
```

要求：

- 默认关闭
- mock provider 可测试
- 真实 provider 后续再接
- 如果需要真实 .env 同步，必须在回报里明确提示人工修改

## 十四、开发拆分

### P14-B.0：仓库锚定

先检查：

- A 侧已有哪些 B client 方法
- 当前如何查询 monitor target
- P13-K 建议字段在哪些接口返回
- resolve_intent 是否已有总结类 intent
- execute_action 如何接新 intent
- task_steps 如何写
- P14-A LLM service 是否可复用 provider 结构

### P14-B.1：summary 数据聚合

基于 B 返回数据生成 summary input。

要求：

- 不改 B 业务逻辑
- 字段缺失时安全处理
- 统计总数、异常数、低可信数、人工接管数、高优先级数

### P14-B.2：LLM monitor summary service

新增 service：

- 支持 mock provider
- 支持 timeout
- 支持失败降级
- 输出老板可读文本

### P14-B.3：接入 execute_action

新增总结类 intent 对应执行分支。

要求：

- 调 B 获取数据
- 调 summary service
- 返回飞书文本
- 写 steps

### P14-B.4：测试

至少覆盖：

- 总结类 intent 能识别
- 有数据时生成 LLM 总结
- LLM 失败时降级规则摘要
- 无监控对象时返回友好提示
- 不触发任何自动执行动作
- steps 有 summary 留痕
- P14-A 不回归
- P13-K 不回归

## 十五、最低通过标准

P14-B 通过标准：

- 能识别总结类命令
- 能获取监控对象状态数据
- 能生成老板可读总结
- 总结包含关键统计
- LLM 失败可降级
- 不自动执行任何动作
- task_steps 有留痕
- 不破坏 P14-A
- 不破坏 P13-K
- .env.example 更新后明确提示真实 .env 需要人工同步

## 十六、完成后回报格式

Agent 完成后必须按以下格式回报：

A. 先读了哪些文件  
B. 当前监控对象数据从哪里获取  
C. 新增了哪个 intent  
D. LLM summary service 如何设计  
E. summary 输入字段有哪些  
F. summary 输出格式是什么  
G. LLM 失败如何降级  
H. steps 如何留痕  
I. 是否修改 .env.example  
J. 真实 .env 需要人工同步哪些变量  
K. 改了哪些文件  
L. 执行了哪些测试  
M. 测试结果  
N. 是否可以进入飞书实机验收  