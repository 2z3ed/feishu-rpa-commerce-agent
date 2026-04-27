# P14-B 老板演示 SOP：LLM 监控对象运营总结

## 一、演示目标

验证 P14-B 是否能基于已有监控对象数据，生成老板可读的价格监控总结。

重点不是证明 LLM 能自动处理问题，而是证明：

- 系统能汇总当前监控情况
- 能识别主要风险
- 能指出需要人工处理的对象类型
- 能给出下一步建议
- 不自动执行任何动作
- LLM 失败时能降级
- task_steps 可追踪

## 二、演示前提

P14-A 已完成并收口。

P14-B 只做：

LLM 监控对象运营总结。

不做：

- 自动刷新
- 自动重试
- 自动替换 URL
- 自动删除对象
- 自动改价
- 主动告警
- OCR
- RPA

## 三、启动前环境

进入 A 项目：

```bash
cd ~/feishu-rpa-commerce-agent
source venv/bin/activate 2>/dev/null || source .venv/bin/activate
```

建议环境变量：

```bash
export USE_SQLITE=true
export ENABLE_LLM_MONITOR_SUMMARY=true
export LLM_MONITOR_SUMMARY_PROVIDER=mock
```

如果 P14-B 同时依赖 P14-A fallback 识别口语化总结命令，也需要：

```bash
export ENABLE_LLM_INTENT_FALLBACK=true
export LLM_INTENT_PROVIDER=mock
```

注意：

agent 不应擅自修改真实 .env。  
如果需要持久化环境变量，由用户人工同步。

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
export ENABLE_LLM_MONITOR_SUMMARY=true
export LLM_MONITOR_SUMMARY_PROVIDER=mock
./scripts/dev_run_worker.sh
```

另开终端启动飞书长连接：

```bash
cd ~/feishu-rpa-commerce-agent
source venv/bin/activate 2>/dev/null || source .venv/bin/activate
export USE_SQLITE=true
export ENABLE_LLM_MONITOR_SUMMARY=true
export LLM_MONITOR_SUMMARY_PROVIDER=mock
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

## 六、用例 1：标准总结命令

飞书发送：

```text
总结一下当前价格监控情况
```

期望：

- 识别为监控总结类 intent
- 调用 B 获取监控数据
- 生成老板可读总结
- steps 有 llm_monitor_summary_started / succeeded
- 不执行刷新、重试、替换 URL、删除、改价

## 七、用例 2：口语化总结命令

飞书发送：

```text
帮我看一下现在监控整体怎么样
```

期望：

- 能识别为监控总结类 intent
- 如果依赖 P14-A fallback，则 fallback 能正确解析
- 返回总结文本
- 不执行任何处理动作

## 八、用例 3：重点处理对象总结

飞书发送：

```text
当前有哪些商品需要重点处理
```

期望：

- 总结中体现高优先级对象、人工接管对象或提醒候选对象
- 不自动处理
- 不发送主动告警

## 九、用例 4：无数据场景

如果当前没有监控对象，飞书发送：

```text
总结一下当前价格监控情况
```

期望：

- 返回友好提示
- 不报 500
- steps 有记录

## 十、用例 5：LLM 失败降级

通过 mock provider 或测试配置模拟 LLM 失败。

飞书发送：

```text
总结一下当前价格监控情况
```

期望：

- 降级为规则摘要
- steps 有 llm_monitor_summary_fallback_used 或 failed
- 飞书不显示 traceback

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

P14-B 不是让大模型自动处理价格问题，而是让它基于系统已有的监控对象、采集状态、诊断字段和决策建议字段，生成老板能快速看懂的运营总结。

系统不会因为总结结果自动刷新、自动改价或自动替换 URL。

如果 LLM 不可用，系统会降级成规则摘要，保证飞书仍然能收到可读结果。

## 十三、通过标准

P14-B 实机通过标准：

- 标准总结命令可用
- 口语化总结命令可用
- 能生成老板可读总结
- 总结包含关键统计和风险建议
- LLM 不编造数据
- LLM 不承诺自动处理
- LLM 失败能降级
- task_steps 可追踪
- 不破坏 P14-A
- 不破坏 P13-K