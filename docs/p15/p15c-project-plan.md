# P15-C 开发主线文档：发票 / 小票结构化字段提取

## 一、阶段名称

P15-C：发票 / 小票结构化字段提取

## 二、当前背景

P14 已完成并总收口，系统已经具备自然语言理解、总结、解释和操作计划能力。

P15-A 已完成 OCR mock 骨架：

- document.ocr_recognize intent
- OCR 输入 / 输出 schema
- mock OCR provider
- OCR service 统一入口
- raw_text / confidence / blocks / provider 输出
- ocr_document_* steps 留痕
- 飞书 / API mock OCR 验收通过

P15-B 已完成真实 OCR provider 接入基础：

- 支持 OCR_DOCUMENT_PROVIDER=mock / paddle / unsupported
- PaddleOCR provider 懒加载
- provider 不可用时降级 mock
- provider_requested / provider_actual / fallback_reason 留痕
- longconn queued 覆盖已完成任务的状态一致性修复
- provider routing 与降级验收通过

P15-C 开始做 OCR 后的业务价值：

OCR raw_text → 结构化字段提取。

## 三、本轮唯一目标

本轮只做：

发票 / 小票结构化字段提取。

固定链路：

飞书命令 / API 命令  
→ document.structured_extract  
→ 调用 OCR service 获取 raw_text  
→ 调用结构化提取 service  
→ 输出字段、字段置信度、缺失字段、人工复核标记  
→ 返回老板可读结果  
→ task_steps 留痕  

## 四、P15-C 定位

P15-C 不是做发票验真。

P15-C 不是做财务报销。

P15-C 要验证的是：

- OCR raw_text 能进入字段提取层
- 字段可以结构化输出
- 缺失字段可以被标记
- 整体置信度可以被计算
- 是否需要人工复核可以被判断
- 飞书用户看到的是可读字段摘要
- 后续 P15-D/E/F 可以基于该结果继续做附件入口、人工确认、归档写入

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
- 更新 .env.example
- 新增 P15-C 测试
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

## 七、建议新增 intent

新增：

document.structured_extract

可识别命令示例：

- 提取这张发票字段
- 帮我提取票据信息
- 识别并整理这张小票
- 把这张发票结构化一下
- 提取发票号码、日期和金额

与 P15-A 的区别：

document.ocr_recognize：只返回 OCR raw_text / confidence / provider  
document.structured_extract：在 OCR 基础上继续提取字段  

## 八、建议新增 schema

建议新增：

app/schemas/document_extraction.py

### ExtractedField

字段建议：

- name：系统字段名
- label：老板可读字段名
- value：字段值
- confidence：字段置信度
- source：rule / ocr / fallback
- needs_review：是否需要人工复核
- warning：字段风险提示

示例：

```json
{
  "name": "invoice_number",
  "label": "发票号码",
  "value": "12345678",
  "confidence": 0.91,
  "source": "rule",
  "needs_review": false,
  "warning": ""
}
```

### DocumentExtractionInput

字段建议：

- document_id
- document_type
- raw_text
- ocr_confidence
- ocr_provider
- hint_document_type
- ocr_fallback_used

示例：

```json
{
  "document_id": "mock-doc-001",
  "document_type": "invoice",
  "raw_text": "发票号码：12345678\n开票日期：2026-04-27\n购买方：测试公司\n金额：128.50",
  "ocr_confidence": 0.92,
  "ocr_provider": "mock",
  "hint_document_type": "invoice",
  "ocr_fallback_used": false
}
```

### DocumentExtractionOutput

字段建议：

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

示例：

```json
{
  "status": "succeeded",
  "document_type": "invoice",
  "fields": [],
  "overall_confidence": 0.86,
  "missing_fields": ["seller_name", "invoice_code"],
  "needs_manual_review": true,
  "warnings": [
    "部分关键字段缺失，需要人工确认"
  ],
  "fallback_used": false,
  "error": "",
  "extractor": "rule"
}
```

## 九、发票字段第一版范围

第一版 invoice 必须支持：

- invoice_number：发票号码
- invoice_date：开票日期
- buyer_name：购买方
- total_amount：价税合计 / 金额
- currency：币种，默认 CNY 或 unknown

第一版可选支持：

- invoice_code：发票代码
- seller_name：销售方

暂不强制：

- buyer_tax_id
- seller_tax_id
- amount_without_tax
- tax_amount
- item_name

这些可以进入 missing_fields 或后续扩展。

## 十、小票字段第一版范围

receipt 第一版支持：

- merchant_name：商户名称
- receipt_date：小票日期
- total_amount：总金额
- currency：币种

暂不做 items 明细。

小票行项目解析后续再做，避免 P15-C 范围膨胀。

