# P15-F2 Agent 开发约束：20 张发票 OCR / 字段抽取小样本评测基线

## 一、当前唯一主线

当前唯一主线是：

P15-F2：20 张发票 OCR / 字段抽取小样本评测基线

本轮只做本地脚本评测。

不要做飞书交互。
不要做人审确认闭环。
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

P15-F 已完成并收口：

- rule_v2 字段抽取增强
- 日期归一化
- 金额候选评分
- missing_reasons
- needs_review / warning

不要回头重做 P15-A/B/C/D/E/F。

## 三、必须先读

开始开发前，必须先读：

1. AGENTS.md 当前阶段入口
2. docs/p15/p15f2-project-plan.md
3. docs/p15/P15F2-agent-prompt.md
4. docs/p15/p15f2-boss-demo-sop.md
5. docs/p15/p15f2-acceptance-checklist.md
6. P15-F 相关代码和测试
7. app/services/ocr/document_ocr.py
8. app/services/ocr/structured_extraction.py
9. app/services/ocr/invoice_field_extractor.py
10. app/schemas/ocr_document.py
11. app/schemas/document_extraction.py

如果文件不存在，先创建文档，不要直接写业务代码。

## 四、本轮目标

本轮只做：

20 张发票 OCR / 字段抽取小样本评测基线。

目标链路：

下载 20 张中文发票样本  
→ 本地批量跑 PaddleOCR  
→ 调用 rule_v2 字段抽取  
→ 输出 summary.json  
→ 输出 details.csv  
→ 输出 failed_cases.json  
→ 供用户后续人工核对字段准确度  

## 五、本轮允许做

允许做：

- 新增 Hugging Face 中文发票样本下载脚本
- 默认下载 20 张图片
- 支持 dry-run
- 支持 limit / seed / output-dir / cache-dir
- 生成 manifest.csv
- 新增批量 OCR + 字段抽取评测脚本
- 输出 summary.json
- 输出 details.csv
- 输出 failed_cases.json
- 输出无标注质量指标
- 更新 .gitignore
- 新增 P15-F2 测试
- 新增 P15-F2 文档

## 六、本轮禁止做

禁止做：

- 不做飞书交互
- 不做人审确认闭环
- 不做字段修改命令
- 不写数据库正式结果
- 不写飞书多维表
- 不做自动报销
- 不做自动付款
- 不做税务合规判断
- 不做发票真伪校验
- 不触发 RPA
- 不改 B 项目
- 不重构 P15-D/E/F
- 不提交样本图片
- 不提交 HF cache
- 不提交 OCR eval runs
- 不提交完整 OCR 原文大文件
- 不提交真实发票图片
- 不提交 PaddleOCR 模型缓存
- 不提交 venv

## 七、下载脚本要求

新增：

scripts/download_hf_chinese_invoice_samples.py

功能要求：

- 使用 huggingface_hub 免登录读取数据集文件列表
- 默认 repo-id=AlroWilde/invoice-checkmark-annotations
- 默认 language-prefix=Chinese/
- 默认 output-dir=data/ocr_samples/hf_chinese_invoice_20
- 默认 cache-dir=data/hf_cache/invoice_checkmark_annotations
- 默认 limit=20
- 默认 seed=42
- 支持 --dry-run
- 生成 manifest.csv
- 复制图片到 output-dir
- 文件名安全可复现
- 不提交下载图片

可以参考用户提供的 download_hf_chinese_invoice_100_no_login.py，但建议改成通用样本脚本名和 limit=20。

## 八、评测脚本要求

新增：

scripts/evaluate_invoice_ocr_batch.py

功能要求：

- 扫描 input-dir 中的图片
- 支持 --input-dir
- 支持 --output-root
- 支持 --run-id
- 支持 --provider
- 支持 --limit
- 支持 --labels-csv 可选
- 支持 --save-raw-text 可选，默认 false
- 每张图片调用 run_document_ocr
- OCR 成功后调用 run_document_extraction
- 单张失败不影响整批
- 输出 summary.json
- 输出 details.csv
- 输出 failed_cases.json

默认不保存完整 raw_text。

可以保存 raw_text_snippet，限制长度，例如 200 字。

## 九、无 labels.csv 指标要求

没有 labels.csv 时，只输出质量指标，不宣称准确率。

必须统计：

