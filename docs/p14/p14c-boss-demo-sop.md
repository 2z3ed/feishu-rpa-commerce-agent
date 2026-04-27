# P14-C 老板演示 SOP：LLM 异常原因解释

## 一、演示目标

验证 P14-C 是否能基于已有诊断字段，生成老板能看懂的异常原因解释。

重点不是证明 LLM 能自动处理问题，而是证明：

- 系统能解释价格为什么不准
- 系统能解释低可信对象的问题
- 系统能解释 mock_price / fallback_mock 的含义
- 系统能解释 search_page / listing_page 的风险
- 系统能给出保守处理建议
- 不自动执行任何动作
- LLM 失败时能降级
- task_steps 可追踪

## 二、演示前提

P14-A 已完成并收口。  
P14-B 已完成并收口。  

P14-C 只做：

LLM 异常原因解释。

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
export ENABLE_LLM_ANOMALY_EXPLANATION=true  
export LLM_ANOMALY_EXPLANATION_PROVIDER=mock  

如果 P14-C 口语化命令依赖 P14-A fallback，也需要：

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
export ENABLE_LLM_ANOMALY_EXPLANATION=true  
export LLM_ANOMALY_EXPLANATION_PROVIDER=mock  
./scripts/dev_run_worker.sh

另开终端启动飞书长连接：

cd ~/feishu-rpa-commerce-agent  
source venv/bin/activate 2>/dev/null || source .venv/bin/activate  
export USE_SQLITE=true  
export ENABLE_LLM_ANOMALY_EXPLANATION=true  
export LLM_ANOMALY_EXPLANATION_PROVIDER=mock  
./scripts/dev_run_feishu_longconn.sh

如果脚本名称和仓库不一致，以仓库实际脚本为准。

## 五、健康检查

curl -s http://127.0.0.1:8000/api/v1/health | python3 -m json.tool

查看最近任务：

curl -s "http://127.0.0.1:8000/api/v1/tasks/?limit=3" | python3 -m json.tool

## 六、用例 1：解释价格为什么不准

飞书发送：

为什么这些商品价格不准

期望：

- 识别为异常解释类 intent
- 调用 B 获取诊断字段
- 返回老板可读异常解释
- steps 有 llm_anomaly_explanation_started / succeeded
- 不执行刷新、重试、替换 URL、删除、改价

## 七、用例 2：解释低可信对象

飞书发送：

解释一下低可信对象的问题

期望：

- 说明低可信是什么意思
- 说明为什么不能直接用于价格判断
- 给出人工复核建议
- 不自动处理

## 八、用例 3：解释 mock_price / fallback_mock

飞书发送：

mock_price 是什么意思，为什么不能直接用

期望：

- 说明 mock_price / fallback_mock 是兜底结果
- 说明它不是稳定真实采集价格
- 建议人工复核或更换详情页 URL
- 不自动改价

## 九、用例 4：解释需要人工处理对象

飞书发送：

为什么这些商品需要人工处理

期望：

- 解释人工接管原因
- 说明典型风险
- 给出保守建议
- 不自动执行

## 十、用例 5：LLM 失败降级

通过 mock provider 或临时配置模拟 LLM 失败。

飞书发送：

为什么这些商品价格不准

期望：

- 降级为规则解释
- steps 有 llm_anomaly_explanation_fallback_used 或 failed
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

P14-C 不是让大模型自动处理价格异常，而是让它把系统已有的诊断字段翻译成老板能看懂的业务解释。

例如 mock_price、fallback_mock、low_confidence、search_page 这些字段，技术上能记录问题，但老板不一定理解。P14-C 会解释这些字段为什么代表风险、对价格判断有什么影响、建议人工怎么处理。

系统不会因为解释结果自动刷新、自动改价或自动替换 URL。

如果 LLM 不可用，系统会降级成规则解释，保证飞书仍然能收到可读结果。

## 十三、通过标准

P14-C 实机通过标准：

- 异常解释命令可用
- 低可信解释可用
- mock_price / fallback_mock 解释可用
- 人工处理原因解释可用
- 能生成老板可读解释
- 解释包含问题、原因、影响、建议
- LLM 不编造数据
- LLM 不承诺自动处理
- LLM 失败能降级
- task_steps 可追踪
- 不破坏 P14-A
- 不破坏 P14-B
- 不破坏 P13-I / P13-K