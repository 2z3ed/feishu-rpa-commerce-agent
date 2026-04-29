# P15-D Agent 开发约束：飞书文件入口接入

## 一、当前唯一主线

当前唯一主线是：

P15-D：飞书文件入口接入

本轮只做飞书图片 / 文件附件进入 OCR 链路。

不要做人工确认。
不要写正式业务结果。
不要做多文件批量。
不要做 PDF 多页 OCR。

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
- 飞书实机验收通过

不要回头重做 P15-A/B/C。

## 三、必须先读

开始开发前，必须先读：

1. AGENTS.md 当前阶段入口
2. docs/p15/p15d-project-plan.md
3. docs/p15/P15D-agent-prompt.md
4. docs/p15/p15d-boss-demo-sop.md
5. docs/p15/p15d-acceptance-checklist.md
6. P15-A / P15-B / P15-C 相关代码和测试
7. 飞书 longconn / message service / file client 相关代码

如果文件不存在，先创建文档，不要直接写业务代码。

## 四、本轮目标

本轮只做：

飞书文件入口接入。

目标链路：

飞书图片 / 文件附件  
→ 解析附件  
→ 下载文件  
→ 保存 evidence  
→ 构造 OCRDocumentInput  
→ 调用 document.ocr_recognize 或 document.structured_extract 既有链路  
→ 返回 OCR 或字段结果  
→ task_steps 留痕  

## 五、本轮允许做

允许做：

- 新增飞书附件 schema
- 新增飞书附件解析 service
- 新增飞书文件下载 service
- 新增 evidence 保存逻辑
- 新增 file_hash / size / mime_type 安全摘要
- 接入 document.ocr_recognize
- 接入 document.structured_extract
- 新增附件相关 steps
- 新增无附件友好提示
- 新增类型不支持友好提示
- 新增文件过大友好提示
- 新增 P15-D 测试
- 更新 .env.example
- 新增 P15-D 文档

## 六、本轮禁止做

禁止做：

- 不做 P15-E 人工确认与字段修正闭环
- 不做 P15-F 结构化结果写入与归档
- 不做多文件批量处理
- 不做 PDF 多页 OCR
- 不做复杂文件预览
- 不做字段人工修正
- 不写数据库正式结果
- 不写飞书多维表
- 不做自动报销
- 不做自动付款
- 不做税务合规判断
- 不做发票真伪校验
- 不触发 RPA
- 不改 B 项目
- 不重构 P14-A/B/C/D
- 不破坏 P15-A/B/C
- 不提交真实 .env
- 不提交真实票据 / 客户文件
- 不提交 data/ocr_evidence 临时文件
- 不泄露飞书 token / 文件下载 URL

## 七、intent 要求

P15-D 原则上不新增新 intent。

增强既有：

- document.ocr_recognize
- document.structured_extract

行为：

- document.ocr_recognize：下载附件后进入 OCR
- document.structured_extract：下载附件后进入 OCR，再进入结构化提取

## 八、附件支持范围

第一版支持：

- 单张图片
- 单个文件
- image/png
- image/jpeg

PDF 第一版可以识别后提示暂不支持，或者仅做保存但不进入 OCR。

不支持：

- 多图
- 多文件
- zip
- Word
- Excel
- 多页 PDF OCR
- 大文件

## 九、环境变量

建议新增：

ENABLE_FEISHU_FILE_DOWNLOAD=false  
FEISHU_FILE_EVIDENCE_DIR=data/ocr_evidence  
FEISHU_FILE_MAX_SIZE_MB=10  
FEISHU_FILE_ALLOWED_MIME_TYPES=image/png,image/jpeg,application/pdf  

注意：

- 可以修改 .env.example
- 不要修改真实 .env
- 如需实机启用，必须回报真实 .env 需要人工同步哪些变量
- evidence 目录不得提交 git

## 十、schema 要求

建议新增：

app/schemas/feishu_file.py

至少包含：

FeishuAttachmentMeta：

- attachment_type
- message_id
- file_key
- image_key
- file_name
- mime_type
- size_bytes

DownloadedFeishuFile：

- document_id
- file_name
- mime_type
- file_path
- source
- file_size
- file_hash
- attachment_type

## 十一、service 要求

建议新增：

app/services/feishu/file_attachment.py

