# 联调排查文档

## 0. Linux / WSL 本地启动步骤

### 前提条件
- Docker 已安装
- Python 3.12 已安装
- 项目依赖已安装 (`pip install -r requirements.txt`)

### 快速启动（推荐）

```bash
# 1. 创建并激活虚拟环境（如尚未创建）
python -m venv venv
source venv/bin/activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动 Docker 依赖服务（PostgreSQL, Redis, Milvus）
./scripts/dev_up.sh

# 4. 启动 FastAPI（终端1）
./scripts/dev_run_api.sh

# 5. 启动 Celery Worker（终端2）
./scripts/dev_run_worker.sh

# 6. 启动飞书长连接监听器（终端3）
./scripts/dev_run_feishu_longconn.sh
```

### 手动启动（不使用脚本）

```bash
# 1. 启动 Docker 依赖
docker compose -f docker-compose.dev.yml up -d

# 2. 激活虚拟环境
source venv/bin/activate

# 3. 启动 FastAPI
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 4. 启动 Celery Worker（单独终端）
python -m celery -A app.workers.celery_app worker --loglevel=info

# 5. 启动飞书长连接（单独终端）
python -m app.services.feishu.runner
```

### 验证

```bash
# 健康检查
curl http://localhost:8000/api/v1/health

# 预期返回（PostgreSQL 和 Redis 都连接成功时）:
# {
#   "code": 0,
#   "message": "success",
#   "data": {
#     "database": {"status": "connected", "error": null},
#     "redis": {"status": "connected", "error": null}
#   }
# }
```

### 常见问题

#### 问题1: `Command 'brew' not found`
```bash
# macOS 用户使用 brew，Linux/WSL 用户使用 docker
docker compose -f docker-compose.dev.yml up -d
```

#### 问题2: `celery: command not found`
```bash
# 确保激活了虚拟环境
source venv/bin/activate

# 或使用 python -m 调用
python -m celery -A app.workers.celery_app worker --loglevel=info
```

#### 问题3: `Error 111 connecting to localhost:6379/0. Connection refused.`
```bash
# 启动 Redis
docker compose -f docker-compose.dev.yml up -d redis
# 或确认 Redis 容器正在运行
docker ps | grep redis
```

#### 问题4: `'sessionmaker' object has no attribute 'execute'`
- 这是健康检查代码的 bug，已修复
- 确保代码已更新到最新版本

---

## 1. PostgreSQL 未运行时现象

### 现象
- FastAPI 启动时 `init_db()` 会尝试建表，如果 PostgreSQL 未运行，会在 startup 阶段报 warning：
  ```
  WARNING - Database init warning: could not connect to server
  ```
- 收到飞书消息后，数据库写入时报错：
  ```
  sqlalchemy.exc.OperationalError: could not connect to server
  ```
- `/api/v1/health` 接口返回 `code=1, message="database connection failed"`

### 排查命令
```bash
# 检查 PostgreSQL 进程
ps aux | grep postgres

# 测试数据库连接
psql -h localhost -p 5432 -U postgres -d feishu_rpa -c "SELECT 1"

# 或用 Python 测试
python3 -c "
from sqlalchemy import create_engine
engine = create_engine('postgresql://postgres:postgres@localhost:5432/feishu_rpa')
with engine.connect() as conn:
    print(conn.execute('SELECT 1'))
"
```

### 启动 PostgreSQL
```bash
# macOS
brew services start postgresql

# Ubuntu/Debian
sudo systemctl start postgresql
sudo systemctl enable postgresql  # 开机自启

# Docker
docker run -d --name postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=feishu_rpa -p 5432:5432 postgres:15
```

### 建表命令（自动）
程序启动时自动建表，调用 `init_db()`:
```python
# app/db/session.py
def init_db() -> None:
    from app.db.base import Base
    from app.db.models import MessageIdempotency, TaskRecord
    Base.metadata.create_all(bind=engine)
```
会自动创建以下表：
- `task_records`
- `message_idempotency`

