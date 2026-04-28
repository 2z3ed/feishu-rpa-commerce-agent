# P15-A Agent 开发约束：OCR 识别骨架与 mock 闭环

## 一、当前唯一主线

当前唯一主线是：

P15-A：OCR 识别骨架与 mock 闭环

本轮只做 OCR 能力骨架，不接真实 OCR。

## 二、当前已完成基础

P14 已完成并总收口：

- P14-A：LLM 意图解析 fallback
- P14-B：LLM 监控对象运营总结
- P14-C：LLM 异常原因解释
- P14-D：LLM 操作计划生成
- P14-Z：P14 总收口文档

不要回头改 P14。

## 三、必须先读

开始开发前，必须先读：

1. AGENTS.md 当前阶段入口
2. docs/p15/p15a-project-plan.md
3. docs/p15/P15A-agent-prompt.md
4. docs/p15/p15a-boss-demo-sop.md
5. docs/p15/p15a-acceptance-checklist.md

如果文件不存在，先创建文档，不要直接写业务代码。

## 四、本轮目标

本轮只做：

OCR 识别骨架与 mock 闭环。

目标链路：

用户命令  
→ 识别 OCR intent  
→ 构造 mock OCR 输入  
→ 调用 OCR service  
→ mock provider 返回 raw_text / confidence  
→ 返回飞书或任务结果  
→ task_steps 留痕  

## 五、本轮允许做

允许做：

- 新增 document.ocr_recognize intent
- 新增 OCR 输入 schema
- 新增 OCR 输出 schema
- 新增 OCR service
- 新增 mock OCR provider
- 新增 execute_action 分支
- 新增 task_steps 留痕
- 新增 .env.example 配置
- 新增测试
- 新增 P15-A 文档

## 六、本轮禁止做

禁止做：

- 不做 P15-B 真实 OCR provider
- 不接 PaddleOCR
- 不接云 OCR
- 不接飞书附件下载
- 不处理真实 PDF
- 不做发票字段结构化
- 不做小票字段结构化
- 不做人工确认与字段修正
- 不写入数据库正式结果
- 不写入飞书多维表
- 不做批量识别
- 不做自动报销
- 不做自动付款
- 不做税务合规判断
- 不改 B 项目
- 不重构 P14-A/B/C/D
- 不破坏 P14 已收口能力
- 不提交真实 .env
- 不提交 data/evidence 文件

## 七、核心规则

1. OCR 结果不是最终业务事实
2. OCR 低置信度必须提示人工确认
3. P15-A 不写正式结果
4. P15-A 不做字段结构化
5. P15-A 不下载飞书附件
6. P15-A 只用 mock provider 验证骨架
7. provider 异常不能导致 500
8. steps 中不能写完整敏感 OCR 原文
9. 真实 .env 不允许提交
10. evidence 文件不允许随便进 git

## 八、建议实现位置

先锚定仓库真实结构，再写代码。

优先检查：

- app/graph/nodes/resolve_intent.py
- app/graph/nodes/execute_action.py
- app/core/config.py
- app/utils/task_logger.py
- app/schemas/
- app/services/
- tests/
- .env.example

建议新增：

- app/schemas/ocr_document.py
- app/services/ocr/document_ocr.py
- tests/test_p15a_ocr_document_mock.py

如果仓库已有类似目录，以现有目录为准，不要重复造第二套。

## 九、OCR 输入 schema 要求

至少包含：

- document_id
- file_name
- mime_type
- file_path
- source
- requested_by
- hint_document_type

P15-A 可使用 mock:// 路径，不要求真实文件存在。

## 十、OCR 输出 schema 要求

至少包含：

- document_type
- raw_text
- confidence
- provider
- blocks
- needs_manual_review
- warnings

## 十一、mock provider 要求

mock provider 至少返回一个可读示例：

- document_type=invoice
- raw_text 包含发票号码、开票日期、购买方、金额
- confidence 大于 0.8
- provider=mock
- needs_manual_review=true
- warnings 包含“当前结果仅为 OCR 初步识别，需人工确认”

## 十二、steps 留痕

至少支持：

- ocr_document_started
- ocr_document_succeeded
- ocr_document_failed
- ocr_document_fallback_used

detail 可以包含：

- provider
- document_type
- mime_type
- confidence
- raw_text_length
- blocks_count
- needs_manual_review
- error

禁止写入：

- API Key
- token
- 密钥
- 超长 OCR 原文
- 完整敏感文件内容
- 真实用户文件路径敏感信息

## 十三、环境变量

建议新增：

ENABLE_OCR_DOCUMENT_RECOGNIZE=false  
OCR_DOCUMENT_PROVIDER=mock  
OCR_DOCUMENT_TIMEOUT_SECONDS=10  
OCR_EVIDENCE_DIR=data/ocr_evidence  

注意：

- 默认关闭
- 可以修改 .env.example
- 不要擅自修改真实 .env
- 如需实机启用，回报里必须明确“真实 .env 需要人工同步哪些变量”

## 十四、测试要求

至少覆盖：

- OCR intent 能识别
- mock OCR 能返回 raw_text
- mock OCR 能返回 confidence
- mock OCR 能返回 provider
- provider 异常能友好处理
- steps 有 ocr_document_* 留痕
- 不写入正式业务记录
- 不触发 RPA
- P14-A/B/C/D 不回归

## 十五、完成后回报格式

完成后必须回报：

A. 先读了哪些文件  
B. 新增了哪个 OCR intent  
C. OCR 输入 schema 如何设计  
D. OCR 输出 schema 如何设计  
E. OCR service 如何设计  
F. mock provider 返回什么  
G. OCR 失败如何处理  
H. steps 如何留痕  
I. 是否修改 .env.example  
J. 真实 .env 需要人工同步哪些变量  
K. 改了哪些文件  
L. 执行了哪些测试  
M. 测试结果  
N. 是否可以进入飞书 / API 验收  

不要编造实机结果。
没有跑飞书就明确说没有跑。