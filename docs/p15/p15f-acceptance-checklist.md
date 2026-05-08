# P15-F 验收清单：真实 OCR 结果下的票据字段抽取增强

## 一、阶段信息

阶段：

P15-F：真实 OCR 结果下的票据字段抽取增强

验收目标：

基于真实 PaddleOCR raw_text，增强发票字段抽取稳定性，尤其是发票号码、开票日期、购买方、价税合计 / 金额等字段。

## 二、文档验收

必须存在：

- AGENTS.md 当前阶段入口
- docs/p15/p15f-project-plan.md
- docs/p15/P15F-agent-prompt.md
- docs/p15/p15f-boss-demo-sop.md
- docs/p15/p15f-acceptance-checklist.md

检查命令：

```bash
ls -la docs/p15
```

## 三、代码验收

建议涉及：

- app/services/ocr/structured_extraction.py
- app/services/ocr/invoice_field_extractor.py
- app/schemas/document_extraction.py
- app/graph/nodes/execute_action.py
- tests/test_p15f_real_ocr_field_extraction.py

如未新增 invoice_field_extractor.py，需要说明为什么直接增强 structured_extraction.py。

## 四、字段验收

最低字段：

- 发票号码
- 开票日期
- 购买方
- 价税合计 / 金额

增强字段：

- 销售方
- 不含税金额
- 税额
- 币种

## 五、日期归一化验收

必须支持：

- 2024年04月07日 → 2024-04-07
- 2024/04/07 → 2024-04-07
- 2024-04-07 → 2024-04-07

通过标准：

- 日期存在时尽量提取
- 提取失败时进入 missing_fields
- 有 missing_reasons

## 六、金额候选验收

必须避免只取第一个金额。

通过标准：

- 能识别价税合计
- 能降低税额 / 单价 / 数量的优先级
- 多候选时能选出更可信候选
- 不确定时 needs_review=true
- warning 有提示

## 七、missing_reasons 验收

通过标准：

- missing_fields 不为空时，missing_reasons 有对应说明
- 字段缺失不导致 failed
- 飞书文案能展示缺失原因或复核提示

## 八、steps 留痕验收

document_extraction_succeeded detail 建议包含：

- extractor=rule_v2
- extraction_profile=cn_vat_invoice
- fields_count
- missing_fields_count
- candidate_fields_count
- amount_candidates_count
- overall_confidence
- needs_manual_review

不得包含：

- 完整 OCR 原文
- 真实票据全文
- API Key
- token
- 下载 URL
- 真实敏感绝对路径

## 九、返回文案验收

飞书返回必须是老板可读摘要，不是 JSON 原文。

必须包含：

- 文档类型
- 整体置信度
- 是否需要人工复核
- 已提取字段
- 缺失字段
- 缺失原因
- 人工确认提醒

## 十、禁止动作验收

P15-F 不能触发：

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
pytest -q tests/test_p15f_real_ocr_field_extraction.py
pytest -q tests/test_p15e_real_ocr_provider_integration.py
pytest -q tests/test_p15d_feishu_file_entry.py
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
- 是否与 P15-F 有关

## 十二、飞书实机验收

至少测试：

上传真实 OCR 可识别样例图片，并发送：

```text
提取这张发票字段
```

通过标准：

- provider_actual=paddle
- fallback_used=false
- document_extraction_succeeded
- 字段结果来自真实 OCR raw_text
- 发票号码、日期、金额等字段比 P15-E 更稳
- 缺失字段有原因
- 不确定字段 needs_review=true
- 不写正式业务结果
- 不触发 RPA

## 十三、允许部分不准确的情况

允许：

- 复杂字段缺失
- 销售方缺失
- 税额缺失
- needs_manual_review=true

但必须：

- 缺失有原因
- 不确定有 warning
- 不高置信度输出明显错误字段
- 不让任务直接 failed

## 十四、禁止收口条件

出现以下情况，不允许收口：

- 真实 OCR raw_text 仍然只能提取 mock 风格字段
- 金额明显误提取但没有 needs_review
- invoice_date 明显存在但提取不到，且没有原因
- buyer_name 明显存在但提取不到，且没有原因
- 字段缺失直接 failed
- 输出 JSON 原文给飞书用户
- steps 写入完整 OCR 原文
- 触发正式写入 / RPA
- P15-C/D/E 回归失败
- P14 回归失败

## 十五、最终收口回报模板

A. 文档是否齐全  
B. 是否增强字段抽取模块  
C. 日期归一化是否可用  
D. 金额候选评分是否可用  
E. missing_reasons 是否可用  
F. needs_review / warning 是否可用  
G. steps 是否记录 rule_v2 / candidate_count  
H. 飞书返回是否老板可读  
I. 是否没有正式写入 / RPA  
J. 测试是否通过  
K. 飞书实机是否通过  
L. 是否允许 P15-F 收口  