---

## 2. Redis 未运行时现象

### 现象
- FastAPI 启动正常，健康检查通过
- 飞书长连接收到消息，数据库写入成功
- Celery 入队时报错：
  ```
  kombu.exceptions.ComunicationError: <Connection: ...>
  ```
- 如果 Celery Worker 已启动但 Redis 未运行：
  - 任务卡在 `pending` 状态
  - Worker 日志：
    ```
    ERROR: Unable to connect to Redis: Connection refused
    ```

### 排查命令
```bash
# 检查 Redis 进程
ps aux | grep redis-server

# 测试 Redis 连接
redis-cli ping
```

### 启动 Redis
```bash
# macOS
brew services start redis

# Ubuntu/Debian
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Docker
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

### Celery Worker 启动命令
```bash
# 方式1: 直接启动（推荐开发调试）
celery -A app.workers.celery_app worker --loglevel=info

# 方式2: 后台启动
celery -A app.workers.celery_app worker --loglevel=info --detach --pidfile=/tmp/celery.pid

# 方式3: 指定日志文件
celery -A app.workers.celery_app worker --loglevel=info --logfile=/tmp/celery.log

# 验证 worker 启动成功
celery -A app.workers.celery_app inspect active
```
注意：`ingress_tasks.py` 中任务名为 `ingress.process_message`，Celery Worker 会自动发现。

---

## 3. 收到飞书消息但数据库没新增 - 排查步骤

### 排查路径
```
1. 确认长连接已启动
2. 确认收到飞书事件
3. 确认解析成功
4. 确认数据库写入
```

### 步骤1: 检查长连接是否启动
查看日志，搜索关键字：
```
grep "Feishu long connection listener started" app.log
```
期望看到：
```
INFO - Feishu long connection listener started, thread running
```

### 步骤2: 确认收到飞书事件
查看日志，搜索关键字：
```
# 原始 payload
grep "Received Feishu event raw payload" app.log

# 解析后字段
grep "Parsed message event fields" app.log
```
期望看到：
```
INFO - Received Feishu event raw payload - event_type=im.message.receive_v1, raw_payload={...}
INFO - Parsed message event fields - message_id=xxx, chat_id=xxx, open_id=xxx, text=xxx
```

### 步骤3: 检查解析是否返回 None
如果日志显示 "Message event parse returned None, skipping"：
- 检查消息是否为文本类型（目前只处理文本消息）
- 检查消息内容是否为空

### 步骤4: 检查数据库写入
查看日志，搜索：
```
grep "Database write successful" app.log
```
如果没有这条日志，说明写入失败，检查：
- 数据库连接是否正常
- 表是否存在

手动查询：
```bash
psql -h localhost -p 5432 -U postgres -d feishu_rpa -c "SELECT * FROM message_idempotency LIMIT 5;"
psql -h localhost -p 5432 -U postgres -d feishu_rpa -c "SELECT * FROM task_records ORDER BY created_at DESC LIMIT 5;"
```

---

## 4. 数据库新增但机器人不回消息 - 排查步骤

### 排查路径
```
1. 检查 Celery 入队
2. 检查飞书 API 调用
3. 检查 message_id 有效性
```

### 步骤1: 检查 Celery 入队
查看日志，搜索：
```
grep "Celery task enqueued" app.log
```
期望看到：
```
INFO - Celery task enqueued - task_id=TASK-xxx, celery_task_id=xxx
```

如果没有：
- 检查 Redis 是否运行
- 检查 Celery Worker 是否启动

```bash
celery -A app.workers.celery_app inspect active
celery -A app.workers.celery_app inspect scheduled
```

### 步骤2: 检查飞书 API 调用
查看日志，搜索：
```
grep "Feishu reply" app.log
```
期望看到成功：
```
INFO - Feishu reply sent successfully - message_id=xxx, task_id=xxx
```
或失败：
```
ERROR - Feishu reply failed - message_id=xxx, task_id=xxx, code=xxx, msg=xxx
```

### 步骤3: 检查 message_id 有效性
飞书消息回复需要有效的 `message_id`。可能原因：
- 消息类型不支持回复（目前只支持文本消息）
- message_id 已过期

调试：
```python
from app.services.feishu.client import feishu_client
result = feishu_client.send_text_reply(
    message_id="your_message_id",
    text="test"
)
print(f"Result: {result}")
```

---

## 5. 完整调试流程图

```
┌─────────────────┐
│  收到飞书消息   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐    No    ┌─────────────┐
│  解析成功？     │ ───────► │ 跳过处理    │
└────────┬────────┘          └─────────────┘
         │ Yes
         ▼
