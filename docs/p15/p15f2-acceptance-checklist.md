# P15-F2 验收清单：20 张发票 OCR / 字段抽取小样本评测基线

## 一、阶段信息

阶段：

P15-F2：20 张发票 OCR / 字段抽取小样本评测基线

验收目标：

本地随机下载 20 张中文发票样本，批量跑 PaddleOCR + rule_v2 字段抽取，生成无标注质量评测报告和可人工核对的 details.csv。

## 二、文档验收

必须存在：

- AGENTS.md 当前阶段入口
- docs/p15/p15f2-project-plan.md
- docs/p15/P15F2-agent-prompt.md
- docs/p15/p15f2-boss-demo-sop.md
- docs/p15/p15f2-acceptance-checklist.md

检查命令：

```bash
ls -la docs/p15
```

## 三、下载脚本验收

必须存在：

scripts/download_hf_chinese_invoice_samples.py

通过标准：

- 支持 --dry-run
- 支持 --repo-id
- 支持 --language-prefix
- 支持 --output-dir
- 支持 --cache-dir
- 支持 --limit
- 支持 --seed
- 默认 limit=20
- 生成 manifest.csv
- 文件名安全可复现

dry-run：

```bash
python scripts/download_hf_chinese_invoice_samples.py --dry-run
```

正式下载：

```bash
python scripts/download_hf_chinese_invoice_samples.py \
  --output-dir data/ocr_samples/hf_chinese_invoice_20 \
  --limit 20 \
  --seed 42
```

数量检查：

```bash
find data/ocr_samples/hf_chinese_invoice_20 -type f \( \
  -name "*.jpg" -o \
  -name "*.jpeg" -o \
  -name "*.png" -o \
  -name "*.webp" \
\) | wc -l
```

通过标准：

```text
20
```

## 四、评测脚本验收

必须存在：

scripts/evaluate_invoice_ocr_batch.py

通过标准：

- 支持 --input-dir
- 支持 --output-root
- 支持 --run-id
- 支持 --provider
- 支持 --limit
- 支持 --labels-csv 可选
- 支持 --save-raw-text 可选，默认 false
- 单张失败不影响整批
- 输出 summary.json
- 输出 details.csv
- 输出 failed_cases.json

执行：

```bash
python scripts/evaluate_invoice_ocr_batch.py \
  --input-dir data/ocr_samples/hf_chinese_invoice_20 \
  --provider paddle
```

## 五、summary.json 验收

必须包含：

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

没有 labels.csv 时不得包含“accuracy”结论或宣称准确率。

## 六、details.csv 验收

必须适合人工核对。

建议包含：

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

## 七、failed_cases.json 验收

必须存在。

每个失败样本建议包含：

- image_file
- stage
- error
- fallback_reason
- provider_actual
- fallback_used

如果没有失败，可以是空列表。

## 八、.gitignore 验收

必须确认以下路径被忽略：

- data/hf_cache/
- data/ocr_samples/
- data/ocr_eval_runs/
- data/ocr_evidence/

git status 不能出现：

- 样本图片
- HF cache
- OCR eval runs
- evidence
- 真实发票图片
- PaddleOCR 模型缓存
- venv

## 九、测试验收

建议执行：

```bash
pytest -q tests/test_p15f2_invoice_batch_eval.py
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

单测不能真实访问 Hugging Face。  
单测不能真实跑 PaddleOCR。

## 十、允许的验收结果

允许：

- 部分图片 OCR 失败
- 部分图片 fallback
- 部分字段缺失
- needs_review 比例较高
- 没有 labels.csv，因此无准确率

但必须：

- 脚本不中断整批
- summary.json 有统计
- details.csv 可人工核对
- failed_cases.json 可定位失败样本
- 不提交样本和评测输出

## 十一、禁止收口条件

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

## 十二、最终收口回报模板

A. 文档是否齐全  
B. 下载脚本是否可用  
C. dry-run 是否成功  
D. 是否成功下载 20 张图片  
E. manifest.csv 是否生成  
F. 批量评测脚本是否可用  
G. summary.json / details.csv / failed_cases.json 是否生成  
H. 无 labels.csv 时是否未宣称准确率  
I. details.csv 是否适合人工核对  
J. .gitignore 是否覆盖样本 / cache / eval runs  
K. 是否确认样本图片 / cache / eval runs 没有进入 git  
L. 测试是否通过  
M. 是否允许 P15-F2 收口  