# P14-D 老板演示 SOP：LLM 操作计划生成

## 一、演示目标

验证 P14-D 是否能基于已有诊断字段和决策建议字段，生成老板能看懂的下一步操作计划。

重点不是证明 LLM 能自动处理问题，而是证明：

- 系统能给出处理顺序
- 系统能分组安排处理对象
- 系统能说明每一步为什么这样处理
- 系统能提示需要人工确认
- 系统不会自动执行任何动作
- LLM 失败时能降级
- task_steps 可追踪

## 二、演示前提

P14-A 已完成并收口。  
P14-B 已完成并收口。  
P14-C 已完成并收口。  

P14-D 只做：

LLM 操作计划生成。

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

cd ~/feishu-rpa-commerce-agent  
source venv/bin/activate 2>/dev/null || source .venv/bin/activate  

建议环境变量：

export USE_SQLITE=true  
export ENABLE_LLM_ACTION_PLAN=true  
export LLM_ACTION_PLAN_PROVIDER=mock  

如果 P14-D 口语化命令依赖 P14-A fallback，也需要：

export ENABLE_LLM_INTENT_FALLBACK=true  
export LLM_INTENT_PROVIDER=mock  

注意：

agent 不应擅自修改真实 .env。  
如果需要持久化环境变量，由用户人工同步。

## 四、启动服务

启动 API：

./scripts/dev_run_api.sh

另开终端启动 worker：

cd ~/feishu-rpa-commerce-agent  
source venv/bin/activate 2>/dev/null || source .venv/bin/activate  
export USE_SQLITE=true  
export ENABLE_LLM_ACTION_PLAN=true  
export LLM_ACTION_PLAN_PROVIDER=mock  
./scripts/dev_run_worker.sh

另开终端启动飞书长连接：

cd ~/feishu-rpa-commerce-agent  
source venv/bin/activate 2>/dev/null || source .venv/bin/activate  
export USE_SQLITE=true  
export ENABLE_LLM_ACTION_PLAN=true  
export LLM_ACTION_PLAN_PROVIDER=mock  
./scripts/dev_run_feishu_longconn.sh

如果脚本名称和仓库不一致，以仓库实际脚本为准。

## 五、健康检查

curl -s http://127.0.0.1:8000/api/v1/health | python3 -m json.tool

查看最近任务：

curl -s "http://127.0.0.1:8000/api/v1/tasks/?limit=3" | python3 -m json.tool

## 六、用例 1：总体处理计划

飞书发送：

这些异常商品下一步怎么处理

期望：

- 识别为操作计划类 intent
- 调用 B 获取诊断字段和决策建议字段
- 返回老板可读处理计划
- steps 有 llm_action_plan_started / succeeded
- 不执行刷新、重试、替换 URL、删除、改价

## 七、用例 2：处理顺序

飞书发送：

帮我安排一下处理顺序

期望：

- 输出处理优先级
- 高优先级 / 人工接管对象排在前面
- 低风险对象可暂缓
- 不自动处理

## 八、用例 3：低可信对象计划

飞书发送：

低可信对象接下来怎么处理

期望：

- 说明低可信对象需要先人工复核
- 对 URL 问题给出替换详情页 URL 建议
- 对 mock_price / fallback_mock 提醒不能直接决策
- 不自动替换 URL

## 九、用例 4：重试与 URL 修正计划

飞书发送：

哪些先重试，哪些先换 URL

期望：

- 区分建议重试对象和建议换 URL 对象
- 只输出计划
- 不触发重试
- 不触发 URL 替换

## 十、用例 5：LLM 失败降级

通过 mock provider 或临时配置模拟 LLM 失败。

飞书发送：

这些异常商品下一步怎么处理

期望：

- 降级为规则计划
- steps 有 llm_action_plan_fallback_used 或 failed
- 飞书不显示 traceback

## 十一、验收查询

查看最近任务：

curl -s "http://127.0.0.1:8000/api/v1/tasks/?limit=10" | python3 -m json.tool

查看任务详情：

curl -s "http://127.0.0.1:8000/api/v1/tasks/{task_id}" | python3 -m json.tool

查看任务 steps：

curl -s "http://127.0.0.1:8000/api/v1/tasks/{task_id}/steps" | python3 -m json.tool

## 十二、老板演示话术

可以这样讲：

P14-D 不是让大模型自动执行处理动作，而是让它把系统已有的诊断字段和建议字段，整理成老板能直接看的下一步处理计划。

比如哪些对象先人工复核，哪些对象建议换 URL，哪些对象建议手动重试，哪些对象可以暂缓观察。

系统不会因为计划结果自动刷新、自动重试、自动改价或自动替换 URL。

如果 LLM 不可用，系统会降级成规则计划，保证飞书仍然能收到可读结果。

## 十三、通过标准

P14-D 实机通过标准：

- 操作计划命令可用
- 处理顺序命令可用
- 低可信对象计划可用
- 重试 / URL 修正计划可用
- 能生成老板可读计划
- 计划包含处理顺序、对象分组、建议动作、人工确认点
- LLM 不编造数据
- LLM 不承诺自动处理
- LLM 失败能降级
- task_steps 可追踪
- 不破坏 P14-A
- 不破坏 P14-B
- 不破坏 P14-C
- 不破坏 P13-I / P13-K