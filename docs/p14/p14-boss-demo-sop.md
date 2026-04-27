# P14-A 老板演示 SOP：LLM 意图解析 fallback

## 一、演示目标

验证 P14-A 是否让飞书自然语言入口更智能。

重点不是让 LLM 自动干活，而是验证：

- 旧规则命令仍稳定
- 规则未命中的口语化表达可以触发 LLM fallback
- LLM 解析结果会被校验
- 低置信度会反问澄清
- 非法 intent 不执行
- 所有过程可在 task_steps 追踪

## 二、演示前提

P13 已完成。

P14-A 只做：

LLM 意图解析 fallback。

不做：

- 运营总结
- 异常解释
- 操作计划
- OCR
- 自动 URL 修复
- 自动 RPA
- 自动修改数据

## 三、启动前环境

进入 A 项目：

```bash
cd ~/feishu-rpa-commerce-agent
source venv/bin/activate 2>/dev/null || source .venv/bin/activate
```

建议环境变量：

```bash
export USE_SQLITE=true
export ENABLE_LLM_INTENT_FALLBACK=true
export LLM_INTENT_PROVIDER=mock
export LLM_INTENT_CONFIDENCE_THRESHOLD=0.75
```

检查状态：

```bash
git status --short
git branch --show-current
```

## 四、启动服务

启动 API：

```bash
./scripts/dev_run_api.sh
```

另开终端启动 worker：

```bash
cd ~/feishu-rpa-commerce-agent
source venv/bin/activate 2>/dev/null || source .venv/bin/activate
export USE_SQLITE=true
export ENABLE_LLM_INTENT_FALLBACK=true
export LLM_INTENT_PROVIDER=mock
./scripts/dev_run_worker.sh
```

另开终端启动飞书长连接：

```bash
cd ~/feishu-rpa-commerce-agent
source venv/bin/activate 2>/dev/null || source .venv/bin/activate
export USE_SQLITE=true
export ENABLE_LLM_INTENT_FALLBACK=true
export LLM_INTENT_PROVIDER=mock
./scripts/dev_run_feishu_longconn.sh
```

如果脚本名称和仓库不一致，以仓库实际脚本为准。

## 五、健康检查

```bash
curl -s http://127.0.0.1:8000/health | python3 -m json.tool
```

查看最近任务：

```bash
curl -s "http://127.0.0.1:8000/api/v1/tasks/?limit=3" | python3 -m json.tool
```

## 六、用例 1：旧规则命令不走 LLM

飞书发送：

```text
查看当前监控对象
```

期望：

- 正常走旧规则链路
- 不触发 LLM fallback
- 旧结果正常返回
- P12 / P13 不受影响

查询 steps：

```bash
curl -s "http://127.0.0.1:8000/api/v1/tasks/{task_id}/steps" | python3 -m json.tool
```

重点看：

- 是否没有误触发 llm_intent_fallback_succeeded
- 任务状态是否正常

## 七、用例 2：老板式表达触发 fallback

飞书发送：

```text
帮我看看哪些商品不太对
```

期望：

- 规则未命中后触发 LLM fallback
- LLM 解析为已有诊断 / 异常查询类 intent
- 返回老板可读结果
- steps 出现 llm_intent_fallback_started / succeeded
- 不修改任何数据

查询 steps：

```bash
curl -s "http://127.0.0.1:8000/api/v1/tasks/{task_id}/steps" | python3 -m json.tool
```

重点看：

- llm_intent
- confidence
- allowed
- slots
- result_summary

## 八、用例 3：失败对象重试表达

飞书发送：

```text
失败的那些再跑一遍
```

期望：

- 解析为已有手动重试类 intent
- 如果参数不足，返回澄清
- 如果参数足够，进入现有安全链路
- 不新增业务动作

## 九、用例 4：低置信度澄清

飞书发送：

```text
处理一下那个有问题的
```

期望：

- 不强行执行
- 返回澄清问题
- steps 有 low_confidence 或 failed 记录

示例返回：

```text
我还需要确认你要处理的是哪一类问题：价格异常、采集失败，还是 URL 不准确？
```

## 十、用例 5：非法动作拦截

飞书发送：

```text
把异常商品都删掉
```

期望：

- 不执行删除
- 不新增危险动作
- 不绕过确认
- steps 记录 blocked / not_allowed / failed

## 十一、验收查询

查看最近任务：

```bash
curl -s "http://127.0.0.1:8000/api/v1/tasks/?limit=10" | python3 -m json.tool
```

查看任务详情：

```bash
curl -s "http://127.0.0.1:8000/api/v1/tasks/{task_id}" | python3 -m json.tool
```

查看任务 steps：

```bash
curl -s "http://127.0.0.1:8000/api/v1/tasks/{task_id}/steps" | python3 -m json.tool
```

## 十二、老板演示话术

可以这样讲：

P14-A 不是让大模型直接操作后台，而是把大模型放在自然语言理解层。

原来的规则命令仍然走规则，保证稳定。

当用户用更口语化的方式说“帮我看看哪些商品不太对”时，系统会调用 LLM fallback，把这句话解析成已有的安全 intent 和参数。

解析成功后，仍然进入原来的任务系统和业务链路。

解析不确定时，系统不会乱执行，而是反问澄清。

所有 fallback 行为都会写入 task_steps，方便追踪和审计。

## 十三、通过标准

P14-A 实机通过标准：

- 旧规则命令正常
- 规则命中不调用 LLM
- 规则未命中触发 LLM fallback
- 高置信度进入现有链路
- 低置信度返回澄清
- 非 allowlist intent 不执行
- 高风险动作不绕过确认
- task_steps 可追踪
- 飞书返回老板可读
- P12 / P13 不退化