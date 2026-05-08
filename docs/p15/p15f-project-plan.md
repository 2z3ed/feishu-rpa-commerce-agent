# P15-F 开发主线文档：真实 OCR 结果下的票据字段抽取增强

## 一、阶段名称

P15-F：真实 OCR 结果下的票据字段抽取增强

## 二、当前背景

P15-D 已经打通飞书真实图片上传、附件解析、文件下载、evidence 保存。

P15-E 已经打通 PaddleOCR 真实读图：

- 飞书真实图片可以下载到 evidence
- PaddleOCR 可以读取 evidence 图片
- provider_actual=paddle
- fallback_used=false
- raw_text 来自真实图片
- blocks_count / confidence 有效

但 P15-E 实机也暴露出新问题：

- OCR 能读图，但结构化字段不够准
- 金额可能误提取
- invoice_date 可能缺失
- buyer_name 可能缺失
- P15-C 的规则更多适配 mock OCR 文本，不够适配真实电子发票 OCR raw_text

所以 P15-F 不是继续做 OCR Provider，而是增强真实 OCR 文本里的字段抽取能力。

## 三、本轮唯一目标

本轮只做：

真实 OCR raw_text → 更稳定的票据字段抽取。

目标链路：

飞书上传真实发票图片  
→ P15-D 下载 evidence  
→ P15-E PaddleOCR 真实识别  
→ 获得真实 raw_text / blocks  
→ P15-F 增强字段抽取  
→ 输出更准确的发票字段  
→ 标记字段置信度、缺失字段、缺失原因、疑似误提取字段  
→ 飞书返回老板可读字段摘要  
→ task_steps 可追踪  

## 四、P15-F 定位

P15-F 是字段抽取增强阶段。

P15-F 不是：

- OCR Provider 修复阶段
- 飞书附件入口阶段
- 人工确认阶段
- 写表阶段
- 报销付款阶段

P15-F 要验证的是：

- 真实 OCR raw_text 可以被更稳地解析成发票字段
- 金额候选可以评分
- 日期可以归一化
- 缺失字段有原因
- 不确定字段不会高置信度输出
- 字段抽取结果更适合后续人工确认

## 五、本轮允许做

允许做：

- 增强 invoice 字段抽取规则
- 增强 OCR 文本归一化
- 增强发票号码提取
- 增强开票日期提取与日期归一化
- 增强购买方 / 销售方提取
- 增强金额候选提取与评分
- 增强价税合计 / 税额 / 不含税金额区分
- 增加 missing_reasons
- 增加 field warning / needs_review
- 增加 extractor=rule_v2 或 extraction_profile=cn_vat_invoice
- 新增真实 OCR raw_text fixture
- 新增 P15-F 测试
- 更新 P15-F 文档

## 六、本轮禁止做

禁止做：

- 不做 P15-G 人工确认与字段修正闭环
- 不做 P15-H 结构化结果写入与归档
- 不做字段人工修正命令
- 不写入数据库正式结果
- 不写入飞书多维表
- 不做自动报销
- 不做自动付款
- 不做税务合规判断
- 不做发票真伪校验
- 不触发 RPA
- 不做批量 OCR
- 不做多文件 OCR
- 不做多页 PDF OCR
- 不更换 OCR Provider
- 不重构 P15-D/E
- 不改 B 项目
- 不提交真实 .env
- 不提交真实发票 / 客户文件
- 不提交 data/ocr_evidence
- 不提交 PaddleOCR 模型缓存
- 不提交 venv

## 七、增强字段范围

P15-F 第一版建议重点增强：

- invoice_number：发票号码
- invoice_date：开票日期
- buyer_name：购买方名称
- seller_name：销售方名称
- total_amount：价税合计 / 小写金额
- amount_without_tax：不含税金额
- tax_amount：税额
- currency：币种，默认 CNY

最低通过字段：

