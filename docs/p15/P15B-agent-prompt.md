# P15-B Agent 开发约束：真实 OCR Provider 接入

## 一、当前唯一主线

当前唯一主线是：

P15-B：真实 OCR Provider 接入

本轮只做真实 OCR provider 接入能力，不做字段结构化、不接飞书附件下载。

## 二、当前已完成基础

P14 已完成并总收口：

- P14-A：LLM 意图解析 fallback
- P14-B：LLM 监控对象运营总结
- P14-C：LLM 异常原因解释
- P14-D：LLM 操作计划生成
- P14-Z：P14 总收口文档

P15-A 已完成并收口：

- document.ocr_recognize intent
- OCR 输入 / 输出 schema
- mock OCR provider
- OCR service 统一入口
- raw_text / confidence / blocks / needs_manual_review 输出
- ocr_document_* steps 留痕
- unsupported provider 降级 mock
- 飞书 / API mock OCR 验收通过

不要回头重做 P15-A。

## 三、必须先读

开始开发前，必须先读：

1. AGENTS.md 当前阶段入口
2. docs/p15/p15b-project-plan.md
3. docs/p15/P15B-agent-prompt.md
4. docs/p15/p15b-boss-demo-sop.md
5. docs/p15/p15b-acceptance-checklist.md
6. P15-A 相关代码和测试

如果文件不存在，先创建文档，不要直接写业务代码。

## 四、本轮目标

本轮只做：

真实 OCR provider 接入。

目标链路：

OCR service  
→ provider routing  
→ mock / paddle / unsupported  
→ paddle provider 懒加载  
→ 输出统一 OCRDocumentOutput  
→ provider 异常时 fallback mock  
→ task_steps 留痕  

## 五、本轮允许做

允许做：

- 新增 PaddleOCR provider
- 新增 OCR provider routing
- 新增 paddle 懒加载
- 新增 paddle disabled 降级
- 新增 paddleocr_not_installed 降级
- 新增 provider_error 降级
- 新增 provider / fallback steps detail
- 新增 P15-B 测试
- 更新 .env.example
- 新增 P15-B 文档

## 六、本轮禁止做

禁止做：

- 不做 P15-C 字段结构化
- 不接飞书附件下载
- 不做真实 PDF 转图片
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
- 不破坏 P15-A mock provider
- 不提交真实 .env
- 不提交真实发票 / 客户文件
- 不提交 data/ocr_evidence 临时文件

## 七、核心规则

1. 真实 OCR provider 必须可插拔
2. PaddleOCR 必须懒加载
3. 普通 pytest 不能强依赖 paddleocr 已安装
4. OCR provider 不可用时不能报 500
5. OCR 结果不是最终业务事实
6. OCR 结果必须提示人工确认
7. 不做字段结构化
8. 不写正式结果
9. 不触发 RPA
10. steps 中不能写完整 OCR 原文或真实敏感路径

## 八、provider routing 要求

必须支持：

- OCR_DOCUMENT_PROVIDER=mock
- OCR_DOCUMENT_PROVIDER=paddle
- OCR_DOCUMENT_PROVIDER=unsupported

行为要求：

### mock

保持 P15-A 行为不变。

### paddle

如果 OCR_PADDLE_ENABLED=true 且 paddleocr 可用，尝试真实 OCR。

如果不可用，fallback mock。

### unsupported

继续 fallback mock，用于降级测试。

## 九、PaddleOCR 懒加载要求

禁止：

```python
from paddleocr import PaddleOCR
```

出现在模块顶层并导致 import 阶段失败。

必须在函数内部或 provider 初始化时懒加载。

如果 ImportError：

- fallback_used=true
- fallback_reason=paddleocr_not_installed
- 不报 500
- 不向飞书暴露 traceback

## 十、环境变量

建议新增 / 扩展：

ENABLE_OCR_DOCUMENT_RECOGNIZE=false  
OCR_DOCUMENT_PROVIDER=mock  
OCR_DOCUMENT_TIMEOUT_SECONDS=10  
OCR_EVIDENCE_DIR=data/ocr_evidence  

OCR_PADDLE_ENABLED=false  
OCR_PADDLE_LANG=ch  
OCR_PADDLE_USE_GPU=false  
OCR_SAMPLE_FILE_PATH=tests/fixtures/ocr/sample_invoice.png  

注意：

- 可以修改 .env.example
- 不要修改真实 .env
- 如需实机启用，必须回报真实 .env 需要人工同步哪些变量

## 十一、输出要求

输出必须兼容 OCRDocumentOutput：

- status
- document_type
- raw_text
- confidence
- provider
- blocks
- needs_manual_review
- warnings
- fallback_used
- error

如果 provider=paddle 成功：

- provider=paddle
- fallback_used=false
- raw_text 来自真实 OCR
- blocks 来自 OCR lines
- confidence 为平均置信度或合理兜底

如果 fallback mock：

- provider=mock
- fallback_used=true
- warnings 说明已降级
- error 记录简短原因

## 十二、steps 留痕

复用：

- ocr_document_started
- ocr_document_succeeded
- ocr_document_failed
- ocr_document_fallback_used

detail 可包含：

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
- 真实敏感文件路径
- 大段文件内容

## 十三、测试要求

新增：

tests/test_p15b_ocr_paddle_provider.py

至少覆盖：

1. provider=mock 保持 P15-A 行为
2. provider=paddle 但 OCR_PADDLE_ENABLED=false → fallback mock
3. provider=paddle 但 paddleocr 未安装 → fallback mock
4. provider=unsupported → fallback mock
5. fallback_used / error / warning 可见
6. 输出仍符合 OCRDocumentOutput
7. 默认测试不需要安装 paddleocr
8. P15-A 测试不回归
9. P14 测试不回归

可选真实 OCR 测试：

- 默认跳过
- 仅 RUN_PADDLE_OCR_TESTS=true 时执行
- 不断言完整 raw_text

## 十四、完成后回报格式

完成后必须回报：

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

不要编造实机结果。
没有跑飞书就明确说没有跑。