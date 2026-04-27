# P14-A 验收清单：LLM 意图解析 fallback

## 一、阶段信息

阶段：

P14-A：LLM 意图解析 fallback

验收目标：

在不破坏现有规则系统的前提下，让规则未命中的自然语言表达可以通过 LLM fallback 解析为已有 intent / slots，并进入现有安全链路。

## 二、文档验收

必须存在：

- AGENTS.md 当前阶段入口
- docs/p14/p14-project-plan.md
- docs/p14/P14-agent-prompt.md
- docs/p14/p14-boss-demo-sop.md
- docs/p14/p14-acceptance-checklist.md

检查命令：

```bash
ls -la docs/p14
```

通过标准：

- 文件存在
- 口径是 P14-A
- 没有混入 P14-B / P14-C / P14-D / P15

## 三、配置验收

必须支持：

```env
ENABLE_LLM_INTENT_FALLBACK=false
LLM_INTENT_PROVIDER=mock
LLM_INTENT_CONFIDENCE_THRESHOLD=0.75
```

通过标准：

- 默认关闭
- 关闭时旧链路不变
- 开启时只在规则未命中时调用 fallback
- mock provider 可测试

## 四、规则命中保护

测试命令：

```text
查看当前监控对象
```

通过标准：

- 走旧规则链路
- 不误触发 LLM fallback
- 返回结果正常
- P12 / P13 不受影响

## 五、规则未命中 fallback

测试命令：

```text
帮我看看哪些商品不太对
```

通过标准：

- 规则未命中后触发 LLM fallback
- LLM 输出结构化 JSON
- intent 在 allowlist 内
- confidence 达标
- slots 可被现有链路使用
- 返回老板可读结果
- task_steps 有 fallback 成功记录

## 六、低置信度处理

测试命令：

```text
处理一下那个有问题的
```

通过标准：

- 不强行执行
- 返回澄清问题
- task_steps 有 low_confidence 或 failed 记录
- 不修改数据

## 七、非法 intent 拦截

模拟 LLM 返回：

```json
{
  "intent": "dangerous.delete_all_monitors",
  "slots": {},
  "confidence": 0.99,
  "needs_confirmation": false,
  "clarification_question": "",
  "reason": "用户要求删除全部异常对象"
}
```

通过标准：

- 不执行
- 不删除数据
- task_steps 记录 blocked / not_allowed / failed
- 返回澄清或拒绝

## 八、LLM 异常回退

需要覆盖：

- timeout
- provider error
- 非 JSON 输出
- JSON schema 缺字段
- confidence 非数字
- intent 不在 allowlist
- slots 不合法

通过标准：

- 不报 500
- 不把 traceback 发给飞书用户
- 不执行危险动作
- 回到 unknown / clarification
- steps 有 failed 记录

## 九、高风险动作保护

测试命令：

```text
把异常商品都删掉
```

通过标准：

- 不直接执行
- 不新增危险业务动作
- 不绕过确认链路
- 不修改数据

## 十、steps 留痕

至少能看到以下之一：

- llm_intent_fallback_started
- llm_intent_fallback_succeeded
- llm_intent_fallback_failed
- llm_intent_fallback_skipped
- llm_intent_fallback_low_confidence

detail 不得包含：

- API Key
- token
- 密钥
- 超长 prompt

## 十一、测试验收

建议执行：

```bash
pytest -q tests/test_p14a_llm_intent_fallback.py
pytest -q
```

如果全量测试失败，必须说明：

- 失败文件
- 失败原因
- 是否与 P14-A 有关

## 十二、飞书实机验收

至少测试：

```text
查看当前监控对象
```

```text
帮我看看哪些商品不太对
```

```text
失败的那些再跑一遍
```

```text
处理一下那个有问题的
```

```text
把异常商品都删掉
```

通过标准：

- 旧命令稳定
- fallback 可触发
- 低置信度会澄清
- 危险命令不执行
- 飞书返回老板可读
- /tasks 和 /steps 可查

## 十三、禁止收口条件

出现以下情况，不允许收口：

- P12 / P13 回归失败
- 规则命中命令被 LLM 改坏
- LLM 默认开启并影响旧链路
- LLM 直接执行高风险动作
- LLM 输出未校验就进入 execute_action
- 没有 allowlist
- 没有 confidence 阈值
- 没有 task_steps 留痕
- 低置信度仍强行执行
- 非 JSON 输出仍执行
- 飞书用户看到 traceback

## 十四、最终收口回报模板

A. 文档是否齐全  
B. 配置是否默认关闭  
C. 规则命中是否不走 LLM  
D. 规则未命中是否触发 fallback  
E. 高置信度是否进入现有链路  
F. 低置信度是否返回澄清  
G. 非法 intent 是否拦截  
H. steps 是否留痕  
I. 测试是否通过  
J. 飞书实机是否通过  
K. 是否允许 P14-A 收口  