- 发票号码
- 开票日期
- 购买方
- 价税合计 / 金额

如果销售方、税额、不含税金额暂时不稳定，可以作为增强字段，不作为最低通过阻塞项。

## 八、推荐实现思路

第一版不建议直接上 LLM。

建议采用：

规则增强 + OCR 行归一化 + 候选字段评分

推荐流程：

OCR raw_text  
→ 文本归一化  
→ 行级清洗  
→ 字段候选提取  
→ 候选评分  
→ 选择最可信字段  
→ 输出字段置信度、source、warning、needs_review  

## 九、建议模块结构

可以继续增强：

app/services/ocr/structured_extraction.py

也可以新增：

app/services/ocr/invoice_field_extractor.py

推荐结构：

- structured_extraction.py
  - run_document_extraction()

- invoice_field_extractor.py
  - normalize_ocr_text()
  - normalize_invoice_date()
  - extract_invoice_number()
  - extract_invoice_date()
  - extract_buyer_name()
  - extract_seller_name()
  - extract_amount_candidates()
  - select_best_total_amount()
  - build_field_result()

不要把规则堆到 execute_action.py。

## 十、OCR 文本归一化

真实 OCR 会有格式差异，例如：

- 价税合计(小写) ¥105.04
- 价税合计 小写 105.04
- 价税合计（小写）￥105.04
- 开票日期:2024年04月07日
- 购买方信息 名称 深圳xxx公司

P15-F 要做轻量归一化：

- 全角冒号 / 半角冒号统一处理
- 中文括号统一处理
- ￥ / ¥ / 人民币 归一为 CNY
- 多空格清理
- 金额中的逗号清理
- 日期格式统一
- 常见 OCR 分隔符清理

日期建议统一成：

YYYY-MM-DD

示例：

- 2024年04月07日 → 2024-04-07
- 2024/04/07 → 2024-04-07
- 2024-04-07 → 2024-04-07

## 十一、金额候选评分

金额字段容易误提取，不能只取第一个金额。

候选来源包括：

- 价税合计
- 小写
- 合计金额
- 金额
- 税额
- 不含税金额
- 单价
- 数量

评分示例：

- 包含“价税合计” +0.5
- 包含“小写” +0.3
- 包含“金额” +0.2
- 包含“税额” -0.4
- 包含“单价” -0.4
- 包含“数量” -0.4
- 位于合计附近 +0.2

最终选择最高分候选作为 total_amount。

如果候选不够可信：

- needs_review=true
- warning=金额候选不唯一，需要人工复核

## 十二、字段来源与置信度

字段结果不只输出 value，还要输出：

- source
- confidence
- needs_review
- warning

示例：

```json
{
  "name": "total_amount",
  "label": "价税合计",
  "value": "105.04",
  "confidence": 0.82,
  "source": "rule_v2:amount_candidate_scoring",
  "needs_review": true,
  "warning": "金额候选较多，建议人工复核"
}
```

## 十三、缺失字段原因

P15-C 已有 missing_fields，P15-F 建议增强 missing_reasons。

示例：

```json
{
  "missing_fields": ["buyer_name"],
  "missing_reasons": {
    "buyer_name": "未找到购买方名称或名称行 OCR 不完整"
  }
}
```

飞书文案可以写：

缺失字段：
- 购买方：未找到明确的购买方名称，建议人工复核

## 十四、task_steps 留痕

继续使用：

- document_extraction_started
- document_extraction_succeeded
- document_extraction_failed

P15-F 增强 detail：

- extractor=rule_v2
- document_type=invoice
- fields_count
- missing_fields_count
- candidate_fields_count
- amount_candidates_count
- overall_confidence
- needs_manual_review
- extraction_profile=cn_vat_invoice

禁止写：

- 完整 OCR 原文
- 真实票据全文
- API Key
- token
- 下载 URL
- 真实敏感绝对路径

## 十五、飞书返回文案

用户发送：

