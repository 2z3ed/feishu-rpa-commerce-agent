# P15-A 开发主线文档：OCR 识别骨架与 mock 闭环

## 一、阶段名称

P15-A：OCR 识别骨架与 mock 闭环

## 二、当前背景

P14 已经完成并收口。

P14 解决的是：

- 用户自然语言意图理解
- 监控对象运营总结
- 异常原因解释
- 操作计划生成

P15 开始新增“文件理解能力”。

P15 的目标不是一开始就做完整 OCR 平台，而是让系统逐步具备：

飞书上传文件 / 图片 / 发票  
→ 系统接收文件  
→ OCR 识别文字  
→ 提取结构化字段  
→ 给出置信度和缺失项  
→ 人工确认  
→ 结果归档  

P15-A 是第一步，只做 OCR 骨架与 mock 闭环。

## 三、P15-A 本轮唯一目标

本轮只做：

OCR 识别骨架与 mock 闭环。

固定链路：

用户命令 / 测试入口  
→ A 项目识别 OCR intent  
→ 构造 OCR 输入  
→ 调用 OCR service  
→ mock OCR provider 返回识别结果  
→ 返回 raw_text / document_type / confidence  
→ task_steps 留痕  
→ 飞书或任务结果返回识别摘要  

## 四、P15-A 定位

P15-A 不是做真实 OCR 准确率。

P15-A 要验证的是：

- OCR 能力在系统里如何抽象
- OCR provider 如何可插拔
- OCR 输入输出 schema 是否稳定
- OCR 任务如何接入 execute_action
- OCR 失败如何降级
- OCR 结果如何留痕
- 后续 P15-B 如何替换真实 OCR provider

## 五、本轮允许做

允许做：

- 新增 OCR intent
- 新增 OCR 输入 schema
- 新增 OCR 输出 schema
- 新增 OCR service
- 新增 mock OCR provider
- 新增 execute_action 分支
- 新增 task_steps 留痕
- 新增 .env.example 配置
- 新增测试
- 新增 P15-A 文档

## 六、本轮禁止做

禁止做：

- 不做 P15-B 真实 OCR provider
- 不接 PaddleOCR
- 不接云 OCR
- 不接飞书附件下载
- 不处理真实 PDF 转图片
- 不做发票字段结构化
- 不做小票字段结构化
- 不做人工确认与字段修正
- 不写入数据库正式结果
- 不写入飞书多维表
- 不做批量识别
- 不做自动报销
- 不做自动付款
- 不做税务合规判断
- 不改 B 项目
- 不重构 P14-A/B/C/D
- 不破坏 P14 已收口能力
- 不提交真实 .env
- 不提交 data/evidence 临时文件

## 七、建议新增 intent

建议新增：

document.ocr_recognize

可识别命令示例：

- 识别这张发票
- 帮我读一下这个文件
- 提取这张图片里的文字
- OCR 识别一下
- 帮我识别票据文字

P15-A 可以先支持文本命令触发 mock OCR，不要求真实飞书附件存在。

## 八、OCR 输入 schema 建议

建议新增：

app/schemas/ocr_document.py

建议结构：

```json
{
  "document_id": "mock-doc-001",
  "file_name": "invoice_sample.png",
  "mime_type": "image/png",
  "file_path": "mock://invoice_sample.png",
  "source": "mock",
  "requested_by": "feishu_user",
  "hint_document_type": "invoice"
}
```

字段说明：

- document_id：文档唯一标识，P15-A 可 mock
- file_name：文件名
- mime_type：文件类型
- file_path：文件路径或 mock 路径
- source：来源，例如 mock / feishu / local
- requested_by：请求来源
- hint_document_type：用户提示的类型，例如 invoice / receipt / unknown

## 九、OCR 输出 schema 建议

建议结构：

```json
{
  "document_type": "invoice",
  "raw_text": "发票号码：12345678\n开票日期：2026-04-27\n购买方：测试公司\n金额：128.50",
  "confidence": 0.92,
  "provider": "mock",
  "blocks": [
    {
      "text": "发票号码：12345678",
      "confidence": 0.95
    }
  ],
  "needs_manual_review": true,
  "warnings": [
    "当前结果仅为 OCR 初步识别，需人工确认"
  ]
}
```

