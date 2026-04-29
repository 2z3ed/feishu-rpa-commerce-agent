# P15-E Agent 开发约束：真实 OCR Provider 实机读取闭环

## 一、当前唯一主线

当前唯一主线是：

P15-E：真实 OCR Provider 实机读取闭环

本轮只做真实 OCR Provider 读取真实图片内容。

不要做人工确认。
不要做字段修改。
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
- 注意：P15-D 只打通真实上传入口，OCR 结果仍是 mock

不要回头重做 P15-A/B/C/D。

## 三、必须先读

开始开发前，必须先读：

1. AGENTS.md 当前阶段入口
2. docs/p15/p15e-project-plan.md
3. docs/p15/P15E-agent-prompt.md
4. docs/p15/p15e-boss-demo-sop.md
5. docs/p15/p15e-acceptance-checklist.md
6. P15-A / P15-B / P15-C / P15-D 相关代码和测试
7. PaddleOCR provider 相关代码
8. 飞书文件下载 / evidence 相关代码

如果文件不存在，先创建文档，不要直接写业务代码。

## 四、本轮目标

本轮只做：

真实 OCR Provider 实机读取闭环。

目标链路：

飞书上传真实图片  
→ P15-D 下载并保存 evidence  
→ OCR_DOCUMENT_PROVIDER=paddle  
→ PaddleOCR 读取 evidence 图片  
→ raw_text / blocks / confidence 来自真实图片  
→ 可选进入 P15-C rule extraction  
→ 返回 OCR 摘要或字段摘要  
→ task_steps 留痕  

## 五、本轮允许做

允许做：

- 检查 PaddleOCR 是否已安装
- 在当前 venv 中安装 PaddleOCR 依赖
- 修正 PaddleOCR provider 对真实返回结构的解析
- 增强 PaddleOCR 输出到 OCRDocumentOutput 的映射
- 支持 blocks / confidence / raw_text 聚合
- 支持 evidence 相对路径进入 provider 后可读
- 支持 provider_actual=paddle 的成功留痕
- 支持 provider 失败时 fallback_reason 清晰留痕
- 新增真实 OCR provider 映射测试
- 新增可选真实 PaddleOCR smoke 测试
- 更新 .env.example
- 新增 P15-E 文档

## 六、本轮禁止做

禁止做：

- 不做 P15-F 人工确认与字段修正闭环
- 不做 P15-G 结构化结果写入与归档
- 不做字段人工修正
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
- 不改 B 项目
- 不重构 P14
- 不重构 P15-A/B/C/D
- 不提交真实 .env
- 不提交真实票据 / 客户文件
- 不提交 data/ocr_evidence
- 不提交 PaddleOCR 模型缓存
- 不提交 venv

## 七、PaddleOCR 安装要求

先检查：

```bash
python - <<'PY'
try:
    import paddleocr
    print("paddleocr installed", getattr(paddleocr, "__version__", "unknown"))
except Exception as e:
    print("paddleocr not available:", repr(e))
PY
```

如果没装，可以在当前 venv 中安装。

但必须注意：

- 不提交 venv
- 不提交 PaddleOCR 模型缓存
- 不提交 pip 缓存
- 安装失败要如实回报
- 不能伪造真实 OCR 验收

## 八、环境变量要求

P15-E 实机验收建议：

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

ENABLE_LLM_INTENT_FALLBACK=true  
LLM_INTENT_PROVIDER=mock  

注意：

- 可以修改 .env.example
- 不要修改真实 .env，除非用户明确让你做本地实机配置
- 真实 .env 不许提交
- evidence 不许提交

## 九、样例图片要求

不要使用真实敏感发票。

建议使用自造样例图片，图片里写：

发票号码：987654321  
开票日期：2026-04-29  
购买方：深圳测试科技有限公司  
金额：256.80  

验收关键：

raw_text 必须能证明来自图片，而不是来自 mock。

不能继续只返回：

发票号码：12345678  
开票日期：2026-04-27  
购买方：测试公司  
金额：128.50  

## 十、PaddleOCR provider 要求

PaddleOCR 不同版本返回结构可能不同。

provider 必须尽量兼容：

- 文本行
- 坐标框
- 置信度
- 空结果
- 异常结果

成功输出要求：

- provider=paddle
- provider_actual=paddle
- fallback_used=false
- raw_text 非空
- blocks_count > 0
- confidence 有值

fallback 输出要求：

