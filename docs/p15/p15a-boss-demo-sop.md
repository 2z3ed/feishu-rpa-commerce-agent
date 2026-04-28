# P15-A 老板演示 SOP：OCR 识别骨架与 mock 闭环

## 一、演示目标

验证系统已经具备 OCR 任务骨架。

P15-A 不是演示真实 OCR 准确率，而是演示：

- 系统能识别 OCR 命令
- 系统能创建 OCR 任务
- 系统能调用 mock OCR provider
- 系统能返回 OCR 识别摘要
- 系统能记录 OCR steps
- OCR 结果不会被当作最终业务事实
- OCR 结果不会自动写入正式业务记录

## 二、演示前提

P14 已完成并收口。

P15-A 只做 OCR mock 闭环。

不做：

- 真实 OCR
- PaddleOCR
- 飞书附件下载
- 发票字段结构化
- 人工确认
- 写入多维表
- 自动报销
- 自动付款

## 三、启动前环境

进入 A 项目：

cd ~/feishu-rpa-commerce-agent  
source venv/bin/activate 2>/dev/null || source .venv/bin/activate  

建议环境变量：

export USE_SQLITE=true  
export ENABLE_OCR_DOCUMENT_RECOGNIZE=true  
export OCR_DOCUMENT_PROVIDER=mock  

如果 OCR 命令依赖 P14-A fallback，也需要：

export ENABLE_LLM_INTENT_FALLBACK=true  
export LLM_INTENT_PROVIDER=mock  

注意：

agent 不应擅自修改真实 .env。  
如果需要持久化环境变量，由用户人工同步。

## 四、启动服务

启动 API：

./scripts/dev_run_api.sh

另开终端启动 worker：

cd ~/feishu-rpa-commerce-agent  
source venv/bin/activate 2>/dev/null || source .venv/bin/activate  
export USE_SQLITE=true  
export ENABLE_OCR_DOCUMENT_RECOGNIZE=true  
export OCR_DOCUMENT_PROVIDER=mock  
./scripts/dev_run_worker.sh

另开终端启动飞书长连接：

cd ~/feishu-rpa-commerce-agent  
source venv/bin/activate 2>/dev/null || source .venv/bin/activate  
export USE_SQLITE=true  
export ENABLE_OCR_DOCUMENT_RECOGNIZE=true  
export OCR_DOCUMENT_PROVIDER=mock  
./scripts/dev_run_feishu_longconn.sh

如果脚本名称和仓库不一致，以仓库实际脚本为准。

## 五、健康检查

curl -s http://127.0.0.1:8000/api/v1/health | python3 -m json.tool

查看最近任务：

curl -s "http://127.0.0.1:8000/api/v1/tasks/?limit=3" | python3 -m json.tool

## 六、用例 1：OCR 基础命令

飞书发送：

识别这张发票

期望：

- 识别为 document.ocr_recognize
- 调用 mock OCR provider
- 返回发票类 OCR 摘要
- steps 有 ocr_document_started / succeeded
- 不写入正式业务记录

## 七、用例 2：图片文字识别命令

飞书发送：

提取这张图片里的文字

期望：

- 识别为 OCR intent
- 返回 raw_text 摘要
- 返回 confidence
- 提示需要人工确认

## 八、用例 3：票据识别命令

飞书发送：

帮我识别票据文字

期望：

- 返回 mock OCR 结果
- 文案说明当前只是 OCR 初步识别
- 不做结构化字段提取
- 不做自动归档

## 九、用例 4：provider 失败降级

通过临时配置模拟 OCR provider 失败。

将真实 .env 临时改为：

OCR_DOCUMENT_PROVIDER=unsupported

重启 worker 后发送：

识别这张发票

期望：

- 不报 500
- 不向飞书展示 traceback
- 返回友好失败或降级提示
- steps 有 ocr_document_failed 或 ocr_document_fallback_used
- 不写入正式业务记录

测试后必须恢复：

OCR_DOCUMENT_PROVIDER=mock

并重启 worker。

## 十、验收查询

查看任务详情：

curl -s "http://127.0.0.1:8000/api/v1/tasks/{task_id}" | python3 -m json.tool

查看任务 steps：

curl -s "http://127.0.0.1:8000/api/v1/tasks/{task_id}/steps" | python3 -m json.tool

## 十一、通过标准

P15-A 实机通过标准：

- OCR 命令可识别
- mock OCR provider 可调用
- 能返回 raw_text / confidence / provider
- 能提示人工确认
- OCR 失败能友好处理
- task_steps 可追踪
- 不写入正式业务记录
- 不触发 RPA
- 不破坏 P14