- total_images
- processed_images
- ocr_success_count
- ocr_failed_count
- fallback_used_count
- fallback_rate
- raw_text_empty_count
- average_raw_text_length
- average_blocks_count
- extraction_success_count
- extraction_failed_count
- needs_review_count
- needs_review_rate
- field_non_empty_rate
- missing_fields_distribution
- fallback_reason_distribution
- error_distribution

字段非空率至少包含：

- invoice_number
- invoice_date
- buyer_name
- seller_name
- total_amount
- tax_amount
- amount_without_tax

## 十、details.csv 要求

details.csv 需要方便人工核对。

建议字段：

- index
- image_file
- status
- provider_actual
- fallback_used
- fallback_reason
- raw_text_length
- blocks_count
- ocr_confidence
- extraction_status
- document_type
- overall_confidence
- needs_manual_review
- missing_fields
- invoice_number
- invoice_date
- buyer_name
- seller_name
- total_amount
- tax_amount
- amount_without_tax
- currency
- warnings
- error
- raw_text_snippet
- manual_invoice_number_correct
- manual_invoice_date_correct
- manual_buyer_name_correct
- manual_seller_name_correct
- manual_total_amount_correct
- manual_note

人工核对列可以留空。

## 十一、failed_cases.json 要求

每个失败样本至少包含：

- image_file
- stage
- error
- fallback_reason
- provider_actual
- fallback_used

## 十二、.gitignore 要求

必须确保以下路径不进入 git：

data/hf_cache/
data/ocr_samples/
data/ocr_eval_runs/
data/ocr_evidence/

如果没有，需要更新 .gitignore。

## 十三、测试要求

新增：

tests/test_p15f2_invoice_batch_eval.py

测试至少覆盖：

1. 下载脚本 safe_output_name 稳定
2. 下载脚本 dry-run 不落图
3. 评测脚本能扫描图片目录
4. 评测脚本能处理 OCR 成功结果
5. 评测脚本能处理 OCR fallback
6. 评测脚本能处理 extraction missing_fields
7. summary.json 指标正确
8. details.csv 字段完整
9. failed_cases.json 可生成
10. 不要求真实 PaddleOCR 参与单测

单测中不要真实访问 Hugging Face。
单测中不要真实跑 PaddleOCR。

## 十四、本地执行建议

安装依赖：

```bash
pip install -U huggingface_hub tqdm pillow
```

dry-run：

```bash
python scripts/download_hf_chinese_invoice_samples.py --dry-run
```

正式下载 20 张：

```bash
python scripts/download_hf_chinese_invoice_samples.py \
  --output-dir data/ocr_samples/hf_chinese_invoice_20 \
  --limit 20 \
  --seed 42
```

验证数量：

```bash
find data/ocr_samples/hf_chinese_invoice_20 -type f \( \
  -name "*.jpg" -o \
  -name "*.jpeg" -o \
  -name "*.png" -o \
  -name "*.webp" \
\) | wc -l
```

批量评测：

```bash
python scripts/evaluate_invoice_ocr_batch.py \
  --input-dir data/ocr_samples/hf_chinese_invoice_20 \
  --provider paddle
```

## 十五、禁止收口条件

出现以下情况不允许收口：

- 样本图片进入 git
- HF cache 进入 git
- data/ocr_eval_runs 进入 git
- 真实发票图片进入 git
- 未标注数据却宣称准确率
- details.csv 不适合人工核对
- 批量脚本遇单张失败就整体崩溃
- failed_cases.json 缺失
- summary.json 缺失
- P15-F 回归失败
- P14 回归失败

## 十六、完成后回报格式

完成后必须回报：

A. 先读了哪些文件  
B. 是否新增下载脚本，脚本路径是什么  
C. 是否新增批量评测脚本，脚本路径是什么  
D. 下载脚本参数和默认输出目录是什么  
E. 评测脚本输出哪些文件  
F. 无 labels.csv 时输出哪些质量指标  
G. 是否修改 .gitignore  
H. 改了哪些文件  
I. 执行了哪些测试  
J. 测试结果  
K. 是否实际 dry-run / 下载 20 张 / 批量评测  
L. 是否确认样本图片 / cache / eval runs 没有进入 git  
M. 是否可以进入收口清理  

不要编造结果。
没有实际下载就明确说没有下载。
没有实际批量评测就明确说没有评测。