# P15-C Agent 开发约束：发票 / 小票结构化字段提取

## 一、当前唯一主线

当前唯一主线是：

P15-C：发票 / 小票结构化字段提取

本轮只做 OCR raw_text 到结构化字段的提取，不接飞书附件下载，不写正式业务结果。

## 二、当前已完成基础

P14 已完成并总收口：

- P14-A：LLM 意图解析 fallback
- P14-B：LLM 监控对象运营总结
- P14-C：LLM 异常原因解释
- P14-D：LLM 操作计划生成
- P14-Z：P14 总收口文档

P15-A 已完成并收口：

- document.ocr_recognize intent
- OCR 输入 / 输出 schema
- mock OCR provider
- OCR service 统一入口
- ocr_document_* steps 留痕
- 飞书 / API mock OCR 验收通过

P15-B 已完成并收口：

- OCR provider routing：mock / paddle / unsupported
- PaddleOCR provider 懒加载
- provider 不可用时 fallback mock
- provider_requested / provider_actual / fallback_reason 留痕
- longconn 状态一致性修复

不要回头重做 P15-A/B。

## 三、必须先读

开始开发前，必须先读：

1. AGENTS.md 当前阶段入口
2. docs/p15/p15c-project-plan.md
3. docs/p15/P15C-agent-prompt.md
4. docs/p15/p15c-boss-demo-sop.md
5. docs/p15/p15c-acceptance-checklist.md
6. P15-A / P15-B 相关代码和测试

如果文件不存在，先创建文档，不要直接写业务代码。

## 四、本轮目标

本轮只做：

OCR raw_text → 结构化字段提取。

目标链路：

用户命令  
→ document.structured_extract  
→ 调用 OCR service 获取 raw_text  
→ 调用 rule extractor  
→ 返回 fields / confidence / missing_fields / needs_manual_review  
→ 返回老板可读字段摘要  
→ task_steps 留痕  

## 五、本轮允许做

允许做：

- 新增 document.structured_extract intent
- 新增结构化提取 schema
- 新增 rule extractor service
- 新增 invoice 字段提取
- 新增 receipt 最小字段提取
- 新增 missing_fields
- 新增 overall_confidence
- 新增 needs_manual_review
- 新增 document_extraction_* steps 留痕
- 新增老板可读返回文案
- 新增 P15-C 测试
- 更新 .env.example
- 新增 P15-C 文档

## 六、本轮禁止做

禁止做：

- 不做 P15-D 飞书文件入口接入
- 不接飞书附件下载
- 不处理真实附件上传
- 不做 PDF 多页解析
- 不做人工确认闭环
- 不做字段修改命令
- 不写入数据库正式结果
- 不写入飞书多维表
- 不做自动报销
- 不做自动付款
- 不做税务合规判断
- 不做发票真伪校验
- 不触发 RPA
- 不改 B 项目
- 不重构 P14-A/B/C/D
- 不破坏 P15-A/B OCR 能力
- 不提交真实 .env
- 不提交真实票据 / 客户文件
- 不提交 data/ocr_evidence 临时文件

## 七、核心规则

1. 结构化提取结果不是最终业务事实
2. 缺失字段必须进入 missing_fields
3. 低置信度必须提示人工确认
4. OCR provider=mock 时也必须提示人工确认
5. 本轮不写正式业务结果
6. 本轮不做字段修正
7. 本轮不接飞书附件下载
8. 本轮不做发票真伪判断
9. steps 中不能写完整 OCR 原文或完整票据内容
10. 真实 .env 和 evidence 文件不能进 git

## 八、intent 要求

新增：

document.structured_extract

识别命令包括：

- 提取这张发票字段
- 帮我提取票据信息
- 识别并整理这张小票
- 把这张发票结构化一下
- 提取发票号码、日期和金额

不能误触发：

- document.ocr_recognize
- P14 summary / explanation / action_plan

## 九、schema 要求

建议新增：

app/schemas/document_extraction.py

至少包含：

- ExtractedField
- DocumentExtractionInput
- DocumentExtractionOutput

ExtractedField 至少包含：

- name
- label
- value
- confidence
- source
- needs_review
- warning

