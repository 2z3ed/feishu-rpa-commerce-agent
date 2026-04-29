# P15-E 开发主线文档：真实 OCR Provider 实机读取闭环

## 一、阶段名称

P15-E：真实 OCR Provider 实机读取闭环

## 二、当前背景

P15-A 已完成 OCR mock 骨架。

P15-B 已完成 OCR provider routing，并加入 PaddleOCR provider 懒加载与 fallback 能力。

P15-C 已完成 OCR raw_text 到票据结构化字段的规则提取。

P15-D 已完成飞书真实文件入口接入，真实图片已经可以：

飞书上传  
→ parser 接收  
→ payload 保留 image_key / file_key  
→ resolver 解析附件  
→ downloader 下载  
→ evidence 保存  
→ 进入 OCR / structured extraction 链路  

但 P15-D 验收时 OCR 仍为：

OCR_DOCUMENT_PROVIDER=mock  
OCR_PADDLE_ENABLED=false  

所以 P15-D 打通的是“真实上传入口”，不是“真实 OCR 识别结果”。

P15-E 要补齐真实 OCR 读取：

飞书真实图片  
→ evidence 图片  
→ PaddleOCR  
→ raw_text 来自图片本身  
→ 再进入结构化提取  

## 三、本轮唯一目标

本轮只做：

真实 OCR Provider 实机读取闭环。

固定链路：

飞书上传图片  
→ P15-D 下载并保存 evidence  
→ OCR_DOCUMENT_PROVIDER=paddle  
→ OCR_PADDLE_ENABLED=true  
→ PaddleOCR 真实读取本地图片  
→ 返回真实 raw_text / blocks / confidence  
→ 可选进入 P15-C rule extraction  
→ 飞书返回 OCR 摘要或字段摘要  
→ /tasks 和 /steps 可查  

## 四、P15-E 定位

P15-E 不是做人工确认。

P15-E 不是做字段修改。

P15-E 不是写表。

P15-E 要验证的是：

- 真实上传图片能被 PaddleOCR 读取
- provider_actual=paddle
- fallback_used=false
- raw_text 不再是固定 mock 文本
- blocks_count > 0
- confidence 有值
- structured extraction 可以基于真实 raw_text 执行
- OCR 失败时 fallback_reason 清晰可查

## 五、P15-E 与 P15-B 的区别

P15-B 做的是 provider routing：

- mock / paddle / unsupported
- PaddleOCR 懒加载
- paddle disabled fallback
- paddleocr not installed fallback
- provider 不可用不崩溃

P15-B 没有强制证明：

飞书真实上传图片  
→ PaddleOCR 真实读取图片内容  

P15-E 要证明：

现在真的能读真实图片内容。

## 六、本轮允许做

允许做：

- 检查 PaddleOCR 是否已安装
- 在当前 venv 中安装 PaddleOCR 依赖
- 修正 paddle provider 对真实 OCR 返回结构的解析
- 增强 PaddleOCR 输出到 OCRDocumentOutput 的映射
- 支持 blocks / confidence / raw_text 聚合
- 支持 evidence 相对路径进入 provider 后可读
- 支持 provider_actual=paddle 的成功留痕
- 支持 provider 失败时 fallback_reason 清晰留痕
- 新增真实 OCR provider 映射测试
- 新增可选真实 PaddleOCR smoke 测试
- 更新 .env.example
- 新增 P15-E 文档

## 七、本轮禁止做

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
- 不提交真实发票 / 客户文件
- 不提交 data/ocr_evidence
- 不提交 PaddleOCR 模型缓存
- 不提交 venv

## 八、环境变量建议

P15-E 实机验收建议：

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

ENABLE_LLM_INTENT_FALLBACK=true
LLM_INTENT_PROVIDER=mock
```

要求：

- 真实 .env 由用户人工同步
- .env 不允许提交
- evidence 不允许提交
- PaddleOCR 模型缓存不允许提交

## 九、PaddleOCR 安装策略

PaddleOCR 是开发/验收环境能力，不是业务逻辑。

Agent 允许做：

- 检查 paddleocr 是否安装
- 输出安装建议
- 在当前 venv 中安装依赖
- 记录版本
- 记录安装结果

检查命令：

```bash
python - <<'PY'
try:
    import paddleocr
    print("paddleocr installed", getattr(paddleocr, "__version__", "unknown"))
except Exception as e:
    print("paddleocr not available:", repr(e))