## 十一、结构化提取 service 设计

建议新增：

app/services/ocr/structured_extraction.py

核心入口：

run_document_extraction(input)

内部根据 document_type 分发：

- invoice → extract_invoice_fields()
- receipt → extract_receipt_fields()
- unknown → 尝试通用金额 / 日期提取，或者返回友好提示

第一版使用规则提取，不依赖真实 LLM key。

示例规则：

- 发票号码[:：]\s*(\S+)
- 开票日期[:：]\s*(\S+)
- 购买方[:：]\s*(.+)
- 金额[:：]\s*([\d.]+)
- 商户[:：]\s*(.+)
- 总金额[:：]\s*([\d.]+)

字段缺失不能报错，必须进入 missing_fields。

## 十二、字段置信度设计

第一版采用稳定规则：

- 明确标签命中：0.90
- 模糊规则命中：0.70
- 缺失字段：0.00

overall_confidence 建议：

min(ocr_confidence, 已提取字段平均置信度)

如果没有字段被提取，overall_confidence=0。

## 十三、人工复核规则

出现以下任一情况：

- missing_fields 非空
- overall_confidence < 0.85
- document_type=unknown
- total_amount 缺失
- OCR provider 是 mock
- OCR fallback_used=true

则：

needs_manual_review=true

飞书文案必须提示：

当前结果来自 OCR 识别与规则抽取，仅供初步整理，正式使用前请人工确认。

## 十四、环境变量建议

建议新增到 .env.example：

ENABLE_DOCUMENT_STRUCTURED_EXTRACTION=false  
DOCUMENT_EXTRACTION_PROVIDER=rule  
DOCUMENT_EXTRACTION_TIMEOUT_SECONDS=10  

要求：

- 默认关闭
- provider 第一版只支持 rule
- 后续可扩展 llm
- 真实 .env 不自动修改
- 如需实机启用，必须提示用户人工同步

## 十五、task_steps 留痕

P15-C 新增：

- document_extraction_started
- document_extraction_succeeded
- document_extraction_failed
- document_extraction_fallback_used

detail 可包含：

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
- 用户真实票据信息大段内容

## 十六、execute_action 分支建议

新增分支：

intent=document.structured_extract

执行流程：

1. 构造 OCRDocumentInput
2. 调用 run_document_ocr()
3. 拿到 OCR raw_text
4. 构造 DocumentExtractionInput
5. 调用 run_document_extraction()
6. 返回老板可读字段摘要
7. 写 ocr_document_* steps
8. 写 document_extraction_* steps
9. action_executed.detail 记录安全摘要

P15-C 可以复用 P15-A/B 的 mock OCR，不需要真实附件。

## 十七、action_executed.detail 建议字段

新增安全摘要：

- document_type
- ocr_provider
- ocr_confidence
- extraction_status
- extractor
- fields_count
- missing_fields_count
- overall_confidence
- needs_manual_review
- formal_write=false

禁止写完整字段内容到 detail。

## 十八、飞书返回文本建议

用户发：

提取这张发票字段

返回示例：

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

## 十九、测试要求

新增测试：

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

可选覆盖：

- receipt 最小提取
- unknown document_type 友好提示
- OCR raw_text 为空时友好失败

## 二十、飞书 / API 验收建议

P15-C 不需要真实附件。

先用 mock OCR 文本验收即可。

### 用例 1：发票字段提取

飞书发送：

提取这张发票字段

预期：

- intent=document.structured_extract
- 返回发票号码、开票日期、购买方、金额
- 有 overall_confidence
- 有 needs_manual_review
- 有缺失字段提示
- steps 有 ocr_document_succeeded
- steps 有 document_extraction_succeeded
- 不写正式业务结果
- 不触发 RPA

### 用例 2：票据信息提取

飞书发送：

帮我提取票据信息

预期：

- intent=document.structured_extract
- 返回结构化字段摘要
- 不输出 JSON 原文
- 提示人工确认

### 用例 3：结构化命令

飞书发送：

把这张发票结构化一下

预期：

- OCR + extraction 链路都跑通
- 字段缺失有提示
- 不写正式业务结果

## 二十一、最低通过标准

P15-C 最低通过标准：

- 新增 document.structured_extract intent
- 新增结构化提取 schema
- 新增 rule extractor service
- 能从 mock OCR raw_text 提取发票号码、日期、购买方、金额
- 能输出 fields / confidence / missing_fields / needs_manual_review
- 能返回老板可读字段摘要
- task_steps 有 document_extraction_* 留痕
- 不写正式业务结果
- 不触发 RPA
- 不接飞书附件下载
- P15-A/B 回归不退化
- P14 回归不退化

## 二十二、完成后回报格式

Agent 完成后必须按以下格式回报：

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