DocumentExtractionOutput 至少包含：

- status
- document_type
- fields
- overall_confidence
- missing_fields
- needs_manual_review
- warnings
- fallback_used
- error
- extractor

## 十、rule extractor 要求

建议新增：

app/services/ocr/structured_extraction.py

核心入口：

run_document_extraction(input)

支持：

- invoice
- receipt
- unknown

invoice 第一版必须提取：

- invoice_number
- invoice_date
- buyer_name
- total_amount
- currency

receipt 第一版支持：

- merchant_name
- receipt_date
- total_amount
- currency

字段缺失不能报错，必须进入 missing_fields。

## 十一、字段置信度要求

建议规则：

- 明确标签命中：0.90
- 模糊规则命中：0.70
- 缺失字段：0.00

overall_confidence：

min(ocr_confidence, 已提取字段平均置信度)

如果没有字段被提取：

overall_confidence=0

## 十二、人工复核要求

以下任一情况：

- missing_fields 非空
- overall_confidence < 0.85
- document_type=unknown
- total_amount 缺失
- OCR provider 是 mock
- OCR fallback_used=true

则：

needs_manual_review=true

飞书文案必须提醒：

当前结果来自 OCR 识别与规则抽取，仅供初步整理，正式使用前请人工确认。

## 十三、steps 留痕

新增：

- document_extraction_started
- document_extraction_succeeded
- document_extraction_failed
- document_extraction_fallback_used

detail 可以包含：

- document_type
- extractor
- fields_count
- missing_fields_count
- overall_confidence
- needs_manual_review
- fallback_used
- error

禁止写入：

- API Key
- token
- 密钥
- 完整 OCR 原文
- 完整票据内容
- 真实文件路径
- 用户真实票据大段内容

## 十四、返回文案要求

飞书返回老板可读摘要，不直接返回 JSON 原文。

必须包含：

- 文档类型
- 整体置信度
- 是否需要人工复核
- 已提取字段
- 缺失字段
- 人工确认提醒

示例结构：

已完成票据字段提取。

文档类型：发票  
整体置信度：0.86  
是否需要人工复核：是  

已提取字段：
- 发票号码：12345678
- 开票日期：2026-04-27
- 购买方：测试公司
- 金额：128.50

缺失字段：
- 销售方
- 发票代码

提醒：
当前结果来自 OCR 识别与规则抽取，仅供初步整理。正式使用前请人工确认。

## 十五、环境变量

建议新增：

ENABLE_DOCUMENT_STRUCTURED_EXTRACTION=false  
DOCUMENT_EXTRACTION_PROVIDER=rule  
DOCUMENT_EXTRACTION_TIMEOUT_SECONDS=10  

注意：

- 可以修改 .env.example
- 不要修改真实 .env
- 如需实机启用，必须回报真实 .env 需要人工同步哪些变量

## 十六、测试要求

新增：

tests/test_p15c_document_structured_extraction.py

至少覆盖：

1. document.structured_extract intent 能识别
2. 发票 mock OCR raw_text 能提取发票号码
3. 能提取开票日期
4. 能提取购买方
5. 能提取金额
6. 缺失字段进入 missing_fields
7. needs_manual_review=true
8. 输出不是 JSON 原文
9. steps 有 document_extraction_started / succeeded
10. 不写正式业务结果
11. 不触发 RPA
12. P15-A/B 回归不退化
13. P14 回归不退化

## 十七、完成后回报格式

完成后必须回报：

A. 先读了哪些文件  
B. 新增了哪个 structured extract intent  
C. 结构化提取 schema 如何设计  
D. rule extractor service 如何设计  
E. invoice 第一版支持哪些字段  
F. receipt 第一版支持哪些字段  
G. 字段置信度如何计算  
H. missing_fields / needs_manual_review 如何判断  
I. steps 如何留痕  
J. 是否修改 .env.example  
K. 真实 .env 需要人工同步哪些变量  
L. 改了哪些文件  
M. 执行了哪些测试  
N. 测试结果  
O. 是否可以进入飞书 / API 验收  

不要编造实机结果。
没有跑飞书就明确说没有跑。