┌─────────────────┐    No    ┌─────────────┐
│  幂等命中？     │ ───────► │ 创建新任务  │
└────────┬────────┘          └──────┬──────┘
         │ Yes                     │
         ▼                         ▼
┌─────────────────┐    ┌─────────────────┐
│  返回历史task_id │    │  数据库写入OK？ │
└────────┬────────┘    └────────┬────────┘
         │                     │ No
         │                     ▼
         │              ┌─────────────┐
         │              │ 检查PostgreSQL│
         │              └─────────────┘
         │                     │
         ▼                     ▼
┌─────────────────┐    ┌─────────────────┐
│ Celery 入队OK？ │    │  Celery入队    │
└────────┬────────┘    └────────┬────────┘
         │                     │
         ▼                     ▼
┌─────────────────┐    ┌─────────────────┐
│ 飞书回执发送OK？│    │ 发送回执成功？ │
└────────┬────────┘    └────────┬────────┘
         │                     │
    Yes  │                     │
         ▼                     ▼
┌─────────────────┐    ┌─────────────────┐
│   流程完成      │    │ 检查飞书API凭证 │
└─────────────────┘    └─────────────────┘
```

---

## 6. 常用调试命令汇总

```bash
# 1. 启动 PostgreSQL (macOS)
brew services start postgresql

# 2. 启动 Redis (macOS)
brew services start redis

# 3. 启动 FastAPI
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 4. 启动 Celery Worker（单独终端）
celery -A app.workers.celery_app worker --loglevel=info

# 5. 启动飞书长连接监听器（单独终端）
python -m app.services.feishu.runner

# 6. 健康检查
curl http://localhost:8000/api/v1/health

# 7. 查看数据库记录
psql -h localhost -p 5432 -U postgres -d feishu_rpa \
  -c "SELECT task_id, status, intent_text, created_at FROM task_records ORDER BY created_at DESC LIMIT 5;"

# 8. 查看 Celery 任务状态
celery -A app.workers.celery_app inspect active

# 9. 查看 Redis 连接
redis-cli info clients
```

---

## 7. 日志关键字索引

| 关键字 | 含义 | 日志级别 |
|--------|------|----------|
| `Feishu long connection listener started` | 长连接启动成功 | INFO |
| `Received Feishu event raw payload` | 收到飞书原始事件 | INFO |
| `Parsed message event fields` | 解析完成，提取字段 | INFO |
| `Idempotency hit` | 幂等命中，重复消息 | INFO |
| `Database write successful` | 数据库写入成功 | INFO |
| `Celery task enqueued` | Celery 入队成功 | INFO |
| `Feishu reply sent successfully` | 飞书回执发送成功 | INFO |
| `Feishu reply failed` | 飞书回执发送失败 | ERROR |
| `Long connection error` | 长连接异常 | ERROR |

---

## 8. 服务启动顺序

正确启动顺序：

```bash
# 1. 启动 PostgreSQL
brew services start postgresql  # 或其他方式

# 2. 启动 Redis
brew services start redis  # 或其他方式

# 3. 启动 Celery Worker（终端1）
celery -A app.workers.celery_app worker --loglevel=info

# 4. 启动 FastAPI（终端2）
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 5. 启动飞书长连接（终端3）
python -m app.services.feishu.runner
```