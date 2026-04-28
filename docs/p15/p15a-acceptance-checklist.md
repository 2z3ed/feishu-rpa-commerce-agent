# P15-A 验收清单：OCR 识别骨架与 mock 闭环

## 一、阶段信息

阶段：

P15-A：OCR 识别骨架与 mock 闭环

验收目标：

搭建 OCR 能力骨架，使用 mock OCR provider 跑通最小识别闭环。

## 二、文档验收

必须存在：

- AGENTS.md 当前阶段入口
- docs/p15/p15a-project-plan.md
- docs/p15/P15A-agent-prompt.md
- docs/p15/p15a-boss-demo-sop.md
- docs/p15/p15a-acceptance-checklist.md

检查命令：

ls -la docs/p15

## 三、配置验收

建议支持：

ENABLE_OCR_DOCUMENT_RECOGNIZE=false  
OCR_DOCUMENT_PROVIDER=mock  
OCR_DOCUMENT_TIMEOUT_SECONDS=10  
OCR_EVIDENCE_DIR=data/ocr_evidence  

通过标准：

- 默认关闭
- mock provider 可测试
- .env.example 可更新
- 真实 .env 需要人工同步时必须明确提示

## 四、intent 识别验收

测试命令：

识别这张发票  
帮我读一下这个文件  
提取这张图片里的文字  
OCR 识别一下  
帮我识别票据文字  

通过标准：

- 能识别为 document.ocr_recognize
- 能进入 OCR 执行分支
- 不误触发 P14 summary / explanation / action_plan

## 五、OCR 输出验收

输出至少包含：

- document_type
- raw_text
- confidence
- provider
- needs_manual_review
- warnings

通过标准：

- raw_text 不为空
- confidence 合理
- provider=mock
- 明确提示人工确认
- 不输出 JSON 原文给飞书用户

## 六、steps 留痕验收

至少能看到：

- ocr_document_started
- ocr_document_succeeded
- ocr_document_failed
- ocr_document_fallback_used

detail 不得包含：

- API Key
- token
- 密钥
- 超长 OCR 原文
- 完整敏感文件内容
- 真实用户文件路径敏感信息

## 七、失败降级验收

模拟 OCR provider 失败。

通过标准：

- 不报 500
- 不把 traceback 发给飞书
- task_steps 有 failed 或 fallback_used
- 返回友好提示
- 不写正式结果

## 八、禁止动作验收

P15-A 不能触发：

- 自动字段结构化
- 自动写库
- 自动写飞书多维表
- 自动报销
- 自动付款
- 自动改价
- 自动 RPA

## 九、测试验收

建议执行：

pytest -q tests/test_p15a_ocr_document_mock.py  
pytest -q tests/test_p14d_llm_action_plan.py  
pytest -q tests/test_p14c_llm_anomaly_explanation.py  
pytest -q tests/test_p14b_llm_monitor_summary.py  
pytest -q tests/test_p14a_llm_intent_fallback.py  

如果全量失败，必须说明：

- 失败文件
- 失败原因
- 是否与 P15-A 有关

## 十、飞书 / API 验收

至少测试：

识别这张发票  
提取这张图片里的文字  
帮我识别票据文字  

模拟 provider 失败后测试：

识别这张发票  

通过标准：

- 有 OCR 摘要
- 有 raw_text 摘要
- 有 confidence
- 有人工确认提醒
- 不自动写入正式结果
- /tasks 和 /steps 可查

## 十一、禁止收口条件

出现以下情况，不允许收口：

- P14 回归失败
- OCR 命令触发了非 OCR intent
- OCR 结果被写入正式业务记录
- OCR 失败时报 500
- 飞书用户看到 traceback
- steps 没有留痕
- 提交了真实 .env
- 提交了本地 evidence 文件
- agent 没有说明真实 .env 需要人工同步哪些变量

## 十二、最终收口回报模板

A. 文档是否齐全  
B. 配置是否默认关闭  
C. OCR intent 是否可识别  
D. OCR schema 是否稳定  
E. mock provider 是否可用  
F. OCR 结果是否包含 raw_text / confidence  
G. OCR 失败是否能友好处理  
H. 是否没有写入正式业务结果  
I. steps 是否留痕  
J. 是否修改 .env.example  
K. 真实 .env 是否需要人工同步  
L. 测试是否通过  
M. 飞书 / API 验收是否通过  
N. 是否允许 P15-A 收口  