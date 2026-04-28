# P15-B 开发主线文档：真实 OCR Provider 接入

## 一、阶段名称

P15-B：真实 OCR Provider 接入

## 二、当前背景

P15-A 已经完成并收口。

P15-A 已具备：

- document.ocr_recognize intent
- OCR 输入 / 输出 schema
- mock OCR provider
- OCR service 统一入口
- raw_text / document_type / confidence / provider / blocks / needs_manual_review 输出
- ocr_document_* steps 留痕
- unsupported provider 降级 mock
- 飞书 / API mock OCR 验收通过

P15-B 不再做 OCR 骨架，而是在 P15-A 的 provider 抽象基础上，接入真实 OCR provider。

## 三、本轮唯一目标

本轮只做：

真实 OCR Provider 接入。

固定链路：

本地图片 / 测试图片 / sample file path  
→ OCR service  
→ provider routing  
→ PaddleOCR provider  
→ raw_text / blocks / confidence  
→ 统一 OCRDocumentOutput  
→ 返回 OCR 摘要  
→ task_steps 留痕  

## 四、P15-B 定位

P15-B 不是做发票字段结构化。

P15-B 要验证的是：

- 系统可以切换 OCR provider
- mock provider 继续可用
- paddle provider 可以懒加载
- PaddleOCR 未安装时系统不崩
- 真实 OCR provider 可用时能返回 raw_text / blocks / confidence
- provider 失败时能降级 mock
- 后续 P15-C 可以基于真实 raw_text 做字段结构化

## 五、推荐 provider

P15-B 首选：

PaddleOCR

原因：

- 中文识别更适合发票、小票、截图等场景
- 支持本地部署
- 适合简历项目展示
- 可与后续票据结构化、LLM 抽取结合

但本轮不能让普通测试强依赖 PaddleOCR 已安装。

必须采用：

- 懒加载
- 可选真实测试
- provider 不可用时降级
- 默认测试不失败

## 六、本轮允许做

允许做：

- 新增 PaddleOCR provider
- 新增 provider routing
- 新增 PaddleOCR 懒加载逻辑
- 新增 paddle disabled / not installed / provider error 的降级逻辑
- 新增可选 sample image 或测试生成图片
- 新增 provider fallback 测试
- 新增真实 OCR 可选验收说明
- 更新 .env.example
- 更新 P15-B 文档

## 七、本轮禁止做

禁止做：

- 不做 P15-C 字段结构化
- 不接飞书附件下载
- 不做多页 PDF 完整处理
- 不做人工确认与字段修正
- 不写入数据库正式结果
- 不写入飞书多维表
- 不做批量 OCR
- 不做自动报销
- 不做自动付款
- 不做税务合规判断
- 不触发 RPA
- 不改 B 项目
- 不重构 P14-A/B/C/D
- 不破坏 P15-A mock OCR 能力
- 不提交真实 .env
- 不提交真实发票 / 真实客户文件
- 不提交 data/ocr_evidence 临时文件

## 八、provider 配置建议

在 .env.example 中扩展：

```env
# P15-A / P15-B OCR document recognition
ENABLE_OCR_DOCUMENT_RECOGNIZE=false
OCR_DOCUMENT_PROVIDER=mock
OCR_DOCUMENT_TIMEOUT_SECONDS=10
OCR_EVIDENCE_DIR=data/ocr_evidence

# P15-B real OCR provider
OCR_PADDLE_ENABLED=false
OCR_PADDLE_LANG=ch
OCR_PADDLE_USE_GPU=false
OCR_SAMPLE_FILE_PATH=tests/fixtures/ocr/sample_invoice.png
```

要求：

- 默认关闭真实 OCR
- OCR_DOCUMENT_PROVIDER=mock 时仍走 P15-A mock provider
- OCR_DOCUMENT_PROVIDER=paddle 时才尝试真实 OCR
- OCR_PADDLE_ENABLED=true 时才允许加载 PaddleOCR
- 未安装 PaddleOCR 时不能报 500
- 真实 .env 仍由用户人工同步

## 九、PaddleOCR 依赖策略

