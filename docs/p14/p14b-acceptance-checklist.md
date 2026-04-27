# P14-B 验收清单：LLM 监控对象运营总结

## 一、阶段信息

阶段：

P14-B：LLM 监控对象运营总结

验收目标：

基于 P13 已有监控对象、诊断字段和决策建议字段，生成老板可读的价格监控运营总结。

## 二、文档验收

必须存在：

- AGENTS.md 当前阶段入口
- docs/p14/p14b-project-plan.md
- docs/p14/P14B-agent-prompt.md
- docs/p14/p14b-boss-demo-sop.md
- docs/p14/p14b-acceptance-checklist.md

检查命令：

```bash
ls -la docs/p14
```

通过标准：

- 文件存在
- 口径是 P14-B
- 没有混入 P14-C / P14-D / P15

## 三、配置验收

建议支持：

```env
ENABLE_LLM_MONITOR_SUMMARY=false
LLM_MONITOR_SUMMARY_PROVIDER=mock
LLM_MONITOR_SUMMARY_TIMEOUT_SECONDS=10
```

通过标准：

- 默认关闭
- mock provider 可测试
- .env.example 可更新
- 真实 .env 需要人工同步时必须明确提示

## 四、intent 识别验收

测试命令：

```text
总结一下当前价格监控情况
```

```text
帮我看一下现在监控整体怎么样
```

```text
当前有哪些商品需要重点处理
```

通过标准：

- 能识别为监控总结类 intent
- 能进入 summary 执行分支
- 不误触发刷新、重试、改价、删除

## 五、数据获取验收

通过标准：

- A 能从 B 获取监控对象状态数据
- 数据包含或兼容 P13 诊断字段
- 数据包含或兼容 P13-K 决策建议字段
- 字段缺失时不报错

## 六、summary 内容验收

总结至少包含：

- 当前监控对象总数
- 异常对象数量
- 低可信对象数量
- 人工接管对象数量
- 高优先级对象数量
- 下一步建议

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

- 降级为规则摘要
- 不报 500
- 不把 traceback 发给飞书
- task_steps 有 fallback_used 或 failed
- 任务状态符合现有语义

## 八、无数据验收

当没有监控对象时：

通过标准：

- 返回友好提示
- 不报 500
- 不调用危险动作
- steps 有记录

## 九、steps 留痕验收

至少能看到：

- llm_monitor_summary_started
- llm_monitor_summary_succeeded
- llm_monitor_summary_failed
- llm_monitor_summary_fallback_used

detail 不得包含：

- API Key
- token
- 密钥
- 超长 prompt
- 完整敏感原始数据

## 十、禁止动作验收

P14-B 不能触发：

- 自动刷新
- 自动重试
- 自动替换 URL
- 自动删除对象
- 自动改价
- 自动告警
- RPA 执行

## 十一、测试验收

建议执行：

```bash
pytest -q tests/test_p14b_llm_monitor_summary.py
pytest -q tests/test_p14a_llm_intent_fallback.py
pytest -q tests/test_p10_b_query_integration.py tests/test_resolve_intent_multi_platform.py
pytest -q
```

如果全量失败，必须说明：

- 失败文件
- 失败原因
- 是否与 P14-B 有关

## 十二、飞书实机验收

至少测试：

```text
总结一下当前价格监控情况
```

```text
帮我看一下现在监控整体怎么样
```

```text
当前有哪些商品需要重点处理
```

模拟 LLM 失败后再测试：

```text
总结一下当前价格监控情况
```

通过标准：

- 有总结
- 有统计
- 有建议
- 不自动执行
- LLM 失败能降级
- /tasks 和 /steps 可查

## 十三、禁止收口条件

出现以下情况，不允许收口：

- P14-A 回归失败
- P13-K 字段回归失败
- 总结命令触发了自动刷新 / 重试 / 改价 / 删除
- LLM 失败时报 500
- 飞书用户看到 traceback
- steps 没有留痕
- 总结编造数据
- 总结承诺已经自动处理
- agent 没有说明真实 .env 需要人工同步哪些变量

## 十四、最终收口回报模板

A. 文档是否齐全  
B. 配置是否默认关闭  
C. 总结类 intent 是否可识别  
D. A 是否能获取监控对象数据  
E. summary 是否包含关键统计  
F. LLM 失败是否能降级  
G. 是否没有触发自动执行动作  
H. steps 是否留痕  
I. 是否修改 .env.example  
J. 真实 .env 是否需要人工同步  
K. 测试是否通过  
L. 飞书实机是否通过  
M. 是否允许 P14-B 收口  