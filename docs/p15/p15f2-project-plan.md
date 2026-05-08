# P15-F2 开发主线文档：20 张发票 OCR / 字段抽取小样本评测基线

## 一、阶段名称

P15-F2：20 张发票 OCR / 字段抽取小样本评测基线

## 二、当前背景

P15-D 已经打通飞书真实图片上传、附件解析、文件下载、evidence 保存。

P15-E 已经打通 PaddleOCR 真实读图：

- 飞书真实图片可以下载到 evidence
- PaddleOCR 可以读取 evidence 图片
- provider_actual=paddle
- fallback_used=false
- raw_text 来自真实图片
- blocks_count / confidence 有效

P15-F 已经完成真实 OCR raw_text 下的字段抽取增强：

- rule_v2
- 发票号码提取
- 日期归一化
- 购买方 / 销售方提取
- 金额候选评分
- missing_fields / missing_reasons
- needs_review / warning

现在需要一个小样本评测基线，先用 20 张随机中文发票图片验证当前 OCR + 字段抽取质量。

因为当前样本没有标准答案 labels，所以本轮不宣称“准确率”。

本轮先做无标注质量评测：

- OCR 是否跑通
- fallback 是否发生
- raw_text 是否为空
- blocks_count 分布
- 字段非空率
- missing_fields 分布
- needs_review 比例
- 失败样本清单

## 三、本轮唯一目标

本轮只做：

20 张本地发票图片批量质量评测基线。

目标链路：

下载 20 张中文发票样本  
→ 本地批量跑 PaddleOCR  
→ 调用 rule_v2 字段抽取  
→ 生成 summary.json  
→ 生成 details.csv  
→ 生成 failed_cases.json  
→ 供用户后续人工核对字段准确度  

## 四、P15-F2 定位

P15-F2 是批量评测阶段。

P15-F2 不是：

- 飞书交互阶段
- 人工确认阶段
- 字段修改阶段
- 正式写表阶段
- 自动报销阶段
- RPA 阶段

P15-F2 要验证的是：

- 当前 PaddleOCR + rule_v2 在 20 张随机发票图片上的可运行性
- 当前字段抽取结果是否适合人工核对
- 哪些字段最容易缺失
- 哪些样本容易失败
- 后续是否值得扩大到 100 张

## 五、本轮允许做

允许做：

- 新增 Hugging Face 发票样本下载脚本
- 默认下载 20 张中文发票图片
- 支持 --dry-run
- 支持 --limit / --seed / --output-dir / --cache-dir
- 生成 manifest.csv
- 新增批量 OCR + 字段抽取评测脚本
- 输出 summary.json
- 输出 details.csv
- 输出 failed_cases.json
- 输出无标注质量指标
- 更新 .gitignore
- 新增 P15-F2 文档
- 新增脚本级测试

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

## 七、阶段拆分

### P15-F2-A：样本下载脚本

新增：

scripts/download_hf_chinese_invoice_samples.py

或沿用并泛化：

scripts/download_hf_chinese_invoice_100_no_login.py

建议最终使用更通用名称：

scripts/download_hf_chinese_invoice_samples.py

功能：

- 免登录读取 HF dataset 文件列表
- 默认 repo-id=AlroWilde/invoice-checkmark-annotations
- 默认 language-prefix=Chinese/
- 默认 limit=20
- 默认 seed=42
- 默认输出 data/ocr_samples/hf_chinese_invoice_20
- 默认缓存 data/hf_cache/invoice_checkmark_annotations
- 支持 --dry-run
- 生成 manifest.csv

### P15-F2-B：批量评测脚本

新增：

scripts/evaluate_invoice_ocr_batch.py

输入：

data/ocr_samples/hf_chinese_invoice_20/

输出：

data/ocr_eval_runs/<run_id>/summary.json  
data/ocr_eval_runs/<run_id>/details.csv  
data/ocr_eval_runs/<run_id>/failed_cases.json  

执行流程：

每张图片  
→ OCRDocumentInput  
→ run_document_ocr(provider=paddle)  
→ run_document_extraction(rule_v2)  
→ 汇总质量指标  

