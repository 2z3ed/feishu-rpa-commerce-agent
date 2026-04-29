# P15-D 开发主线文档：飞书文件入口接入

## 一、阶段名称

P15-D：飞书文件入口接入

## 二、当前背景

P15-A 已完成 OCR mock 骨架：

- document.ocr_recognize intent
- OCR 输入 / 输出 schema
- mock OCR provider
- OCR service 统一入口
- ocr_document_* steps 留痕

P15-B 已完成真实 OCR provider 接入基础：

- OCR provider routing：mock / paddle / unsupported
- PaddleOCR provider 懒加载
- provider 不可用时 fallback mock
- provider_requested / provider_actual / fallback_reason 留痕

P15-C 已完成结构化字段提取：

- document.structured_extract intent
- OCR raw_text → 结构化字段
- invoice / receipt 最小字段提取
- fields / overall_confidence / missing_fields / needs_manual_review
- document_extraction_* steps 留痕

目前缺少的是：

飞书真实文件入口。

用户虽然可以说“识别这张发票”“提取这张发票字段”，但系统还没有真正从飞书消息里下载附件。

P15-D 就是补齐：

飞书附件 → 本地文件 → OCR 输入。

## 三、本轮唯一目标

本轮只做：

飞书文件入口接入。

固定链路：

用户在飞书发送图片 / 文件 + 命令  
→ longconn 收到消息事件  
→ 解析 message 里的附件信息  
→ 获取 image_key / file_key / message_id  
→ 调飞书接口下载文件  
→ 保存到 evidence 目录  
→ 构造 OCRDocumentInput  
→ 调用 document OCR service  
→ 如 intent=document.structured_extract，再调用 structured extraction service  
→ 返回飞书结果  
→ task_steps 留痕  

## 四、P15-D 定位

P15-D 不是做 OCR 算法。

P15-D 不是做票据字段规则。

P15-D 要验证的是：

- 飞书消息附件能被识别
- 飞书图片 / 文件能被下载
- 文件能被安全保存到 evidence 目录
- 下载后的文件路径能进入 OCRDocumentInput
- 现有 document.ocr_recognize 能使用真实 file_path
- 现有 document.structured_extract 能使用真实 file_path
- 无附件 / 下载失败 / 类型不支持 / 文件过大均有友好提示
- task_steps 能完整追踪附件处理链路

## 五、本轮允许做

允许做：

- 新增飞书附件 schema
- 新增飞书附件解析 service
- 新增飞书文件下载 service
- 新增 evidence 保存逻辑
- 新增 file hash / size / mime_type 安全摘要
- 在 document.ocr_recognize 分支接入附件解析
- 在 document.structured_extract 分支接入附件解析
- 新增附件相关 steps
- 新增无附件友好提示
- 新增文件类型不支持提示
- 新增文件过大提示
- 更新 .env.example
- 新增 P15-D 测试
- 新增 P15-D 文档

## 六、本轮禁止做

禁止做：

- 不做 P15-E 人工确认与字段修正闭环
- 不做 P15-F 结果写入与归档
- 不做多文件批量处理
- 不做 PDF 多页 OCR
- 不做复杂文件预览
- 不做字段人工修正
- 不写入数据库正式结果
- 不写入飞书多维表
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

## 七、支持范围

P15-D 第一版只支持：

- 单张图片
- 单个文件
- image/png
- image/jpeg

可识别但暂不深度支持：

- application/pdf

PDF 第一版可以提示：

当前阶段暂不支持 PDF 多页解析，请先上传图片格式发票。

或仅保存文件并返回“PDF OCR 后续支持”。

不支持：

- 多图
- 多文件
- zip
- Word
- Excel
- 大文件
- 多页 PDF OCR

## 八、intent 关系

P15-D 不新增新的业务 intent。

它增强现有 intent：

- document.ocr_recognize
- document.structured_extract

示例：

识别这张发票  
→ document.ocr_recognize  
→ 如果消息有附件，则下载附件  
→ 调 OCR

提取这张发票字段  
→ document.structured_extract  
→ 如果消息有附件，则下载附件  
→ 调 OCR  
→ 调结构化提取

## 九、环境变量建议

建议新增到 .env.example：

```env
ENABLE_FEISHU_FILE_DOWNLOAD=false
FEISHU_FILE_EVIDENCE_DIR=data/ocr_evidence
FEISHU_FILE_MAX_SIZE_MB=10
FEISHU_FILE_ALLOWED_MIME_TYPES=image/png,image/jpeg,application/pdf
```

要求：

- 默认关闭
- 真实 .env 不自动修改
- 如需实机启用，由用户人工同步
- evidence 目录不得提交 git

## 十、建议新增 schema

建议新增：

app/schemas/feishu_file.py

### FeishuAttachmentMeta

建议字段：

- attachment_type：image / file
- message_id
- file_key
- image_key
- file_name
- mime_type
- size_bytes

### DownloadedFeishuFile

建议字段：

