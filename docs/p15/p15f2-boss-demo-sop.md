
# P15-F2 老板演示 SOP：20 张发票 OCR / 字段抽取小样本评测基线

## 一、演示目标

验证系统可以对一批本地发票图片执行 OCR + 字段抽取，并输出可人工核对的质量评测表。

P15-F2 要演示：

- 可下载 20 张中文发票样本
- 可批量执行 PaddleOCR
- 可批量执行 rule_v2 字段抽取
- 可生成 summary.json
- 可生成 details.csv
- 可生成 failed_cases.json
- 无 labels.csv 时不宣称准确率
- 样本图片和评测输出不进 git

## 二、演示前提

P15-E 已完成真实 OCR 读图闭环。  
P15-F 已完成真实 OCR raw_text 下的字段抽取增强。

P15-F2 只做本地小样本质量评测。

不做：

- 飞书交互
- 人工确认闭环
- 字段修改命令
- 写入多维表
- 自动报销
- 自动付款
- 发票真伪校验
- RPA

## 三、安装依赖

```bash
cd ~/feishu-rpa-commerce-agent
source venv/bin/activate 2>/dev/null || source .venv/bin/activate

pip install -U huggingface_hub tqdm pillow
```

## 四、dry-run 下载检查

```bash
python scripts/download_hf_chinese_invoice_samples.py --dry-run
```

预期：

- 能读取 Hugging Face dataset 文件列表
- 中文图片候选数量 > 0
- 如果候选数量 >= 20，可进入下载
- dry-run 不实际下载图片

## 五、正式下载 20 张

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

预期：

```text
20
```

检查 manifest：

```bash
ls -la data/ocr_samples/hf_chinese_invoice_20
head -n 5 data/ocr_samples/hf_chinese_invoice_20/manifest.csv
```

## 六、批量评测

```bash
python scripts/evaluate_invoice_ocr_batch.py \
  --input-dir data/ocr_samples/hf_chinese_invoice_20 \
  --provider paddle
```

预期输出：

```text
data/ocr_eval_runs/<run_id>/summary.json
data/ocr_eval_runs/<run_id>/details.csv
data/ocr_eval_runs/<run_id>/failed_cases.json
```

## 七、查看 summary

```bash
cat data/ocr_eval_runs/<run_id>/summary.json | python3 -m json.tool
```

重点看：

- total_images
- processed_images
- ocr_success_count
- ocr_failed_count
- fallback_used_count
- fallback_rate
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

## 八、查看 details.csv

```bash
head -n 5 data/ocr_eval_runs/<run_id>/details.csv
```

确认字段适合人工核对：

- invoice_number
- invoice_date
- buyer_name
- seller_name
- total_amount
- tax_amount
- amount_without_tax
- manual_*_correct
- manual_note

## 九、查看 failed_cases

```bash
cat data/ocr_eval_runs/<run_id>/failed_cases.json | python3 -m json.tool
```

如果没有失败，可以为空列表。

如果有失败，必须能看出：

- image_file
- stage
- error
- fallback_reason
- provider_actual
- fallback_used

## 十、git 检查

```bash
git status --short
```

确认不能出现：

- data/hf_cache/
- data/ocr_samples/
- data/ocr_eval_runs/
- data/ocr_evidence/
- 真实发票图片
- PaddleOCR 模型缓存
- venv

## 十一、通过标准

P15-F2 通过标准：

- dry-run 成功
- 能下载 20 张图片
- manifest.csv 生成
- 批量评测脚本能处理 20 张图片
- summary.json 生成
- details.csv 生成
- failed_cases.json 生成
- 没有 labels.csv 时不宣称准确率
- details.csv 适合人工核对
- 样本图片和评测输出不进 git
- 不触发正式写入 / RPA

## 十二、演示话术

可以这样说明：

P15-F2 不是准确率结论阶段，而是小样本质量评测基线。  
系统会先随机下载 20 张中文发票图片，本地批量执行 PaddleOCR 与 rule_v2 字段抽取，并生成 summary、details、failed_cases 三类评测输出。  

因为当前还没有人工标注 labels，所以本轮只看 OCR 成功率、fallback 率、字段非空率、缺失字段分布和 needs_review 比例，不宣称准确率。  
后续用户可以基于 details.csv 人工核对 20 张样本，再决定是否扩大到 100 张。