核心能力：

- resolve_feishu_attachments(message_payload)
- select_single_supported_attachment(attachments)
- download_feishu_file(attachment, task_id)
- build_ocr_input_from_downloaded_file(downloaded_file, requested_by, hint_document_type)

如果仓库已有相同能力，以现有结构为准，不重复造第二套。

单测中必须 mock 飞书下载 API，不真实调飞书。

## 十二、steps 留痕

新增：

- feishu_attachment_detected
- feishu_attachment_missing
- feishu_file_download_started
- feishu_file_download_succeeded
- feishu_file_download_failed
- feishu_file_unsupported_type
- feishu_file_too_large

detail 可以包含：

- attachment_type
- mime_type
- file_name
- size_bytes
- file_hash
- evidence_relative_path
- error

禁止写入：

- 飞书 token
- download token
- API Key
- 完整下载 URL
- 真实敏感绝对路径
- 大段文件内容

## 十三、无附件策略

ENABLE_FEISHU_FILE_DOWNLOAD=true 时：

如果用户说“识别这张发票 / 提取这张发票字段”，但消息里没有附件，返回：

我还没有收到可识别的图片或文件。请上传发票图片后再发送识别命令。

并写：

feishu_attachment_missing

ENABLE_FEISHU_FILE_DOWNLOAD=false 时：

仍允许 P15-A/B/C mock 路径跑通，避免破坏测试。

## 十四、错误处理要求

### 文件下载失败

返回：

文件下载失败，请重新上传图片后再试。

steps：

feishu_file_download_failed

### 类型不支持

返回：

当前只支持图片文件，PDF/其他格式将在后续阶段支持。

steps：

feishu_file_unsupported_type

### 文件过大

返回：

文件超过当前识别大小限制，请压缩或上传更清晰的小图。

steps：

feishu_file_too_large

所有错误都不能：

- 抛 500
- 暴露 traceback
- 泄露 token
- 泄露下载 URL

## 十五、action_executed.detail 要求

可增加：

- attachment_type
- attachment_mime_type
- attachment_size_bytes
- attachment_downloaded
- attachment_hash
- evidence_saved
- evidence_relative_path
- file_source=feishu
- formal_write=false

禁止写：

- 完整绝对路径
- 下载 URL
- token
- 完整文件内容

## 十六、测试要求

新增：

tests/test_p15d_feishu_file_entry.py

至少覆盖：

1. 能从模拟飞书 event 中识别 image 附件
2. 能从模拟飞书 event 中识别 file 附件
3. 无附件时返回 friendly missing
4. unsupported mime type 返回 friendly unsupported
5. 文件过大返回 friendly too_large
6. 下载成功后能构造 OCRDocumentInput
7. document.ocr_recognize 能使用 downloaded file_path
8. document.structured_extract 能使用 downloaded file_path
9. steps 有 feishu_file_download_started / succeeded
10. 不泄露 token
11. 不写正式业务结果
12. 不触发 RPA
13. P15-A/B/C 回归不退化
14. P14 回归不退化

执行建议：

pytest -q tests/test_p15d_feishu_file_entry.py
pytest -q tests/test_p15c_document_structured_extraction.py
pytest -q tests/test_p15b_ocr_paddle_provider.py
pytest -q tests/test_p15a_ocr_document_mock.py
pytest -q tests/test_p14d_llm_action_plan.py
pytest -q tests/test_p14c_llm_anomaly_explanation.py
pytest -q tests/test_p14b_llm_monitor_summary.py
pytest -q tests/test_p14a_llm_intent_fallback.py

## 十七、完成后回报格式

完成后必须回报：

A. 先读了哪些文件  
B. 是否新增 intent，还是增强既有 document intent  
C. 飞书附件 schema 如何设计  
D. 附件解析 / 下载 service 如何设计  
E. 支持哪些附件类型  
F. 无附件 / 类型不支持 / 文件过大 / 下载失败如何处理  
G. 如何构造 OCRDocumentInput  
H. steps 如何留痕  
I. 是否修改 .env.example  
J. 真实 .env 需要人工同步哪些变量  
K. 改了哪些文件  
L. 执行了哪些测试  
M. 测试结果  
N. 是否可以进入飞书实机验收  

不要编造实机结果。
没有跑飞书就明确说没有跑。