- document_id
- file_name
- mime_type
- file_path
- source
- file_size
- file_hash
- attachment_type

示例：

```json
{
  "document_id": "feishu-file-xxx",
  "file_name": "invoice.png",
  "mime_type": "image/png",
  "file_path": "data/ocr_evidence/TASK-xxx/invoice.png",
  "source": "feishu",
  "file_size": 12345,
  "file_hash": "sha256..."
}
```

## 十一、建议新增 service

建议新增：

app/services/feishu/file_attachment.py

或拆成：

- app/services/feishu/attachment_resolver.py
- app/services/feishu/file_downloader.py

第一版可以合并成一个文件，避免过度拆分。

建议核心函数：

- resolve_feishu_attachments(message_payload)
- select_single_supported_attachment(attachments)
- download_feishu_file(attachment, task_id)
- build_ocr_input_from_downloaded_file(downloaded_file, requested_by, hint_document_type)

如果仓库已有飞书 client / message 结构，以现有实现为准。

## 十二、附件 steps 设计

新增 steps：

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

P15-D 开启后，如果用户说：

识别这张发票  
提取这张发票字段  

但消息里没有附件，则返回：

我还没有收到可识别的图片或文件。请上传发票图片后再发送识别命令。

steps：

- feishu_attachment_missing

注意：

为了不破坏 P15-A/B/C 的测试，可以用配置控制：

ENABLE_FEISHU_FILE_DOWNLOAD=true 时：
- 飞书实机要求附件
- 没附件就提示缺附件

ENABLE_FEISHU_FILE_DOWNLOAD=false 时：
- 仍允许 mock OCR 路径跑通

## 十四、文件下载失败策略

下载失败时返回：

文件下载失败，请重新上传图片后再试。

steps：

- feishu_file_download_failed

不能：

- 抛 500
- 给飞书用户展示 traceback
- 泄露 token
- 泄露完整下载 URL

## 十五、文件类型不支持策略

如果文件类型不支持，返回：

当前只支持图片文件，PDF/其他格式将在后续阶段支持。

steps：

- feishu_file_unsupported_type

## 十六、文件过大策略

如果文件超过 FEISHU_FILE_MAX_SIZE_MB，返回：

文件超过当前识别大小限制，请压缩或上传更清晰的小图。

steps：

- feishu_file_too_large

## 十七、execute_action 接入建议

在 document.ocr_recognize / document.structured_extract 分支里：

1. 判断 ENABLE_FEISHU_FILE_DOWNLOAD 是否开启
2. 如果开启，尝试从消息上下文解析附件
3. 无附件则友好返回
4. 有附件则下载文件
5. 下载成功后构造 OCRDocumentInput
6. 后续复用 P15-A/B/C 原链路
7. 记录附件 steps
8. action_executed.detail 增加安全摘要

## 十八、action_executed.detail 建议字段

可增加：

- attachment_type
- attachment_mime_type
- attachment_size_bytes
- attachment_downloaded=true/false
- attachment_hash
- evidence_saved=true/false
- evidence_relative_path
- file_source=feishu
- formal_write=false

禁止：

- 完整绝对路径
- 下载 URL
- token
- 完整文件内容

## 十九、测试建议

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

单测中必须 mock 飞书下载 API，不要真实调飞书。

## 二十、飞书实机验收建议

### 用例 1：无附件提示

飞书发送：

识别这张发票

但不上传图片。

预期：

- 返回未收到图片或文件
- steps 有 feishu_attachment_missing
- 不报 500

### 用例 2：上传图片 + OCR 识别

飞书上传一张自造样例图片，并发送：

识别这张发票

预期：

- feishu_attachment_detected
- feishu_file_download_started
- feishu_file_download_succeeded
- ocr_document_succeeded
- 返回 OCR 摘要
- 不写正式业务结果
- 不触发 RPA

### 用例 3：上传图片 + 字段提取

飞书上传一张自造样例图片，并发送：

提取这张发票字段

预期：

- 附件下载成功
- OCR 成功
- structured extraction 成功
- 返回字段摘要
- 不写正式业务结果
- 不触发 RPA

### 用例 4：不支持类型

上传不支持文件，发送：

识别这个文件

预期：

- 返回类型不支持
- 不进入 OCR
- 不报 500

## 二十一、最低通过标准

P15-D 最低通过标准：

- 能识别飞书消息中的单张图片或单个文件附件
- 能下载附件并保存到 evidence 目录
- 能构造 OCRDocumentInput
- document.ocr_recognize 可使用下载后的 file_path
- document.structured_extract 可使用下载后的 file_path
- 无附件 / 下载失败 / 类型不支持 / 文件过大均有友好提示
- task_steps 有附件检测和下载留痕
- 不泄露 token / 真实敏感路径 / 大段文件内容
- 不写正式业务结果
- 不触发 RPA
- P15-A/B/C 回归不退化
- P14 回归不退化

## 二十二、完成后回报格式

Agent 完成后必须按以下格式回报：

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