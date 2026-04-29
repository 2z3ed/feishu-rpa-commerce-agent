# P15-E 老板演示 SOP：真实 OCR Provider 实机读取闭环

## 一、演示目标

验证系统已经从“飞书真实上传 + mock OCR”升级为“飞书真实上传 + PaddleOCR 真实读取图片内容”。

P15-E 要演示：

- 飞书上传图片
- 系统下载图片并保存 evidence
- PaddleOCR 读取 evidence 图片
- raw_text 来自图片本身
- provider_actual=paddle
- fallback_used=false
- 可进入结构化提取
- 不写正式业务结果
- 不触发 RPA

## 二、演示前提

P15-A 已完成并收口。  
P15-B 已完成并收口。  
P15-C 已完成并收口。  
P15-D 已完成并提交。  

P15-E 只做真实 OCR 读取闭环。

不做：

- 人工确认
- 字段修正
- 写入多维表
- 自动报销
- 自动付款
- 发票真伪校验
- RPA
- 多文件批量
- PDF 多页 OCR

## 三、准备自造样例图片

不要使用真实敏感发票。

建议图片上写：

```text
发票号码：987654321
开票日期：2026-04-29
购买方：深圳测试科技有限公司
金额：256.80
```

验收时重点看 OCR 是否识别到这些新内容。

如果返回仍然是：

```text
发票号码：12345678
开票日期：2026-04-27
购买方：测试公司
金额：128.50
```

说明仍然走的是 mock，不算通过 P15-E。

## 四、检查 PaddleOCR

进入项目：

```bash
cd ~/feishu-rpa-commerce-agent
source venv/bin/activate 2>/dev/null || source .venv/bin/activate
```

检查：

```bash
python - <<'PY'
try:
    import paddleocr
    print("paddleocr installed", getattr(paddleocr, "__version__", "unknown"))
except Exception as e:
    print("paddleocr not available:", repr(e))
PY
```

如果未安装，需要先在当前 venv 中安装。

安装过程不要提交 venv / 模型缓存 / pip 缓存。

## 五、启动环境变量

P15-E 实机验收建议：

```bash
export USE_SQLITE=true

export ENABLE_FEISHU_FILE_DOWNLOAD=true
export FEISHU_FILE_EVIDENCE_DIR=data/ocr_evidence
export FEISHU_FILE_MAX_SIZE_MB=10
export FEISHU_FILE_ALLOWED_MIME_TYPES="image/png,image/jpeg"

export ENABLE_OCR_DOCUMENT_RECOGNIZE=true
export OCR_DOCUMENT_PROVIDER=paddle
export OCR_PADDLE_ENABLED=true
export OCR_PADDLE_LANG=ch
export OCR_PADDLE_USE_GPU=false

export ENABLE_DOCUMENT_STRUCTURED_EXTRACTION=true
export DOCUMENT_EXTRACTION_PROVIDER=rule
export DOCUMENT_EXTRACTION_TIMEOUT_SECONDS=10

export ENABLE_LLM_INTENT_FALLBACK=true
export LLM_INTENT_PROVIDER=mock
```

如果 Redis 需要显式配置：

```bash
export REDIS_HOST=127.0.0.1
export REDIS_PORT=6379
export REDIS_DB=0
export CELERY_BROKER_URL=redis://127.0.0.1:6379/0
export CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0
```

## 六、启动服务

启动 API：

```bash
./scripts/dev_run_api.sh
```

启动 worker。

如果默认 Celery prefork 有 SemLock 权限问题，可以用开发验收模式：

```bash
celery -A app.workers.celery_app worker --loglevel=info --pool=solo --concurrency=1
```

启动 longconn：

```bash
./scripts/dev_run_feishu_longconn.sh
```

## 七、健康检查

```bash
curl -s http://127.0.0.1:8000/api/v1/health | python3 -m json.tool
```

要求：

- database connected
- redis connected

worker 日志应显示：

- connected to redis
- ready

longconn 日志应显示：

- connected to Feishu websocket
- ping / pong 正常

## 八、用例 1：上传图片 + OCR 识别

飞书同一条消息上传自造样例图片并发送：

```text
识别这张发票
```

预期：

- intent=document.ocr_recognize
- feishu_file_download_succeeded
- ocr_document_succeeded
- provider_requested=paddle
- provider_actual=paddle
- provider=paddle
- fallback_used=false
- raw_text 来自图片
- result_summary 不再是固定 mock 文本
- blocks_count > 0
- confidence 有值
- 不写正式业务结果
- 不触发 RPA

## 九、用例 2：上传图片 + 字段提取

飞书同一条消息上传自造样例图片并发送：

```text
提取这张发票字段
```

预期：

- intent=document.structured_extract
- feishu_file_download_succeeded
- ocr_document_succeeded
- provider_actual=paddle
- fallback_used=false
- document_extraction_succeeded
- 字段结果来自真实 raw_text
- 可允许部分字段缺失
- needs_manual_review=true
- 不写正式业务结果
- 不触发 RPA

## 十、用例 3：provider 失败 fallback

可以临时设置错误 provider 参数或模拟图片读取失败。

预期：

- ocr_document_fallback_used
- provider_requested=paddle
- provider_actual=mock
- fallback_used=true
- fallback_reason 有值
- 不报 500
- 不暴露 traceback

## 十一、验收查询

查看任务详情：

```bash
curl -s "http://127.0.0.1:8000/api/v1/tasks/{task_id}" | python3 -m json.tool
```

查看任务 steps：

```bash
curl -s "http://127.0.0.1:8000/api/v1/tasks/{task_id}/steps" | python3 -m json.tool
```

## 十二、重点检查

重点检查：

- provider_requested
- provider_actual
- provider
- fallback_used
- fallback_reason
- raw_text_length
- blocks_count
- confidence
- evidence_relative_path
- ocr_document_succeeded
- document_extraction_succeeded

确认没有出现：

- 固定 mock OCR 文本
- token 泄露
- 下载 URL 泄露
- 完整绝对路径暴露
- 完整 OCR 原文写入 steps
- 字段人工修正
- 写数据库正式结果
- 写飞书多维表
- 自动报销
- 自动付款
- 发票真伪判断
- RPA 执行

## 十三、evidence 与 git 检查

执行：

```bash
find data/ocr_evidence -maxdepth 3 -type f | head -n 20
git status --short
```

确认：

- evidence 文件已保存
- evidence 文件没有进入 git
- 真实图片没有进入 git
- 模型缓存没有进入 git
- venv 没有进入 git

## 十四、通过标准

P15-E 实机通过标准：

- PaddleOCR 在当前 venv 可用
- 飞书上传图片能进入 PaddleOCR
- provider_actual=paddle
- fallback_used=false
- raw_text 来自图片本身
- result_summary 不再是 P15-A mock 固定文本
- blocks_count > 0
- confidence 有值
- structured extraction 能基于真实 OCR raw_text 执行
- 不写正式业务结果
- 不触发 RPA
- 不破坏 P15-A/B/C/D
- 不破坏 P14