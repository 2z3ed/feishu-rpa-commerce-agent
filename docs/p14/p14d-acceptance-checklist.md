# P14-D 验收清单：LLM 操作计划生成

## 一、阶段信息

阶段：

P14-D：LLM 操作计划生成

验收目标：

基于 P13 已有采集状态、诊断字段和决策建议字段，生成老板可读的下一步操作计划。

## 二、文档验收

必须存在：

- AGENTS.md 当前阶段入口
- docs/p14/p14d-project-plan.md
- docs/p14/P14D-agent-prompt.md
- docs/p14/p14d-boss-demo-sop.md
- docs/p14/p14d-acceptance-checklist.md

检查命令：

ls -la docs/p14

通过标准：

- 文件存在
- 口径是 P14-D
- 没有混入 P15

## 三、配置验收

建议支持：

ENABLE_LLM_ACTION_PLAN=false  
LLM_ACTION_PLAN_PROVIDER=mock  
LLM_ACTION_PLAN_TIMEOUT_SECONDS=10  

通过标准：

- 默认关闭
- mock provider 可测试
- .env.example 可更新
- 真实 .env 需要人工同步时必须明确提示

## 四、intent 识别验收

测试命令：

这些异常商品下一步怎么处理  
给我一个处理计划  
低可信对象接下来怎么处理  
帮我安排一下处理顺序  
哪些先重试，哪些先换 URL  

通过标准：

- 能识别为操作计划类 intent
- 能进入 action plan 执行分支
- 不误触发刷新、重试、改价、删除、URL 替换

## 五、数据获取验收

通过标准：

- A 能从 B 获取监控对象诊断字段
- 数据包含或兼容 P13-I 诊断字段
- 数据包含或兼容 P13-K 决策建议字段
- 字段缺失时不报错

## 六、action plan 内容验收

计划至少包含：

- 当前处理优先级判断
- 必须人工复核的对象或分组
- 建议替换 URL 的对象或分组
- 建议手动重试采集的对象或分组
- 可暂缓观察的对象或分组
- 人工确认点
- 不会自动处理提醒

输出要求：

- 老板可读
- 不堆字段名
- 不编造数据
- 不承诺自动处理
- 不说已经执行动作
- 不暴露内部敏感信息

## 七、降级验收

模拟 LLM 失败。

通过标准：

- 降级为规则计划
- 不报 500
- 不把 traceback 发给飞书
- task_steps 有 fallback_used 或 failed
- 任务状态符合现有语义

## 八、无可处理对象验收

当没有需要处理的对象时：

通过标准：

- 返回友好提示
- 不报 500
- 不调用危险动作
- steps 有记录

## 九、steps 留痕验收

至少能看到：

- llm_action_plan_started
- llm_action_plan_succeeded
- llm_action_plan_failed
- llm_action_plan_fallback_used

detail 不得包含：

- API Key
- token
- 密钥
- 超长 prompt
- 完整敏感原始数据

## 十、禁止动作验收

P14-D 不能触发：

- 自动刷新
- 自动重试
- 自动替换 URL
- 自动删除对象
- 自动改价
- 自动告警
- RPA 执行

## 十一、测试验收

建议执行：

pytest -q tests/test_p14d_llm_action_plan.py  
pytest -q tests/test_p14c_llm_anomaly_explanation.py  
pytest -q tests/test_p14b_llm_monitor_summary.py  
pytest -q tests/test_p14a_llm_intent_fallback.py  
pytest -q tests/test_p10_b_query_integration.py tests/test_resolve_intent_multi_platform.py  

如果全量失败，必须说明：

- 失败文件
- 失败原因
- 是否与 P14-D 有关

## 十二、飞书实机验收

至少测试：

这些异常商品下一步怎么处理  
帮我安排一下处理顺序  
低可信对象接下来怎么处理  
哪些先重试，哪些先换 URL  

模拟 LLM 失败后再测试：

这些异常商品下一步怎么处理  

通过标准：

- 有计划
- 有处理顺序
- 有对象分组
- 有人工确认点
- 不自动执行
- LLM 失败能降级
- /tasks 和 /steps 可查

## 十三、禁止收口条件

出现以下情况，不允许收口：

- P14-A 回归失败
- P14-B 回归失败
- P14-C 回归失败
- P13-I / P13-K 字段回归失败
- 操作计划命令触发了自动刷新 / 重试 / URL 替换 / 改价 / 删除
- LLM 失败时报 500
- 飞书用户看到 traceback
- steps 没有留痕
- 计划编造数据
- 计划承诺已经自动处理
- agent 没有说明真实 .env 需要人工同步哪些变量

## 十四、最终收口回报模板

A. 文档是否齐全  
B. 配置是否默认关闭  
C. 操作计划类 intent 是否可识别  
D. A 是否能获取诊断字段和建议字段  
E. action plan 是否包含处理顺序、对象分组、建议动作、人工确认点  
F. LLM 失败是否能降级  
G. 是否没有触发自动执行动作  
H. steps 是否留痕  
I. 是否修改 .env.example  
J. 真实 .env 是否需要人工同步  
K. 测试是否通过  
L. 飞书实机是否通过  
M. 是否允许 P14-D 收口  