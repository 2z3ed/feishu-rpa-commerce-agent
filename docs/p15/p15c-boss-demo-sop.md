# P15-C 老板演示 SOP：发票 / 小票结构化字段提取

## 一、演示目标

验证系统已经从“能 OCR 读文字”升级为“能把 OCR 文字整理成业务字段”。

P15-C 的重点不是发票验真，也不是自动报销，而是演示：

- OCR raw_text 能进入结构化提取层
- 系统能提取发票号码、开票日期、购买方、金额
- 系统能标记缺失字段
- 系统能给出整体置信度
- 系统能提示人工复核
- 系统不会写入正式业务结果
- 系统不会触发 RPA

## 二、演示前提

P15-A 已完成并收口。  
P15-B 已完成并收口。  

P15-C 只做结构化字段提取。

不做：

- 飞书附件下载
- 字段人工修正
- 写入多维表
- 自动报销
- 自动付款
- 发票真伪校验
- RPA

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
```

如果结构化命令依赖 P14-A fallback，也需要：

```bash
export ENABLE_LLM_INTENT_FALLBACK=true
export LLM_INTENT_PROVIDER=mock
```

注意：

agent 不应擅自修改真实 .env。  
如果需要持久化环境变量，由用户人工同步。

## 四、启动服务

启动 API：

```bash
./scripts/dev_run_api.sh
```

另开终端启动 worker：

```bash
cd ~/feishu-rpa-commerce-agent
source venv/bin/activate 2>/dev/null || source .venv/bin/activate
export USE_SQLITE=true
export ENABLE_OCR_DOCUMENT_RECOGNIZE=true
export OCR_DOCUMENT_PROVIDER=mock
export ENABLE_DOCUMENT_STRUCTURED_EXTRACTION=true
export DOCUMENT_EXTRACTION_PROVIDER=rule
./scripts/dev_run_worker.sh
```

另开终端启动飞书长连接：

```bash
cd ~/feishu-rpa-commerce-agent
source venv/bin/activate 2>/dev/null || source .venv/bin/activate
export USE_SQLITE=true
export ENABLE_OCR_DOCUMENT_RECOGNIZE=true
export OCR_DOCUMENT_PROVIDER=mock
export ENABLE_DOCUMENT_STRUCTURED_EXTRACTION=true
export DOCUMENT_EXTRACTION_PROVIDER=rule
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

## 六、用例 1：发票字段提取

飞书发送：

```text
提取这张发票字段
```

期望：

- intent=document.structured_extract
- 调用 OCR mock provider
- 调用 rule extractor
- 返回发票号码、开票日期、购买方、金额
- 有 overall_confidence
- 有 needs_manual_review
- 有 missing_fields
- steps 有 ocr_document_succeeded
- steps 有 document_extraction_succeeded
- 不写正式业务结果
- 不触发 RPA

## 七、用例 2：票据信息提取

飞书发送：

```text
帮我提取票据信息
```

期望：

- intent=document.structured_extract
- 返回结构化字段摘要
- 不输出 JSON 原文
- 提示人工确认
- 不写正式业务结果

## 八、用例 3：发票结构化

飞书发送：

```text
把这张发票结构化一下
```

期望：

- OCR + extraction 链路都跑通
- 字段缺失有提示
- 有人工复核提醒
- 不做字段修改
- 不写正式业务结果

## 九、用例 4：字段缺失场景

可以通过测试 fixture 或 mock raw_text 缺字段触发。

期望：

- missing_fields 有值
- needs_manual_review=true
- 不报 500
- steps 有 document_extraction_succeeded 或 failed
- 飞书用户看到友好提示

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
- intent=document.structured_extract
- result_summary
- ocr_document_started
- ocr_document_succeeded
- document_extraction_started
- document_extraction_succeeded
- fields_count
- missing_fields_count
- overall_confidence
- needs_manual_review
- formal_write=false

确认没有出现：

- 飞书附件下载
- 字段人工修正
- 写数据库正式结果
- 写飞书多维表
- 自动报销
- 自动付款
- 发票真伪判断
- RPA 执行

## 十二、通过标准

P15-C 实机通过标准：

- 结构化提取命令可识别
- OCR raw_text 可进入提取层
- 发票核心字段可提取
- 缺失字段可提示
- 整体置信度可返回
- 人工复核提醒可返回
- task_steps 可追踪
- 不写正式业务结果
- 不触发 RPA
- 不破坏 P15-A/B
- 不破坏 P14