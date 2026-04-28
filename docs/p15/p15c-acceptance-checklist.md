# P15-C 验收清单：发票 / 小票结构化字段提取

## 一、阶段信息

阶段：

P15-C：发票 / 小票结构化字段提取

验收目标：

基于 P15-A/B 的 OCR raw_text，完成票据结构化字段提取，输出字段、置信度、缺失项和人工复核提示。

## 二、文档验收

必须存在：

- AGENTS.md 当前阶段入口
- docs/p15/p15c-project-plan.md
- docs/p15/P15C-agent-prompt.md
- docs/p15/p15c-boss-demo-sop.md
- docs/p15/p15c-acceptance-checklist.md

检查命令：

```bash
ls -la docs/p15
```

## 三、配置验收

建议支持：

```env
ENABLE_DOCUMENT_STRUCTURED_EXTRACTION=false
DOCUMENT_EXTRACTION_PROVIDER=rule
DOCUMENT_EXTRACTION_TIMEOUT_SECONDS=10
```

通过标准：

- 默认关闭
- rule provider 可测试
- .env.example 更新
- 真实 .env 需要人工同步时必须明确提示

## 四、intent 识别验收

测试命令：

```text
提取这张发票字段
帮我提取票据信息
识别并整理这张小票
把这张发票结构化一下
提取发票号码、日期和金额
```

通过标准：

- 能识别为 document.structured_extract
- 不误触发 document.ocr_recognize
- 不误触发 P14 summary / explanation / action_plan

## 五、schema 验收

必须包含：

- ExtractedField
- DocumentExtractionInput
- DocumentExtractionOutput

字段输出至少包含：

- fields
- overall_confidence
- missing_fields
- needs_manual_review
- warnings
- extractor
- status

## 六、invoice 提取验收

第一版 invoice 至少能提取：

- 发票号码
- 开票日期
- 购买方
- 金额
- 币种

通过标准：

- mock OCR raw_text 能稳定提取核心字段
- 缺失字段进入 missing_fields
- 字段 confidence 有值
- needs_manual_review 合理

## 七、receipt 提取验收

第一版 receipt 至少支持：

- 商户名称
- 小票日期
- 总金额
- 币种

通过标准：

- 不要求 items 明细
- 字段缺失不报错
- 能返回友好提示

## 八、返回文案验收

飞书返回必须是老板可读摘要，不是 JSON 原文。

必须包含：

- 文档类型
- 整体置信度
- 是否需要人工复核
- 已提取字段
- 缺失字段
- 人工确认提醒

## 九、steps 留痕验收

至少能看到：

- document_extraction_started
- document_extraction_succeeded
- document_extraction_failed
- document_extraction_fallback_used

detail 不得包含：

- API Key
- token
- 密钥
- 完整 OCR 原文
- 完整票据内容
- 真实文件路径
- 用户真实票据大段内容

## 十、禁止动作验收

P15-C 不能触发：

- 飞书附件下载
- 字段人工修正
- 写数据库正式结果
- 写飞书多维表
- 自动报销
- 自动付款
- 发票真伪校验
- RPA 执行

## 十一、测试验收

建议执行：

```bash
pytest -q tests/test_p15c_document_structured_extraction.py
pytest -q tests/test_p15b_ocr_paddle_provider.py
pytest -q tests/test_p15a_ocr_document_mock.py
pytest -q tests/test_p14d_llm_action_plan.py
pytest -q tests/test_p14c_llm_anomaly_explanation.py
pytest -q tests/test_p14b_llm_monitor_summary.py
pytest -q tests/test_p14a_llm_intent_fallback.py
```

如果全量失败，必须说明：

- 失败文件
- 失败原因
- 是否与 P15-C 有关

## 十二、飞书 / API 验收

至少测试：

```text
提取这张发票字段
帮我提取票据信息
把这张发票结构化一下
```

通过标准：

- 有结构化字段摘要
- 有核心字段
- 有缺失字段提示
- 有人工复核提示
- 有 document_extraction_* steps
- 不写正式业务结果
- 不触发 RPA

## 十三、禁止收口条件

出现以下情况，不允许收口：

- P15-A 回归失败
- P15-B 回归失败
- P14 回归失败
- 结构化命令误触发 OCR recognize
- 字段缺失时报 500
- 飞书用户看到 traceback
- steps 没有 extraction 留痕
- 输出 JSON 原文给用户
- 写入正式业务结果
- 触发 RPA
- 提交真实 .env
- 提交真实票据 / 客户文件
- 提交 data/ocr_evidence 文件

## 十四、最终收口回报模板

A. 文档是否齐全  
B. structured extract intent 是否可识别  
C. schema 是否稳定  
D. invoice 字段是否可提取  
E. receipt 字段是否最小支持  
F. missing_fields / needs_manual_review 是否可用  
G. steps 是否记录 extraction  
H. 是否没有附件下载 / 正式写入 / RPA  
I. 是否修改 .env.example  
J. 真实 .env 是否需要人工同步  
K. 测试是否通过  
L. 飞书 / API 验收是否通过  
M. 是否允许 P15-C 收口  