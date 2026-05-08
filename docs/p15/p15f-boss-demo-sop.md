# P15-F 老板演示 SOP：真实 OCR 结果下的票据字段抽取增强

## 一、演示目标

验证系统已经从“真实 OCR 能读图”升级为“真实 OCR 文本里的发票字段能更稳定抽取”。

P15-F 要演示：

- 飞书上传真实发票图片
- PaddleOCR 真实读取图片内容
- 字段抽取基于真实 raw_text
- 发票号码、开票日期、购买方、金额等字段更稳定
- 金额候选不确定时能提示人工复核
- 缺失字段有缺失原因
- 不写正式业务结果
- 不触发 RPA

## 二、演示前提

P15-A 已完成并收口。  
P15-B 已完成并收口。  
P15-C 已完成并收口。  
P15-D 已完成并提交。  
P15-E 已完成并收口。  

P15-F 只做真实 OCR 文本下的字段抽取增强。

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

## 三、启动前环境

进入项目：

```bash
cd ~/feishu-rpa-commerce-agent
source venv/bin/activate 2>/dev/null || source .venv/bin/activate
```

建议环境变量：

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

## 四、启动服务

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

## 五、健康检查

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

## 六、用例 1：上传图片 + 字段提取

飞书同一条消息上传真实 OCR 可识别的样例发票图片，并发送：

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
- result_summary 是老板可读字段摘要
- 不输出 JSON 原文
- 不写正式业务结果
- 不触发 RPA

## 七、重点字段检查

重点检查 result_summary：

- 发票号码是否提取
- 开票日期是否提取并归一化为 YYYY-MM-DD
- 购买方是否提取或有缺失原因
- 销售方是否提取或有缺失原因
- 价税合计 / 金额是否不再明显误提取
- 币种是否为 CNY
- 缺失字段是否有说明
- 不确定字段是否 needs_review=true

## 八、验收查询

查看任务详情：

```bash
curl -s "http://127.0.0.1:8000/api/v1/tasks/{task_id}" | python3 -m json.tool
```

查看任务 steps：

```bash
curl -s "http://127.0.0.1:8000/api/v1/tasks/{task_id}/steps" | python3 -m json.tool
```

## 九、steps 检查

必须看到：

- feishu_file_download_succeeded
- ocr_document_succeeded
- document_extraction_started
- document_extraction_succeeded

detail 建议包含：

- extractor=rule_v2
- extraction_profile=cn_vat_invoice
- fields_count
- missing_fields_count
- amount_candidates_count
- overall_confidence
- needs_manual_review

## 十、失败也可接受的情况

P15-F 不是要求字段 100% 准确。

以下情况可以接受：

- 复杂字段缺失
- 销售方缺失
- 税额缺失
- needs_manual_review=true

但必须满足：

- 缺失字段有 missing_reasons
- 不确定字段不高置信度输出
- 金额明显不确定时有 warning
- 任务不直接 failed
- 不报 500

## 十一、不能接受的情况

以下情况不能通过：

- 真实 OCR raw_text 仍然只按 mock 风格提取
- 金额明显误提取但没有 needs_review
- invoice_date 明显存在但提取不到，且没有原因
- buyer_name 明显存在但提取不到，且没有原因
- 字段缺失直接 failed
- 输出 JSON 原文给飞书用户
- steps 写入完整 OCR 原文
- 触发正式写入 / RPA

## 十二、evidence 与 git 检查

执行：

```bash
find data/ocr_evidence -maxdepth 3 -type f | head -n 20
git status --short
```

确认：

- evidence 文件没有进入 git
- 真实图片没有进入 git
- 模型缓存没有进入 git
- venv 没有进入 git

## 十三、通过标准

P15-F 实机通过标准：

- 基于真实 PaddleOCR raw_text 做字段提取
- document_extraction_succeeded
- 发票号码提取稳定
- 开票日期提取增强
- 金额候选评分可用
- 购买方 / 销售方至少有增强识别逻辑
- missing_fields / missing_reasons 可用
- 字段 confidence / needs_review 可用
- result_summary 是老板可读字段摘要
- 不写正式业务结果
- 不触发 RPA
- 不破坏 P15-C/D/E
- 不破坏 P14