### P15-F2-C：人工核对准备

details.csv 要适合用户后续人工核对。

建议输出字段：

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
- manual_invoice_number_correct
- manual_invoice_date_correct
- manual_buyer_name_correct
- manual_seller_name_correct
- manual_total_amount_correct
- manual_note

人工核对列可以先留空。

## 八、无标注质量指标

没有 labels.csv 时，本轮只输出：

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
  - invoice_number
  - invoice_date
  - buyer_name
  - seller_name
  - total_amount
  - tax_amount
  - amount_without_tax
- missing_fields_distribution
- fallback_reason_distribution
- error_distribution

禁止在没有 labels.csv 的情况下宣称准确率。

## 九、有 labels.csv 的后续扩展

本轮可以预留 labels.csv 支持，但不是必须完成。

后续如果有 labels.csv，可以增加：

- invoice_number exact match
- invoice_date exact match
- total_amount exact match
- buyer_name fuzzy match
- seller_name fuzzy match

labels.csv 建议字段：

- image_file
- invoice_number
- invoice_date
- buyer_name
- seller_name
- total_amount
- tax_amount
- amount_without_tax
- currency

## 十、.gitignore 要求

必须确保以下路径不进入 git：

data/hf_cache/
data/ocr_samples/
data/ocr_eval_runs/
data/ocr_evidence/

如果没有，需要更新 .gitignore。

## 十一、脚本参数建议

### download_hf_chinese_invoice_samples.py

建议参数：

- --repo-id
- --language-prefix
- --output-dir
- --cache-dir
- --limit
- --seed
- --dry-run

默认：

- repo-id=AlroWilde/invoice-checkmark-annotations
- language-prefix=Chinese/
- output-dir=data/ocr_samples/hf_chinese_invoice_20
- cache-dir=data/hf_cache/invoice_checkmark_annotations
- limit=20
- seed=42

### evaluate_invoice_ocr_batch.py

建议参数：

- --input-dir
- --manifest
- --output-root
- --run-id
- --provider
- --limit
- --labels-csv
- --save-raw-text
- --dry-run

默认：

- input-dir=data/ocr_samples/hf_chinese_invoice_20
- output-root=data/ocr_eval_runs
- provider=paddle
- save-raw-text=false

注意：

默认不保存完整 raw_text 到 details.csv，避免泄露大段票据内容。

如需人工核对，可以保存 raw_text_snippet，不超过 200 字。

## 十二、评测输出要求

### summary.json

保存聚合指标。

### details.csv

保存每张图片的处理结果与字段抽取结果。

### failed_cases.json

保存失败样本列表，字段包括：

- image_file
- stage
- error
- fallback_reason
- provider_actual
- fallback_used

## 十三、安全要求

不得输出：

- 完整真实发票图片到 git
- 完整 OCR 原文大文件到 git
- token
- download URL
- API Key
- 真实敏感绝对路径

CSV / JSON 默认只保存：

- 字段值
- 安全摘要
- 相对路径
- 统计指标
- raw_text_snippet

## 十四、测试建议

新增：

tests/test_p15f2_invoice_batch_eval.py

至少覆盖：

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

单测中不要真实访问 Hugging Face，不要真实跑 PaddleOCR。

## 十五、本地执行建议

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

## 十六、最低通过标准

P15-F2 最低通过：

- download 脚本存在
- dry-run 成功
- 能下载 20 张图片
- manifest.csv 生成
- evaluate 脚本存在
- 能批量处理 20 张图片
- summary.json 生成
- details.csv 生成
- failed_cases.json 生成
- 无 labels.csv 时不宣称准确率
- details.csv 适合人工核对
- .gitignore 已覆盖样本 / cache / eval runs
- 样本图片不进入 git
- P15-A/B/C/D/E/F 回归不退化
- P14 回归不退化

## 十七、禁止收口条件

以下任一情况不允许收口：

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

## 十八、完成后回报格式

Agent 完成后必须按以下格式回报：

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