上传发票图片 + 提取这张发票字段

返回示例：

已完成票据字段提取。

文档类型：发票  
整体置信度：0.84  
是否需要人工复核：是  

已提取字段：
- 发票号码：24412000000050936591
- 开票日期：2024-04-07
- 购买方：xxx公司
- 价税合计：105.04
- 币种：CNY

缺失字段：
- 销售方：未找到明确销售方名称

提醒：
当前结果来自真实 OCR 识别与规则抽取，仅供初步整理。正式使用前请人工确认。

## 十六、测试要求

新增：

tests/test_p15f_real_ocr_field_extraction.py

建议使用 P15-E 实机 raw_text 做脱敏 fixture，而不是 mock OCR 文本。

可以新增：

tests/fixtures/ocr/p15e_real_invoice_raw_text.txt

注意：

- 不要放真实敏感发票信息
- 可以放自造样例
- 可以放脱敏后的 OCR 文本

测试至少覆盖：

1. 能从真实 OCR raw_text 提取发票号码
2. 能从“2024年04月07日”提取并归一化开票日期
3. 能识别购买方名称
4. 能区分价税合计 / 税额 / 不含税金额
5. 金额候选多时选择价税合计
6. 字段缺失时进入 missing_fields
7. 缺失字段有 missing_reasons
8. needs_manual_review 正确触发
9. 输出不是 JSON 原文
10. 不写正式业务结果
11. 不触发 RPA
12. P15-C/D/E 回归不退化
13. P14 回归不退化

## 十七、飞书实机验收建议

复用 P15-E 已打通的真实发票图片。

飞书发送：

上传图片 + 提取这张发票字段

预期：

- provider_actual=paddle
- fallback_used=false
- document_extraction_succeeded
- 发票号码正确或更稳定
- 开票日期能提取或明确说明缺失原因
- 金额字段不再明显误提取
- 购买方能提取或明确说明缺失原因
- needs_manual_review=true 可以接受
- 不写正式业务结果
- 不触发 RPA

如果字段不能完全准确，也可以通过，但必须满足：

- 不把明显错误字段高置信度输出
- 不确定字段要 needs_review=true
- 缺失字段要说明原因

## 十八、最低通过标准

P15-F 最低通过：

- 基于真实 PaddleOCR raw_text 提取字段
- 发票号码提取稳定
- 开票日期提取增强，支持中文日期归一化
- 金额候选评分增强，避免明显误提取
- 购买方 / 销售方至少有一种增强识别逻辑
- missing_fields / missing_reasons 可用
- 字段 confidence / needs_review 可用
- result_summary 是老板可读字段摘要
- steps 有 rule_v2 / candidate_count 等安全摘要
- 不写正式业务结果
- 不触发 RPA
- P15-C/D/E 回归不退化
- P14 回归不退化

## 十九、禁止收口条件

出现以下情况，不允许收口：

- 真实 OCR raw_text 仍然只能提取 mock 风格字段
- 金额仍然明显误提取但没有 needs_review
- invoice_date 明显存在但提取不到，且没有原因
- buyer_name 明显存在但提取不到，且没有原因
- 字段缺失直接 failed
- 输出 JSON 原文给飞书用户
- steps 写入完整 OCR 原文
- 触发正式写入 / RPA
- P15-C/D/E 回归失败

## 二十、完成后回报格式

Agent 完成后必须按以下格式回报：

A. 先读了哪些文件  
B. 是否新增 invoice_field_extractor 或增强 structured_extraction  
C. OCR 文本归一化如何设计  
D. 发票号码 / 日期 / 购买方 / 金额字段如何提取  
E. 金额候选评分如何设计  
F. missing_reasons / needs_review 如何设计  
G. steps 如何留痕  
H. 是否修改 .env.example  
I. 改了哪些文件  
J. 执行了哪些测试  
K. 测试结果  
L. 是否可以进入飞书实机验收  