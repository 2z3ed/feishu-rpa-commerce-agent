# P15-F Agent 开发约束：真实 OCR 结果下的票据字段抽取增强

## 一、当前唯一主线

当前唯一主线是：

P15-F：真实 OCR 结果下的票据字段抽取增强

本轮只做真实 PaddleOCR raw_text 下的字段抽取增强。

不要做人工确认。
不要做字段修改命令。
不要写正式业务结果。
不要触发 RPA。

## 二、当前已完成基础

P14 已完成并总收口。

P15-A 已完成并收口：

- document.ocr_recognize
- OCR schema
- mock OCR provider
- OCR service
- ocr_document_* steps

P15-B 已完成并收口：

- OCR provider routing
- PaddleOCR provider 懒加载
- provider fallback
- provider_requested / provider_actual / fallback_reason 留痕

P15-C 已完成并收口：

- document.structured_extract
- rule extractor
- invoice / receipt 最小字段提取
- document_extraction_* steps

P15-D 已完成并提交：

- 飞书真实图片 / 文件入口
- image/post/file 消息进入任务系统
- image_key / file_key 透传
- 附件解析
- 飞书文件下载
- evidence 保存

P15-E 已完成并收口：

- PaddleOCR 真实读取飞书 evidence 图片
- provider_actual=paddle
- fallback_used=false
- raw_text 来自真实图片
- blocks_count / confidence 有效

不要回头重做 P15-A/B/C/D/E。

## 三、必须先读

开始开发前，必须先读：

1. AGENTS.md 当前阶段入口
2. docs/p15/p15f-project-plan.md
3. docs/p15/P15F-agent-prompt.md
4. docs/p15/p15f-boss-demo-sop.md
5. docs/p15/p15f-acceptance-checklist.md
6. P15-C / P15-D / P15-E 相关代码和测试
7. app/services/ocr/structured_extraction.py
8. app/schemas/document_extraction.py
9. app/graph/nodes/execute_action.py

如果文件不存在，先创建文档，不要直接写业务代码。

## 四、本轮目标

本轮只做：

真实 OCR raw_text 下的票据字段抽取增强。

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
- 不写数据库正式结果
- 不写飞书多维表
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

## 七、字段增强范围

第一版重点增强：

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

## 八、实现建议

建议采用：

规则增强 + OCR 行归一化 + 候选字段评分

可以继续增强：

app/services/ocr/structured_extraction.py

也可以新增：

app/services/ocr/invoice_field_extractor.py

建议不要把字段规则写进 execute_action.py。

## 九、OCR 文本归一化要求

需要支持：

- 全角冒号 / 半角冒号统一
- 中文括号统一
- ￥ / ¥ / 人民币 归一为 CNY
- 多空格清理
- 金额中的逗号清理
- 日期格式统一
- 常见 OCR 分隔符清理

日期统一成：

YYYY-MM-DD

支持：

- 2024年04月07日
- 2024/04/07
- 2024-04-07

## 十、金额候选评分要求

不能简单取第一个金额。

金额候选来源包括：

- 价税合计
- 小写
- 合计金额
- 金额
- 税额
- 不含税金额
- 单价
- 数量

候选评分建议：

- 包含“价税合计”加分
- 包含“小写”加分
- 包含“金额”加分
- 包含“税额”降分
- 包含“单价”降分
- 包含“数量”降分

如果候选不唯一或置信不足：

- needs_review=true
- warning=金额候选不唯一，需要人工复核

## 十一、missing_reasons 要求

P15-F 除了 missing_fields，建议增加 missing_reasons。

示例：

buyer_name: 未找到购买方名称或名称行 OCR 不完整

字段缺失不能导致任务 failed。

## 十二、steps 留痕要求

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

## 十三、返回文案要求

飞书返回老板可读摘要，不直接返回 JSON 原文。

必须包含：

- 文档类型
- 整体置信度
- 是否需要人工复核
- 已提取字段
- 缺失字段
- 缺失原因
- 人工确认提醒

## 十四、测试要求

新增：

tests/test_p15f_real_ocr_field_extraction.py

建议新增 fixture：

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

## 十五、飞书实机验收要求

复用 P15-E 已经打通的真实发票图片。

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

## 十六、禁止收口条件

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
- P14 回归失败

## 十七、完成后回报格式

完成后必须回报：

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

不要编造实机结果。
没有跑飞书就明确说没有跑。