- provider_actual=mock
- fallback_used=true
- fallback_reason 有值
- 不能悄悄假装真实 OCR 成功

## 十一、真实图片路径要求

P15-D 下载后的 file_path 必须可读。

需要检查：

- 相对路径是否能解析到项目根目录
- 文件是否存在
- 文件是否可读
- 图片格式是否可读

路径问题不能抛 500。

如果路径不存在：

- fallback_reason=file_not_found
- 不暴露 traceback
- 不泄露绝对路径给飞书用户

## 十二、steps 留痕

继续复用：

- feishu_attachment_detected
- feishu_file_download_started
- feishu_file_download_succeeded
- ocr_document_started
- ocr_document_succeeded
- ocr_document_fallback_used
- document_extraction_started
- document_extraction_succeeded

P15-E 必须强化 OCR detail：

- provider_requested=paddle
- provider_actual=paddle
- provider=paddle
- fallback_used=false
- raw_text_length
- blocks_count
- confidence
- image_source=feishu
- evidence_relative_path

fallback 时：

- provider_requested=paddle
- provider_actual=mock
- fallback_used=true
- fallback_reason
- error

禁止写：

- 完整 OCR 原文
- 真实图片绝对路径
- 飞书 token
- 下载 URL
- 大段文件内容
- 真实敏感票据全文

## 十三、测试要求

新增：

tests/test_p15e_real_ocr_provider_integration.py

默认测试不能强依赖真实 PaddleOCR 安装。

至少覆盖：

1. provider=paddle 且 OCR_PADDLE_ENABLED=false 时 fallback mock
2. provider=paddle 但 file_path 不存在时 fallback_reason=file_not_found
3. provider=paddle 成功结果能映射为 OCRDocumentOutput
4. PaddleOCR 返回空结果时友好失败或 fallback
5. raw_text 来自 provider result，不是 mock 固定文本
6. provider_actual=paddle 时 fallback_used=false
7. provider_actual=mock 时 fallback_used=true

可选真实测试：

tests/test_p15e_real_paddle_smoke.py

只在显式设置时执行：

RUN_PADDLE_OCR_REAL_TESTS=true pytest -q tests/test_p15e_real_paddle_smoke.py

## 十四、飞书实机验收要求

### 用例 1：上传自造样例图片 + OCR 识别

飞书同一条消息上传图片并发送：

识别这张发票

预期：

- feishu_file_download_succeeded
- ocr_document_succeeded
- provider_requested=paddle
- provider_actual=paddle
- fallback_used=false
- raw_text 来自图片
- result_summary 不再是固定 mock 文本
- 不写正式业务结果
- 不触发 RPA

### 用例 2：上传自造样例图片 + 字段提取

飞书同一条消息上传图片并发送：

提取这张发票字段

预期：

- provider_actual=paddle
- fallback_used=false
- raw_text 来自图片
- document_extraction_succeeded
- 字段结果来自真实 raw_text
- 不写正式业务结果
- 不触发 RPA

### 用例 3：provider 失败 fallback

临时制造 provider error。

预期：

- ocr_document_fallback_used
- fallback_reason 有值
- 不报 500
- 不暴露 traceback
- provider_actual=mock
- fallback_used=true

## 十五、禁止收口条件

以下任一情况不允许收口：

- 配置为 paddle，但最终 provider_actual=mock 且 fallback_used=true，且没有明确原因
- OCR 返回仍然是固定 mock 文本
- raw_text 与上传图片内容无关
- blocks_count=0
- confidence 缺失
- 真实图片路径无法进入 OCR provider
- PaddleOCR 失败但没有明确 fallback_reason
- 飞书用户看到 traceback
- steps 泄露绝对路径 / token / 下载 URL
- 触发正式写入 / RPA
- P15-A/B/C/D 回归失败
- P14 回归失败

## 十六、完成后回报格式

完成后必须回报：

A. 先读了哪些文件  
B. PaddleOCR 是否已安装，版本是什么  
C. 是否修改 PaddleOCR provider，如何兼容真实返回结构  
D. 真实 evidence 图片如何进入 provider  
E. provider_actual / fallback_used 如何记录  
F. raw_text 如何保证来自真实图片而不是 mock  
G. steps 如何留痕  
H. 是否修改 .env.example  
I. 真实 .env 需要人工同步哪些变量  
J. 改了哪些文件  
K. 执行了哪些测试  
L. 测试结果  
M. 是否可以进入飞书实机验收  

不要编造实机结果。
没有跑飞书就明确说没有跑。