PaddleOCR 安装较重，因此本轮必须遵守：

1. 不在模块顶层强制 import PaddleOCR
2. paddle provider 内部懒加载 PaddleOCR
3. 没安装 paddleocr 时返回友好错误或 fallback mock
4. 普通 pytest 不因为没装 paddleocr 而失败
5. 真实 PaddleOCR 测试必须是可选测试或手动验收
6. 不把 PaddleOCR 加成强制运行依赖，除非项目已有明确依赖管理策略

建议逻辑：

- OCR_DOCUMENT_PROVIDER=mock → 直接 mock
- OCR_DOCUMENT_PROVIDER=paddle + OCR_PADDLE_ENABLED=false → fallback mock，reason=paddle_disabled
- OCR_DOCUMENT_PROVIDER=paddle + paddleocr 未安装 → fallback mock，reason=paddleocr_not_installed
- OCR_DOCUMENT_PROVIDER=paddle + 文件不存在 → fallback mock 或友好失败，reason=file_not_found
- OCR_DOCUMENT_PROVIDER=paddle + 正常 → provider=paddle，fallback_used=false

## 十、建议新增文件

建议新增：

- app/services/ocr/providers/__init__.py
- app/services/ocr/providers/paddle_provider.py
- tests/test_p15b_ocr_paddle_provider.py

可选新增：

- tests/fixtures/ocr/sample_invoice.png

如果新增 sample 图片，必须是自造样例，不得包含真实敏感信息。

如果不提交图片，可以在测试里动态生成简单图片或只测 provider routing / fallback。

## 十一、需要调整的文件

可能需要调整：