PY
```

如果未安装，可以在当前 venv 中安装，但必须注意：

- 不提交 venv
- 不提交模型缓存
- 不提交 pip 缓存
- 不把安装动作当成业务代码改动
- 安装失败要如实回报，不允许伪造真实 OCR 验收

## 十、样例图片策略

P15-E 不使用真实敏感发票。

建议使用自造样例图片。

图片内容建议：

```text
发票号码：987654321
开票日期：2026-04-29
购买方：深圳测试科技有限公司
金额：256.80
```

验收重点：

OCR raw_text 是否包含部分新内容，例如：

- 987654321
- 2026-04-29
- 深圳测试科技有限公司
- 256.80

只要能读出部分关键字段，就证明真实 OCR 链路打通。

不能继续只返回 P15-A mock 文本：

```text
发票号码：12345678
开票日期：2026-04-27
购买方：测试公司
金额：128.50
```

## 十一、PaddleOCR provider 增强要求

PaddleOCR 不同版本返回结构可能不同。

provider 需要兼容常见返回：

- 文本行
- 坐标框
- 置信度
- 空结果
- 异常结果

输出统一为 OCRDocumentOutput：

```json
{
  "provider": "paddle",
  "raw_text": "...",
  "blocks": [
    {
      "text": "...",
      "confidence": 0.91
    }
  ],
  "confidence": 0.88,
  "fallback_used": false
}
```

要求：

- raw_text 由 blocks 拼接
- blocks_count > 0
- confidence 可取平均置信度
- 空结果不能假装成功
- 成功时 provider_actual=paddle
- 成功时 fallback_used=false
- fallback 时 provider_actual=mock，fallback_used=true，fallback_reason 有值

## 十二、真实图片路径要求

P15-D 下载后的 file_path 必须能被 provider 读取。

需要检查：

- file_path 是相对路径还是绝对路径
- 相对路径是否基于项目根目录解析
- 文件是否存在
- 文件是否可读
- 图片格式是否可读
- path 相关错误不能泄露敏感绝对路径给飞书用户

如果路径不存在：

- 不报 500
- ocr_document_fallback_used 或 ocr_document_failed
- fallback_reason=file_not_found
- 不暴露 traceback

## 十三、steps 留痕要求

继续复用：

- feishu_attachment_detected
- feishu_file_download_started
- feishu_file_download_succeeded
- ocr_document_started
- ocr_document_succeeded
- ocr_document_fallback_used
- document_extraction_started
- document_extraction_succeeded

P15-E 强化 OCR detail：

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

禁止写入：

- 完整 OCR 原文
- 真实图片绝对路径
- 飞书 token
- 下载 URL
- 大段文件内容
- 真实敏感票据全文

## 十四、飞书返回文案建议

### OCR 识别成功

用户上传图片并发送：

识别这张发票

返回示例：

已完成 OCR 识别。

文档类型：invoice  
识别置信度：0.87  
Provider：paddle  

识别文本摘要：
发票号码：987654321
开票日期：2026-04-29
购买方：深圳测试科技有限公司
金额：256.80

提醒：当前结果来自真实 OCR 自动识别，仍需人工确认。

### 结构化提取成功

用户上传图片并发送：

提取这张发票字段

返回示例：

已完成票据字段提取。

文档类型：发票  
整体置信度：0.82  
是否需要人工复核：是  

已提取字段：
- 发票号码：987654321
- 开票日期：2026-04-29
- 购买方：深圳测试科技有限公司
- 金额：256.80

缺失字段：
- 销售方
- 发票代码

提醒：
当前结果来自真实 OCR 识别与规则抽取，仅供初步整理。正式使用前请人工确认。

## 十五、测试要求

新增：

tests/test_p15e_real_ocr_provider_integration.py

默认测试不强依赖 PaddleOCR 安装。

默认测试至少覆盖：

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

```bash
RUN_PADDLE_OCR_REAL_TESTS=true pytest -q tests/test_p15e_real_paddle_smoke.py
```

可选真实测试要求：

- 输入自造样例图片
- provider=paddle
- fallback_used=false
- raw_text 非空
- blocks_count > 0
- raw_text 包含部分样例文字

## 十六、飞书实机验收建议

### 用例 1：上传自造样例图片 + OCR 识别

配置：

```env
OCR_DOCUMENT_PROVIDER=paddle
OCR_PADDLE_ENABLED=true
```

飞书同一条消息上传图片并发送：

```text
识别这张发票
```

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

```text
提取这张发票字段
```

预期：

- provider_actual=paddle
- fallback_used=false
- raw_text 来自图片
- document_extraction_succeeded
- 字段结果来自真实 raw_text
- 不写正式业务结果
- 不触发 RPA

### 用例 3：provider 失败 fallback

可临时制造 provider error。

预期：

- ocr_document_fallback_used
- fallback_reason 有值
- 不报 500
- 不暴露 traceback
- provider_actual=mock
- fallback_used=true

## 十七、最低通过标准

P15-E 最低通过标准：

- PaddleOCR 在当前 venv 可用，或安装完成并记录版本
- OCR_DOCUMENT_PROVIDER=paddle 时进入真实 PaddleOCR provider
- 飞书下载的 evidence 图片能被真实 OCR provider 读取
- OCR 成功时 provider_actual=paddle
- OCR 成功时 fallback_used=false
- raw_text 不再是 P15-A 固定 mock 文本
- raw_text 能包含上传样例图片里的部分关键文本
- blocks_count > 0
- confidence 有值
- document.structured_extract 能基于真实 OCR raw_text 执行
- task_steps 可追踪 provider=paddle
- provider 失败时 fallback 可控
- 不写正式业务结果
- 不触发 RPA
- P15-A/B/C/D 回归不退化
- P14 回归不退化

## 十八、禁止收口条件

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

## 十九、完成后回报格式

Agent 完成后必须按以下格式回报：

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