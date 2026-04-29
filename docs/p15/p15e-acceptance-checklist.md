# P15-E 验收清单：真实 OCR Provider 实机读取闭环

## 一、阶段信息

阶段：

P15-E：真实 OCR Provider 实机读取闭环

验收目标：

飞书真实上传图片后，系统使用 PaddleOCR 真实读取图片内容，raw_text 不再来自 mock 固定文本。

## 二、文档验收

必须存在：

- AGENTS.md 当前阶段入口
- docs/p15/p15e-project-plan.md
- docs/p15/P15E-agent-prompt.md
- docs/p15/p15e-boss-demo-sop.md
- docs/p15/p15e-acceptance-checklist.md

检查命令：

```bash
ls -la docs/p15
```

## 三、配置验收

实机验收建议：

```env
ENABLE_FEISHU_FILE_DOWNLOAD=true
FEISHU_FILE_EVIDENCE_DIR=data/ocr_evidence
FEISHU_FILE_MAX_SIZE_MB=10
FEISHU_FILE_ALLOWED_MIME_TYPES=image/png,image/jpeg

ENABLE_OCR_DOCUMENT_RECOGNIZE=true
OCR_DOCUMENT_PROVIDER=paddle
OCR_PADDLE_ENABLED=true
OCR_PADDLE_LANG=ch
OCR_PADDLE_USE_GPU=false

ENABLE_DOCUMENT_STRUCTURED_EXTRACTION=true
DOCUMENT_EXTRACTION_PROVIDER=rule
DOCUMENT_EXTRACTION_TIMEOUT_SECONDS=10
```

通过标准：

- 真实 .env 不进入 git
- worker 实际使用 paddle 配置
- 不能仍然是 OCR_DOCUMENT_PROVIDER=mock
- evidence 不进入 git

## 四、PaddleOCR 安装验收

检查：

```bash
python - <<'PY'
try:
    import paddleocr
    print("paddleocr installed", getattr(paddleocr, "__version__", "unknown"))
except Exception as e:
    print("paddleocr not available:", repr(e))
PY
```

通过标准：

- PaddleOCR 在当前 venv 可 import
- 记录版本
- 安装失败不能伪造真实 OCR 验收
- 不提交 venv / 模型缓存

## 五、样例图片验收

使用自造样例图片，不使用真实敏感发票。

建议图片内容：

```text
发票号码：987654321
开票日期：2026-04-29
购买方：深圳测试科技有限公司
金额：256.80
```

通过标准：

- OCR raw_text 能包含部分样例内容
- 不再返回 P15-A mock 固定文本
- 真实样例图片不进入 git

## 六、OCR provider 验收

通过标准：

- OCR_DOCUMENT_PROVIDER=paddle
- OCR_PADDLE_ENABLED=true
- provider_requested=paddle
- provider_actual=paddle
- provider=paddle
- fallback_used=false
- blocks_count > 0
- confidence 有值
- raw_text_length > 0

## 七、mock 区分验收

不允许出现：

```text
发票号码：12345678
开票日期：2026-04-27
购买方：测试公司
金额：128.50
```

除非是明确 fallback mock 场景。

如果配置为 paddle 且 OCR 成功，结果仍然是 mock 固定文本，不允许收口。

## 八、结构化提取验收

飞书上传样例图片并发送：

```text
提取这张发票字段
```

通过标准：

- ocr_document_succeeded
- provider_actual=paddle
- fallback_used=false
- document_extraction_succeeded
- 字段结果来自真实 OCR raw_text
- 可允许部分字段缺失
- needs_manual_review=true
- 不写正式业务结果

## 九、fallback 验收

制造 provider error 或错误图片路径。

通过标准：

- ocr_document_fallback_used
- fallback_reason 有值
- provider_actual=mock
- fallback_used=true
- 不报 500
- 不暴露 traceback
- 不假装真实 OCR 成功

## 十、steps 留痕验收

必须能看到：

- feishu_attachment_detected
- feishu_file_download_started
- feishu_file_download_succeeded
- ocr_document_started
- ocr_document_succeeded
- document_extraction_started
- document_extraction_succeeded

fallback 场景应能看到：

- ocr_document_fallback_used

detail 不得包含：

- API Key
- token
- 下载 URL
- 完整绝对路径
- 完整 OCR 原文
- 大段文件内容
- 用户真实票据内容

## 十一、禁止动作验收

P15-E 不能触发：

- 字段人工修正
- 写数据库正式结果
- 写飞书多维表
- 自动报销
- 自动付款
- 发票真伪校验
- RPA 执行

## 十二、测试验收

建议执行：

```bash
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

可选真实 PaddleOCR 测试：

```bash
RUN_PADDLE_OCR_REAL_TESTS=true pytest -q tests/test_p15e_real_paddle_smoke.py
```

如果全量失败，必须说明：

- 失败文件
- 失败原因
- 是否与 P15-E 有关

## 十三、飞书实机验收

至少测试：

1. 上传自造样例图片 + 识别这张发票
2. 上传自造样例图片 + 提取这张发票字段
3. provider 失败 fallback

通过标准：

- OCR 结果来自图片
- provider_actual=paddle
- fallback_used=false
- blocks_count > 0
- confidence 有值
- 结构化提取可执行
- 不泄露敏感信息
- 不写正式业务结果
- 不触发 RPA

## 十四、禁止收口条件

出现以下情况，不允许收口：

- 配置为 paddle，但实际 provider_actual=mock 且无明确 fallback_reason
- OCR 返回仍然是 mock 固定文本
- raw_text 与上传图片内容无关
- blocks_count=0
- confidence 缺失
- PaddleOCR 未安装却宣称真实 OCR 通过
- PaddleOCR 失败但没有 fallback_reason
- 飞书用户看到 traceback
- steps 泄露绝对路径 / token / 下载 URL
- evidence / 真实图片 / 模型缓存进入 git
- 触发正式写入 / RPA
- P15-A/B/C/D 回归失败
- P14 回归失败

## 十五、最终收口回报模板

A. 文档是否齐全  
B. PaddleOCR 是否安装并记录版本  
C. OCR_DOCUMENT_PROVIDER 是否为 paddle  
D. 飞书图片是否进入真实 OCR provider  
E. provider_actual 是否为 paddle  
F. fallback_used 是否为 false  
G. raw_text 是否来自图片而非 mock  
H. blocks_count / confidence 是否有效  
I. structured extraction 是否基于真实 raw_text 执行  
J. fallback 场景是否可控  
K. steps 是否记录真实 provider  
L. 是否没有正式写入 / RPA  
M. 测试是否通过  
N. 飞书实机是否通过  
O. 是否允许 P15-E 收口  