# P15-B 老板演示 SOP：真实 OCR Provider 接入

## 一、演示目标

验证系统已经从 P15-A 的 mock OCR 骨架，升级为支持真实 OCR provider 的可插拔架构。

P15-B 的重点不是字段结构化，而是演示：

- OCR provider 可以从 mock 切换到 paddle
- PaddleOCR provider 使用懒加载
- provider 不可用时不会拖垮任务
- 系统能降级到 mock
- OCR 输出仍有 raw_text / blocks / confidence
- task_steps 能追踪 provider 与 fallback
- OCR 结果仍需人工确认
- 不写正式业务记录，不触发 RPA

## 二、演示前提

P15-A 已完成并收口。

P15-B 只做真实 OCR provider 接入。

不做：

- 飞书附件下载
- 发票字段结构化
- 小票字段结构化
- 人工确认
- 写入多维表
- 自动报销
- 自动付款
- RPA

## 三、启动前环境

进入 A 项目：

```bash
cd ~/feishu-rpa-commerce-agent
source venv/bin/activate 2>/dev/null || source .venv/bin/activate
```

## 四、验收场景 1：mock provider 回归

环境变量：

```bash
export USE_SQLITE=true
export ENABLE_OCR_DOCUMENT_RECOGNIZE=true
export OCR_DOCUMENT_PROVIDER=mock
```

启动服务：

```bash
./scripts/dev_run_api.sh
./scripts/dev_run_worker.sh
./scripts/dev_run_feishu_longconn.sh
```

飞书发送：

```text
识别这张发票
```

期望：

- intent=document.ocr_recognize
- provider=mock
- 返回 OCR mock 摘要
- steps 有 ocr_document_started / succeeded
- P15-A 不退化

## 五、验收场景 2：paddle provider 未启用降级

环境变量：

```bash
export ENABLE_OCR_DOCUMENT_RECOGNIZE=true
export OCR_DOCUMENT_PROVIDER=paddle
export OCR_PADDLE_ENABLED=false
```

飞书发送：

```text
识别这张发票
```

期望：

- 不报 500
- 不展示 traceback
- steps 有 ocr_document_fallback_used
- fallback_reason=paddle_disabled
- 最终降级 mock
- result_summary 说明已降级，仍需人工确认

## 六、验收场景 3：paddleocr 未安装降级

环境变量：

```bash
export ENABLE_OCR_DOCUMENT_RECOGNIZE=true
export OCR_DOCUMENT_PROVIDER=paddle
export OCR_PADDLE_ENABLED=true
```

如果本机未安装 paddleocr，飞书发送：

```text
识别这张发票
```

期望：

- 不报 500
- steps 有 ocr_document_fallback_used
- fallback_reason=paddleocr_not_installed
- 最终降级 mock

## 七、验收场景 4：真实 PaddleOCR 可选验收

如果本机已安装 PaddleOCR，并准备了自造 sample 图片：

```bash
export ENABLE_OCR_DOCUMENT_RECOGNIZE=true
export OCR_DOCUMENT_PROVIDER=paddle
export OCR_PADDLE_ENABLED=true
export OCR_SAMPLE_FILE_PATH=tests/fixtures/ocr/sample_invoice.png
```

飞书发送：

```text
识别这张发票
```

期望：

- provider=paddle
- fallback_used=false
- raw_text 来自真实 OCR
- blocks 非空
- confidence 有值
- steps 有 ocr_document_succeeded
- 不写正式业务结果
- 不触发 RPA

## 八、验收查询

查看任务详情：

```bash
curl -s "http://127.0.0.1:8000/api/v1/tasks/{task_id}" | python3 -m json.tool
```

查看任务 steps：

```bash
curl -s "http://127.0.0.1:8000/api/v1/tasks/{task_id}/steps" | python3 -m json.tool
```

## 九、重点检查

重点检查：

- status
- intent=document.ocr_recognize
- provider_requested
- provider_actual
- fallback_used
- fallback_reason
- confidence
- blocks_count
- ocr_document_started
- ocr_document_succeeded
- ocr_document_fallback_used

确认没有出现：

- 飞书附件下载
- 字段结构化
- 写正式业务表
- 写飞书多维表
- 自动报销
- 自动付款
- RPA 执行

## 十、通过标准

P15-B 实机通过标准：

- mock provider 回归可用
- paddle provider routing 可用
- paddle disabled 能降级
- paddleocr 未安装能降级
- 可选真实 PaddleOCR 能跑通一次则更好
- steps 可追踪 provider 和 fallback
- 不写正式业务结果
- 不触发 RPA
- 不破坏 P15-A
- 不破坏 P14