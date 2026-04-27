# P14-C 验收清单：LLM 异常原因解释

## 一、阶段信息

阶段：

P14-C：LLM 异常原因解释

验收目标：

基于 P13 已有采集状态、诊断字段和决策建议字段，生成老板可读的异常原因解释。

## 二、文档验收

必须存在：

- AGENTS.md 当前阶段入口
- docs/p14/p14c-project-plan.md
- docs/p14/P14C-agent-prompt.md
- docs/p14/p14c-boss-demo-sop.md
- docs/p14/p14c-acceptance-checklist.md

检查命令：

ls -la docs/p14

通过标准：

- 文件存在
- 口径是 P14-C
- 没有混入 P14-D / P15

## 三、配置验收

建议支持：

ENABLE_LLM_ANOMALY_EXPLANATION=false  
LLM_ANOMALY_EXPLANATION_PROVIDER=mock  
LLM_ANOMALY_EXPLANATION_TIMEOUT_SECONDS=10  

通过标准：

- 默认关闭
- mock provider 可测试
- .env.example 可更新
- 真实 .env 需要人工同步时必须明确提示

## 四、intent 识别验收

测试命令：

为什么这些商品价格不准  
解释一下低可信对象的问题  
mock_price 是什么意思，为什么不能直接用  
为什么这些商品需要人工处理  

通过标准：

- 能识别为异常解释类 intent
- 能进入 explanation 执行分支
- 不误触发刷新、重试、改价、删除

## 五、数据获取验收

通过标准：

- A 能从 B 获取监控对象诊断字段
- 数据包含或兼容 P13-I 诊断字段
- 数据包含或兼容 P13-K 决策建议字段
- 字段缺失时不报错

## 六、explanation 内容验收

解释至少包含：

- 当前问题是什么
- 为什么会出现
- 对价格判断有什么影响
- 建议怎么处理
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

- 降级为规则解释
- 不报 500
- 不把 traceback 发给飞书
- task_steps 有 fallback_used 或 failed
- 任务状态符合现有语义

## 八、无异常数据验收

当没有异常对象时：

通过标准：

- 返回友好提示
- 不报 500
- 不调用危险动作
- steps 有记录

## 九、steps 留痕验收

至少能看到：

- llm_anomaly_explanation_started
- llm_anomaly_explanation_succeeded
- llm_anomaly_explanation_failed
- llm_anomaly_explanation_fallback_used

detail 不得包含：

- API Key
- token
- 密钥
- 超长 prompt
- 完整敏感原始数据

## 十、禁止动作验收

P14-C 不能触发：

- 自动刷新
- 自动重试
- 自动替换 URL
- 自动删除对象
- 自动改价
- 自动告警
- RPA 执行

## 十一、测试验收

建议执行：

pytest -q tests/test_p14c_llm_anomaly_explanation.py  
pytest -q tests/test_p14b_llm_monitor_summary.py  
pytest -q tests/test_p14a_llm_intent_fallback.py  
pytest -q tests/test_p10_b_query_integration.py tests/test_resolve_intent_multi_platform.py  

如果全量失败，必须说明：

- 失败文件
- 失败原因
- 是否与 P14-C 有关

## 十二、飞书实机验收

至少测试：

为什么这些商品价格不准  
解释一下低可信对象的问题  
mock_price 是什么意思，为什么不能直接用  
为什么这些商品需要人工处理  

模拟 LLM 失败后再测试：

为什么这些商品价格不准  

通过标准：

- 有解释
- 有原因
- 有影响说明
- 有建议
- 不自动执行
- LLM 失败能降级
- /tasks 和 /steps 可查

## 十三、禁止收口条件

出现以下情况，不允许收口：

- P14-A 回归失败
- P14-B 回归失败
- P13-I / P13-K 字段回归失败
- 异常解释命令触发了自动刷新 / 重试 / 改价 / 删除
- LLM 失败时报 500
- 飞书用户看到 traceback
- steps 没有留痕
- 解释编造数据
- 解释承诺已经自动处理
- agent 没有说明真实 .env 需要人工同步哪些变量

## 十四、最终收口回报模板

A. 文档是否齐全  
B. 配置是否默认关闭  
C. 异常解释类 intent 是否可识别  
D. A 是否能获取诊断字段  
E. explanation 是否包含问题、原因、影响、建议  
F. LLM 失败是否能降级  
G. 是否没有触发自动执行动作  
H. steps 是否留痕  
I. 是否修改 .env.example  
J. 真实 .env 是否需要人工同步  
K. 测试是否通过  
L. 飞书实机是否通过  
M. 是否允许 P14-C 收口  