- app/services/ocr/document_ocr.py
- app/core/config.py
- .env.example
- tests/test_p15a_ocr_document_mock.py
- AGENTS.md
- docs/p15/*

如无必要，不改：

- app/graph/nodes/resolve_intent.py
- app/graph/nodes/execute_action.py
- app/tasks/ingress_tasks.py

如果必须修改，需说明原因。

## 十二、OCR 输出要求

P15-B 必须继续返回 OCRDocumentOutput 兼容结构：

```json
{
  "status": "succeeded",
  "document_type": "invoice",
  "raw_text": "...",
  "confidence": 0.88,
  "provider": "paddle",
  "blocks": [
    {
      "text": "发票号码：12345678",
      "confidence": 0.91
    }
  ],
  "needs_manual_review": true,
  "warnings": [
    "当前结果为 OCR 自动识别，需人工确认"
  ],
  "fallback_used": false,
  "error": ""
}
```

说明：

- raw_text 可以是真实 OCR 结果
- blocks 可以是行级文本
- confidence 可以取 OCR block 平均值
- document_type 可先来自 hint_document_type
- needs_manual_review 固定 true
- 不做字段结构化

## 十三、steps 留痕要求

复用 P15-A steps：

- ocr_document_started
- ocr_document_succeeded
- ocr_document_failed
- ocr_document_fallback_used

P15-B 应补充 detail：

- provider_requested
- provider_actual
- provider
- fallback_used
- fallback_reason
- document_type
- mime_type
- confidence
- raw_text_length
- blocks_count
- needs_manual_review
- error

禁止写入：

- API Key
- token
- 密钥
- 完整 OCR 原文
- 真实文件敏感路径
- 大段图片内容
- 用户真实票据内容

## 十四、失败与降级策略

### 场景 1：OCR_DOCUMENT_PROVIDER=paddle，但 PaddleOCR 未安装

预期：

- 不报 500
- steps 有 ocr_document_fallback_used
- result_summary 提示真实 OCR provider 不可用，已降级 mock
- 任务可以 succeeded
- fallback_used=true

### 场景 2：OCR_PADDLE_ENABLED=false

预期：

- 不加载 PaddleOCR
- fallback mock
- fallback_reason=paddle_disabled

### 场景 3：图片路径不存在

预期：

- 不报 500
- 返回友好错误或 fallback mock
- 不泄露敏感路径
- steps 有 failed 或 fallback_used

### 场景 4：PaddleOCR 调用异常

预期：

- 捕获异常
- 不向飞书暴露 traceback
- steps 记录截断后的 error
- 可 fallback mock

## 十五、测试要求

新增测试：

tests/test_p15b_ocr_paddle_provider.py

至少覆盖：

1. OCR_DOCUMENT_PROVIDER=mock 时仍保持 P15-A 行为
2. OCR_DOCUMENT_PROVIDER=paddle 且 OCR_PADDLE_ENABLED=false 时 fallback mock
3. OCR_DOCUMENT_PROVIDER=paddle 且 paddleocr 未安装时 fallback mock
4. OCR_DOCUMENT_PROVIDER=unsupported 仍 fallback mock
5. fallback_used / error / warning 可见
6. 输出仍符合 OCRDocumentOutput
7. 不强制依赖 paddleocr 安装
8. P15-A 回归不退化
9. P14 回归不退化

可选真实 OCR 测试：

- 默认跳过
- 只有 RUN_PADDLE_OCR_TESTS=true 时执行
- 不断言完整 raw_text，只断言 raw_text 非空、blocks 非空、provider=paddle

## 十六、飞书 / API 验收建议

### 验收 1：mock provider 回归

配置：

```env
ENABLE_OCR_DOCUMENT_RECOGNIZE=true
OCR_DOCUMENT_PROVIDER=mock
```

飞书发送：

```text
识别这张发票
```

预期：

- provider=mock
- P15-A 行为不退化

### 验收 2：paddle provider 不可用降级

配置：

```env
ENABLE_OCR_DOCUMENT_RECOGNIZE=true
OCR_DOCUMENT_PROVIDER=paddle
OCR_PADDLE_ENABLED=false
```

或 PaddleOCR 未安装时：

```env
ENABLE_OCR_DOCUMENT_RECOGNIZE=true
OCR_DOCUMENT_PROVIDER=paddle
OCR_PADDLE_ENABLED=true
```

飞书发送：

```text
识别这张发票
```

预期：

- 不报 500
- 有 ocr_document_fallback_used
- result_summary 说明已降级 mock
- 不触发 RPA

### 验收 3：真实 PaddleOCR 可选验收

如果本机安装了 PaddleOCR：

```env
ENABLE_OCR_DOCUMENT_RECOGNIZE=true
OCR_DOCUMENT_PROVIDER=paddle
OCR_PADDLE_ENABLED=true
OCR_SAMPLE_FILE_PATH=tests/fixtures/ocr/sample_invoice.png
```

飞书发送：

```text
识别这张发票
```

预期：

- provider=paddle
- raw_text 来自真实 OCR
- confidence 有值
- blocks 有值
- steps 有 ocr_document_succeeded
- 不写正式业务结果
- 不触发 RPA

## 十七、最低通过标准

P15-B 最低通过标准：

- OCR provider routing 支持 mock / paddle / unsupported
- paddle provider 懒加载
- 默认测试不强依赖 paddleocr
- PaddleOCR 未安装时不报 500
- PaddleOCR 未启用时不报 500
- provider 不可用时能 fallback mock
- 输出仍符合 OCRDocumentOutput
- steps 有 provider / fallback / confidence / blocks 留痕
- P15-A mock OCR 回归不退化
- 不接飞书附件下载
- 不做字段结构化
- 不写正式业务结果
- 不触发 RPA
- P14 回归不退化

## 十八、完成后回报格式

Agent 完成后必须按以下格式回报：

A. 先读了哪些文件  
B. 新增 / 调整了哪些 provider  
C. PaddleOCR provider 如何懒加载  
D. OCR_DOCUMENT_PROVIDER=mock 是否保持 P15-A 行为  
E. OCR_DOCUMENT_PROVIDER=paddle 但 OCR_PADDLE_ENABLED=false 如何处理  
F. paddleocr 未安装时如何处理  
G. 真实 PaddleOCR 可选验收如何跑  
H. steps 如何记录 provider / fallback  
I. 是否修改 .env.example  
J. 真实 .env 需要人工同步哪些变量  
K. 改了哪些文件  
L. 执行了哪些测试  
M. 测试结果  
N. 是否可以进入飞书 / API 验收  