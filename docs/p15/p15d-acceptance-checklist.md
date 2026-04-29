# P15-D 验收清单：飞书文件入口接入

## 一、阶段信息

阶段：

P15-D：飞书文件入口接入

验收目标：

让飞书图片 / 文件附件能够进入 OCR 与结构化提取链路。

## 二、文档验收

必须存在：

- AGENTS.md 当前阶段入口
- docs/p15/p15d-project-plan.md
- docs/p15/P15D-agent-prompt.md
- docs/p15/p15d-boss-demo-sop.md
- docs/p15/p15d-acceptance-checklist.md

检查命令：

```bash
ls -la docs/p15
```

## 三、配置验收

建议支持：

```env
ENABLE_FEISHU_FILE_DOWNLOAD=false
FEISHU_FILE_EVIDENCE_DIR=data/ocr_evidence
FEISHU_FILE_MAX_SIZE_MB=10
FEISHU_FILE_ALLOWED_MIME_TYPES=image/png,image/jpeg,application/pdf
```

通过标准：

- 默认关闭
- .env.example 更新
- 真实 .env 需要人工同步时必须明确提示
- evidence 不进入 git

## 四、附件解析验收

通过标准：

- 能识别 image 附件
- 能识别 file 附件
- 能提取 message_id / file_key / image_key
- 能识别 file_name / mime_type / size
- 多附件第一版可以友好提示暂不支持

## 五、下载验收

通过标准：

- 能开始下载
- 能保存 evidence
- 能计算 file_hash
- 能返回相对 evidence path
- 下载失败不报 500
- 不泄露 token / download URL

## 六、OCR 接入验收

通过标准：

- 下载后的 file_path 能构造 OCRDocumentInput
- document.ocr_recognize 能使用下载文件
- OCR service 能继续返回结果
- steps 有 ocr_document_succeeded

## 七、结构化提取接入验收

通过标准：

- document.structured_extract 能使用下载文件
- OCR 成功后能进入 rule extraction
- steps 有 document_extraction_succeeded
- 返回字段摘要
- 不写正式业务结果

## 八、无附件验收

飞书发送：

```text
识别这张发票
```

但不上传附件。

通过标准：

- 返回未收到图片或文件
- steps 有 feishu_attachment_missing
- 不报 500

## 九、类型不支持验收

上传不支持类型。

通过标准：

- 返回类型不支持
- steps 有 feishu_file_unsupported_type
- 不进入 OCR
- 不报 500

## 十、文件过大验收

模拟文件超过 FEISHU_FILE_MAX_SIZE_MB。

通过标准：

- 返回文件过大提示
- steps 有 feishu_file_too_large
- 不进入 OCR
- 不报 500

## 十一、steps 留痕验收

至少能看到：

- feishu_attachment_detected
- feishu_attachment_missing
- feishu_file_download_started
- feishu_file_download_succeeded
- feishu_file_download_failed
- feishu_file_unsupported_type
- feishu_file_too_large

detail 不得包含：

- API Key
- token
- 下载 URL
- 完整绝对路径
- 大段文件内容
- 用户真实票据内容

## 十二、禁止动作验收

P15-D 不能触发：

- 字段人工修正
- 写数据库正式结果
- 写飞书多维表
- 自动报销
- 自动付款
- 发票真伪校验
- RPA 执行

## 十三、测试验收

建议执行：

```bash
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
- 是否与 P15-D 有关

## 十四、飞书实机验收

至少测试：

1. 无附件 + 识别命令
2. 上传图片 + 识别命令
3. 上传图片 + 字段提取命令
4. 上传不支持类型 + 识别命令

通过标准：

- 有正确友好提示
- 有附件下载 steps
- 有 OCR steps
- 有 extraction steps
- 不泄露敏感信息
- 不写正式业务结果
- 不触发 RPA

## 十五、禁止收口条件

出现以下情况，不允许收口：

- P15-A/B/C 回归失败
- P14 回归失败
- 无附件时报 500
- 下载失败时报 500
- 飞书用户看到 traceback
- steps 没有附件留痕
- 泄露 token / 下载 URL
- evidence 或真实文件进入 git
- 写入正式业务结果
- 触发 RPA

## 十六、最终收口回报模板

A. 文档是否齐全  
B. 是否增强 document.ocr_recognize / document.structured_extract  
C. 附件解析是否可用  
D. 文件下载是否可用  
E. evidence 是否可保存且不进 git  
F. 无附件 / 类型不支持 / 文件过大 / 下载失败是否友好处理  
G. OCR / extraction 链路是否能使用下载文件  
H. steps 是否记录附件链路  
I. 是否没有正式写入 / RPA  
J. 是否修改 .env.example  
K. 真实 .env 是否需要人工同步  
L. 测试是否通过  
M. 飞书实机是否通过  
N. 是否允许 P15-D 收口  