字段说明：

- document_type：文档类型，P15-A 可先支持 invoice / receipt / unknown
- raw_text：OCR 原始识别文本
- confidence：整体置信度
- provider：OCR provider 名称
- blocks：文本块，P15-A 可简单返回 mock lines
- needs_manual_review：是否需要人工复核
- warnings：提示信息

## 十、OCR service 设计建议

建议新增：

app/services/ocr/document_ocr.py

核心入口：

run_document_ocr(input)

要求：

- 支持 mock provider
- provider 默认 mock
- provider 异常时可返回 failed 或 fallback_used
- 不抛 500 给飞书用户
- 不读取真实文件内容
- 不依赖真实 OCR 引擎
- 不写正式业务表

## 十一、环境变量建议

建议新增到 .env.example：

ENABLE_OCR_DOCUMENT_RECOGNIZE=false  
OCR_DOCUMENT_PROVIDER=mock  
OCR_DOCUMENT_TIMEOUT_SECONDS=10  
OCR_EVIDENCE_DIR=data/ocr_evidence  

要求：

- 默认关闭
- mock provider 可测试
- 真实 .env 不自动修改
- 如果需要实机启用，必须提示用户人工同步

## 十二、task_steps 留痕

至少新增：

- ocr_document_started
- ocr_document_succeeded
- ocr_document_failed
- ocr_document_fallback_used

detail 可包含：

- provider
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
- 超长 OCR 原文
- 完整敏感文件内容
- 本地真实文件路径中的敏感信息

## 十三、飞书返回文本建议

P15-A 返回老板可读摘要，不直接返回 JSON 原文。

示例：

已完成 OCR 识别。

文档类型：发票  
识别置信度：0.92  
Provider：mock  

识别文本摘要：
发票号码：12345678  
开票日期：2026-04-27  
购买方：测试公司  
金额：128.50  

提醒：当前结果仅为 OCR 初步识别，后续仍需人工确认。

## 十四、开发拆分

### P15-A.0：仓库锚定

先检查：

- resolve_intent 当前 intent 识别方式
- execute_action 当前分支结构
- app/services 目录结构
- app/schemas 目录结构
- task_steps 写法
- .env.example 配置风格
- P14 LLM service 的降级风格
- tests 命名方式

### P15-A.1：schema 与 mock provider

新增：

- OCR 输入 schema
- OCR 输出 schema
- mock OCR provider
- OCR service 统一入口

### P15-A.2：intent 与执行分支

新增：

- document.ocr_recognize
- resolve_intent 规则识别
- execute_action 分支
- 飞书结果摘要

### P15-A.3：steps 留痕

新增：

- ocr_document_started
- ocr_document_succeeded
- ocr_document_failed
- ocr_document_fallback_used

### P15-A.4：测试

新增测试：

tests/test_p15a_ocr_document_mock.py

至少覆盖：

- OCR intent 能识别
- mock OCR 能返回 raw_text
- confidence 能返回
- provider 信息能返回
- OCR 失败能友好处理
- steps 有留痕
- 不写入正式业务结果
- P14-A/B/C/D 回归不受影响

## 十五、最低通过标准

P15-A 通过标准：

- 新增 document.ocr_recognize intent
- 有 OCR 输入 schema
- 有 OCR 输出 schema
- 有 mock OCR provider
- 能返回 raw_text / document_type / confidence / provider
- OCR provider 异常时不报 500
- task_steps 有 ocr_document_* 留痕
- 不自动写入正式业务记录
- 不自动触发 RPA
- 不影响 P14
- 测试通过

## 十六、完成后回报格式

Agent 完成后必须按以下格式回报：

A. 先读了哪些文件  
B. 新增了哪个 OCR intent  
C. OCR 输入 schema 如何设计  
D. OCR 输出 schema 如何设计  
E. OCR service 如何设计  
F. mock provider 返回什么  
G. OCR 失败如何处理  
H. steps 如何留痕  
I. 是否修改 .env.example  
J. 真实 .env 需要人工同步哪些变量  
K. 改了哪些文件  
L. 执行了哪些测试  
M. 测试结果  
N. 是否可以进入飞书 / API 验收  