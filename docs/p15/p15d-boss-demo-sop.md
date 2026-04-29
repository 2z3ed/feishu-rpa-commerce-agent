# P15-D 老板演示 SOP：飞书文件入口接入

## 一、演示目标

验证系统已经从“命令触发 mock OCR”升级为“飞书真实文件入口”。

P15-D 要演示：

- 用户可以在飞书上传图片或文件
- 系统可以识别附件
- 系统可以下载附件
- 系统可以保存 evidence
- 系统可以把文件交给 OCR 链路
- 系统可以继续走结构化提取链路
- 系统不会写正式业务结果
- 系统不会触发 RPA

## 二、演示前提

P15-A 已完成并收口。  
P15-B 已完成并收口。  
P15-C 已完成并收口。  

P15-D 只做飞书文件入口接入。

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

进入 A 项目：

```bash
cd ~/feishu-rpa-commerce-agent
source venv/bin/activate 2>/dev/null || source .venv/bin/activate
```

建议环境变量：

```bash
export USE_SQLITE=true
export ENABLE_OCR_DOCUMENT_RECOGNIZE=true
export OCR_DOCUMENT_PROVIDER=mock
export ENABLE_DOCUMENT_STRUCTURED_EXTRACTION=true
export DOCUMENT_EXTRACTION_PROVIDER=rule
export ENABLE_FEISHU_FILE_DOWNLOAD=true
export FEISHU_FILE_EVIDENCE_DIR=data/ocr_evidence
export FEISHU_FILE_MAX_SIZE_MB=10
export FEISHU_FILE_ALLOWED_MIME_TYPES=image/png,image/jpeg,application/pdf
```

如果结构化命令依赖 P14-A fallback，也需要：

```bash
export ENABLE_LLM_INTENT_FALLBACK=true
export LLM_INTENT_PROVIDER=mock
```

注意：

agent 不应擅自修改真实 .env。  
如果需要持久化环境变量，由用户人工同步。  
data/ocr_evidence 不允许提交 git。

## 四、启动服务

启动 API：

```bash
./scripts/dev_run_api.sh
```

另开终端启动 worker：

```bash
./scripts/dev_run_worker.sh
```

另开终端启动飞书长连接：

```bash
./scripts/dev_run_feishu_longconn.sh
```

如果脚本名称和仓库不一致，以仓库实际脚本为准。

## 五、健康检查

```bash
curl -s http://127.0.0.1:8000/api/v1/health | python3 -m json.tool
```

查看最近任务：

```bash
curl -s "http://127.0.0.1:8000/api/v1/tasks/?limit=3" | python3 -m json.tool
```

## 六、用例 1：无附件提示

飞书发送：

```text
识别这张发票
```

但不上传图片。

期望：

- 返回未收到可识别图片或文件
- steps 有 feishu_attachment_missing
- 不报 500
- 不进入正式写入
- 不触发 RPA

## 七、用例 2：上传图片 + OCR 识别

飞书上传一张自造样例图片，并发送：

```text
识别这张发票
```

期望：

- feishu_attachment_detected
- feishu_file_download_started
- feishu_file_download_succeeded
- ocr_document_started
- ocr_document_succeeded
- 返回 OCR 摘要
- evidence 保存成功
- 不写正式业务结果
- 不触发 RPA

## 八、用例 3：上传图片 + 字段提取

飞书上传一张自造样例图片，并发送：

```text
提取这张发票字段
```

期望：

- 附件检测成功
- 文件下载成功
- OCR 成功
- structured extraction 成功
- 返回字段摘要
- 不写正式业务结果
- 不触发 RPA

## 九、用例 4：类型不支持

上传不支持文件，例如 docx / xlsx / zip。

飞书发送：

```text
识别这个文件
```

期望：

- 返回当前类型不支持
- steps 有 feishu_file_unsupported_type
- 不进入 OCR
- 不报 500

## 十、验收查询

查看任务详情：

```bash
curl -s "http://127.0.0.1:8000/api/v1/tasks/{task_id}" | python3 -m json.tool
```

查看任务 steps：

```bash
curl -s "http://127.0.0.1:8000/api/v1/tasks/{task_id}/steps" | python3 -m json.tool
```

## 十一、重点检查

重点检查：

- status
- intent
- feishu_attachment_detected
- feishu_attachment_missing
- feishu_file_download_started
- feishu_file_download_succeeded
- feishu_file_download_failed
- feishu_file_unsupported_type
- ocr_document_succeeded
- document_extraction_succeeded
- evidence_relative_path
- file_hash
- formal_write=false

确认没有出现：

- token 泄露
- 下载 URL 泄露
- 完整绝对路径暴露
- 字段人工修正
- 写数据库正式结果
- 写飞书多维表
- 自动报销
- 自动付款
- 发票真伪判断
- RPA 执行

## 十二、通过标准

P15-D 实机通过标准：

- 无附件有友好提示
- 上传图片可被检测
- 文件可下载
- evidence 可保存
- OCR 链路可执行
- 结构化提取链路可执行
- steps 可追踪附件检测 / 下载 / OCR / 提取
- 不泄露敏感信息
- 不写正式业务结果
- 不触发 RPA
- 不破坏 P15-A/B/C
- 不破坏 P14