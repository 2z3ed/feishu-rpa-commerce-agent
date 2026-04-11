# LangGraph 最小状态流实现说明

## 已完成内容

### 1. LangGraph 最小骨架
实现了以下模块：

- `app/graph/state.py` - Graph State 定义
- `app/graph/builder.py` - LangGraph 构建器
- `app/graph/nodes/load_task_context.py` - 加载任务上下文
- `app/graph/nodes/parse_command.py` - 解析命令文本
- `app/graph/nodes/resolve_intent.py` - 识别意图
- `app/graph/nodes/execute_action.py` - 执行动作
- `app/graph/nodes/finalize_result.py` -  finalize 结果并更新任务记录

### 2. Graph State 包含的字段
- `task_id`: 任务 ID
- `source_message_id`: 飞书消息 ID
- `source_chat_id`: 聊天 ID
- `user_open_id`: 用户 open_id
- `raw_text`: 原始文本
- `normalized_text`: 标准化后的文本
- `intent_code`: 识别的意图
- `slots`: 提取的参数
- `execution_mode`: 执行模式
- `result_summary`: 结果摘要
- `error_message`: 错误消息
- `status`: 任务状态
- `platform`: 目标平台

### 3. LangGraph 流程
```
load_task_context
→ parse_command
→ resolve_intent
→ execute_action
→ finalize_result
```

### 4. 第一个真实动作：product.query_sku_status
支持命令示例：
- "查询 SKU A001 状态"
- "帮我查一下 SKU A001"
- "看一下商品 A001 库存和状态"
- "查 SKU A001"

提取参数：
- `sku` (必填): SKU 代码
- `platform` (可选): 平台 (woo/odoo)，默认 mock

Mock 返回示例：
```
SKU: A001
商品：示例商品 A001
状态：active
库存：128
价格：59.9
平台：mock
```

### 5. Celery 接 LangGraph
修改了 `app/tasks/ingress_tasks.py`:
- 读取 task_record
- 构造 graph state
- 调用 LangGraph 执行
- 将结果写回 task_record
- 发送飞书结果消息

### 6. task_records 状态推进
状态流转：
- `received`: 初始状态
- `queued`: 已入 Celery 队列
- `processing`: Worker 开始处理
- `succeeded`: Graph 执行成功
- `failed`: Graph 执行失败

更新字段：
- `intent_code`
- `result_summary`
- `error_message`
- `started_at`
- `finished_at`

### 7. 飞书结果回执
Graph 成功后，自动发送结果消息到飞书：
```
SKU: A001
商品：示例商品 A001
状态：active
库存：128
价格：59.9
平台：mock
```

## 修改的文件列表

1. `app/tasks/ingress_tasks.py` - 集成 LangGraph
2. `app/services/feishu/longconn.py` - 传递 message_id 和 chat_id 给 Celery
3. `app/graph/nodes/resolve_intent.py` - 修复 SKU 提取正则
4. `requirements.txt` - 添加 langgraph 依赖

## 新增的文件列表

1. `app/graph/__init__.py`
2. `app/graph/state.py`
3. `app/graph/builder.py`
4. `app/graph/nodes/__init__.py`
5. `app/graph/nodes/load_task_context.py`
6. `app/graph/nodes/parse_command.py`
7. `app/graph/nodes/resolve_intent.py`
8. `app/graph/nodes/execute_action.py`
9. `app/graph/nodes/finalize_result.py`
10. `app/repositories/__init__.py`
11. `app/repositories/product_repo.py`
12. `test_langgraph.py`

## 本地启动方式

1. 启动依赖服务：
```bash
./scripts/dev_up.sh
```

2. 启动 FastAPI：
```bash
./scripts/dev_run_api.sh
```

3. 启动 Celery Worker：
```bash
./scripts/dev_run_worker.sh
```

4. 启动飞书长连接监听器：
```bash
./scripts/dev_run_feishu_longconn.sh
```

## 手动验证步骤

### 测试 1: 查询 SKU 状态
在飞书中发送：
```
查询 SKU A001 状态
```

预期日志：
- `=== FEISHU EVENT RECEIVED ===`
- `=== PARSER SUCCESS ===`
- `=== CELERY ENQUEUE START ===`
- `=== LANGGRAPH EXECUTION START ===`
- `Intent resolved: intent_code=product.query_sku_status, slots={'sku': 'A001'}`
- `Product query executed successfully: sku=A001`
- `=== LANGGRAPH EXECUTION END ===`
- `Feishu result message sent`

预期 task_records 变化：
- `status`: succeeded
- `intent_code`: product.query_sku_status
- `result_summary`: "SKU：A001\n商品：示例商品 A001\n状态：active\n库存：128\n价格：59.9\n平台：mock"
- `started_at`: 有时间戳
- `finished_at`: 有时间戳

预期飞书收到：
```
SKU: A001
商品：示例商品 A001
状态：active
库存：128
价格：59.9
平台：mock
```

### 测试 2: 未知命令
在飞书中发送：
```
你好
```

预期日志：
- `=== FEISHU EVENT RECEIVED ===`
- `=== PARSER SUCCESS ===`
- `=== CELERY ENQUEUE START ===`
- `=== LANGGRAPH EXECUTION START ===`
- `Unknown intent: text='你好'`
- `Cannot execute unknown intent`
- `=== LANGGRAPH EXECUTION END ===`

预期 task_records 变化：
- `status`: failed
- `intent_code`: unknown
- `result_summary`: "未识别到已知命令，请尝试其他表述方式"

预期飞书收到：
```
未识别到已知命令，请尝试其他表述方式
```

## 意图识别规则

当前 `product.query_sku_status` 的识别规则：
1. 文本包含 "SKU" 或 "商品" 或 "产品" + 字母数字组合
2. 或者文本中包含字母 + 数字组合 (如 A001)
3. 并且包含查询关键词：查询、查、看一下、看看、状态、库存

## Mock 商品数据

当前 mock 数据库包含：
- A001: 示例商品 A001, active, 库存 128, 价格 59.90
- A002: 示例商品 A002, inactive, 库存 0, 价格 99.00
- B001: 示例商品 B001, active, 库存 256, 价格 129.50

## 下一步扩展

要添加新的业务动作，只需：
1. 在 `app/graph/nodes/resolve_intent.py` 中添加新的意图识别逻辑
2. 在 `app/graph/nodes/execute_action.py` 中添加新的执行逻辑
3. 可选：在 `app/repositories/` 中添加新的 repository
