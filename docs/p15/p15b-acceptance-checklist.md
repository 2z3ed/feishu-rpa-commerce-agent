# P15-B 验收清单：真实 OCR Provider 接入

## 一、阶段信息

阶段：

P15-B：真实 OCR Provider 接入

验收目标：

在 P15-A OCR mock 骨架上，新增真实 OCR provider 可插拔能力，优先支持 PaddleOCR provider，并保证 provider 不可用时可降级。

## 二、文档验收

必须存在：

- AGENTS.md 当前阶段入口
- docs/p15/p15b-project-plan.md
- docs/p15/P15B-agent-prompt.md
- docs/p15/p15b-boss-demo-sop.md
- docs/p15/p15b-acceptance-checklist.md

检查命令：

```bash
ls -la docs/p15
```

## 三、配置验收

建议支持：

```env
OCR_DOCUMENT_PROVIDER=mock
OCR_DOCUMENT_PROVIDER=paddle
OCR_PADDLE_ENABLED=false
OCR_PADDLE_LANG=ch
OCR_PADDLE_USE_GPU=false
OCR_SAMPLE_FILE_PATH=tests/fixtures/ocr/sample_invoice.png
```

通过标准：

- 默认不强制启用 paddle
- PaddleOCR 未安装时普通测试不失败
- .env.example 更新
- 真实 .env 需要人工同步时必须明确提示

## 四、provider routing 验收

必须支持：

- mock
- paddle
- unsupported

通过标准：

- mock 保持 P15-A 行为
- paddle 会进入 paddle provider routing
- unsupported 仍能 fallback mock

## 五、懒加载验收

通过标准：

- paddleocr 不在模块顶层强制 import
- 未安装 paddleocr 时不影响服务启动
- 未安装 paddleocr 时普通 pytest 不失败
- ImportError 被捕获并转为 fallback

## 六、paddle disabled 验收

场景：

```env
OCR_DOCUMENT_PROVIDER=paddle
OCR_PADDLE_ENABLED=false
```

通过标准：

- 不加载 PaddleOCR
- fallback mock
- fallback_reason=paddle_disabled
- 不报 500

## 七、paddleocr 未安装验收

场景：

```env
OCR_DOCUMENT_PROVIDER=paddle
OCR_PADDLE_ENABLED=true
```

如果未安装 paddleocr：

通过标准：

- 不报 500
- fallback mock
- fallback_reason=paddleocr_not_installed
- 不展示 traceback

## 八、真实 PaddleOCR 可选验收

如果环境安装了 paddleocr：

通过标准：

- provider=paddle
- fallback_used=false
- raw_text 非空
- blocks 非空
- confidence 有值
- 不写正式业务结果
- 不触发 RPA

该验收可选，不应阻塞最低验收，除非用户明确要求必须真实 OCR 跑通。

## 九、输出验收

OCR 输出必须兼容 OCRDocumentOutput：

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

通过标准：

- fallback 时 warnings 说明原因
- 不输出 JSON 原文给飞书用户
- 不把 OCR 结果当最终业务事实

## 十、steps 留痕验收

至少能看到：

- ocr_document_started
- ocr_document_succeeded
- ocr_document_failed
- ocr_document_fallback_used

detail 不得包含：

- API Key
- token
- 密钥
- 完整 OCR 原文
- 真实敏感文件路径
- 大段文件内容

## 十一、禁止动作验收

P15-B 不能触发：

- 飞书附件下载
- 字段结构化
- 写正式业务表
- 写飞书多维表
- 自动报销
- 自动付款
- 自动改价
- 自动 RPA

## 十二、测试验收

建议执行：

```bash
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
- 是否与 P15-B 有关

## 十三、飞书 / API 验收

至少测试：

1. mock provider 回归
2. paddle disabled 降级
3. paddleocr 未安装降级
4. 真实 PaddleOCR 可选验收

通过标准：

- provider routing 正确
- fallback 行为正确
- 不报 500
- 不泄露 traceback
- steps 可查
- 不写正式结果
- 不触发 RPA

## 十四、禁止收口条件

出现以下情况，不允许收口：

- P15-A 回归失败
- P14 回归失败
- 普通 pytest 因为没装 paddleocr 失败
- OCR provider 不可用时报 500
- 飞书用户看到 traceback
- steps 没有 provider / fallback 留痕
- 提交了真实 .env
- 提交了真实发票 / 客户文件
- 提交了 data/ocr_evidence 文件
- 触发了字段结构化或正式写入
- 触发了 RPA

## 十五、最终收口回报模板

A. 文档是否齐全  
B. provider routing 是否支持 mock / paddle / unsupported  
C. PaddleOCR 是否懒加载  
D. paddle disabled 是否可降级  
E. paddleocr 未安装是否可降级  
F. mock provider 是否不退化  
G. steps 是否记录 provider / fallback  
H. 是否没有字段结构化 / 正式写入 / RPA  
I. 是否修改 .env.example  
J. 真实 .env 是否需要人工同步  
K. 测试是否通过  
L. 飞书 / API 验收是否通过  
M. 是否允许 P15-B 收口  