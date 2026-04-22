# SQLite版 P9-B 最小验收 SOP

## 一、目的

验证这条链是否已经成立：

主系统（8000）  
→ 任务创建  
→ confirm 放行  
→ YingdaoRunner / bridge / ShadowBot 执行  
→ `done/outbox` 回传  
→ 数据库写入 `task_records / task_steps / action_executed.detail`  
→ `/tasks` `/steps` 可查

当前使用 SQLite 做本轮首验收。

---

## 二、验收前提

本 SOP 默认：

- 使用 SQLite
- 使用当前已经跑通的 ShadowBot success 主链
- 使用 self-hosted real_nonprod_page
- 暂不深挖 failure
- 暂不要求 PostgreSQL
- 暂不要求真实截图链，只接受 runtime-result.json 兜底

---

## 三、启动准备

### 1. 终端 A：启动 stub 后台

```bash
cd ~/feishu-rpa-commerce-agent
source venv/bin/activate
bash script/run_nonprod_admin_stub.sh
```

### 2. 终端 B：启动 8000 主系统（必须使用项目 venv）

```bash
cd ~/feishu-rpa-commerce-agent
./venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3. 终端 C：启动 Celery worker（必须使用项目 venv）

```bash
cd ~/feishu-rpa-commerce-agent
./venv/bin/python -m celery -A app.workers.celery_app worker --loglevel=info -n p9b@%h -c 1
```

### 4. 验证 health（Redis + DB 必须都 connected）

```bash
curl -s http://127.0.0.1:8000/api/v1/health
```

期望包含（示例）：

- `database.status=connected`
- `redis.status=connected`

---

## 四、success baseline 固定命令（A001：100 -> 105）

```bash
cd ~/feishu-rpa-commerce-agent
./venv/bin/python script/p91_yingdao_real_rehearsal.py \
  --mode real-runtime \
  --clean-all \
  --reset-db-inventory 100 \
  --sku A001 \
  --old-inventory 100 \
  --delta 5 \
  --target-inventory 105 \
  --bridge-wait-timeout-s 180
```

---

## 五、本轮已通过的硬证据（冻结）

### 1) python / venv（锚定）

- `./venv/bin/python`（Python 3.12.3）

### 2) SQLite 文件路径（真相源）

- `sqlite:///./feishu_rpa.db`（仓库根目录 `./feishu_rpa.db`）

### 3) 本轮 success 任务 ID（主系统落库）

- task_id：`TASK-P9B-ODOO-ADJ-ORIG-P92-1776864344799-8bddc2cc`
- confirm_task_id：`TASK-P9B-ODOO-ADJ-CFM-P92-1776864344799-8bddc2cc`
- run_id：`TASK-P9B-ODOO-ADJ-CFM-P92-1776864344799-8bddc2cc`

### 4) done / outbox / evidence（可复验）

- done：`/mnt/z/yingdao_bridge/done/TASK-P9B-ODOO-ADJ-CFM-P92-1776864344799-8bddc2cc.done.json`
- outbox：`tmp/yingdao_bridge/outbox/TASK-P9B-ODOO-ADJ-CFM-P92-1776864344799-8bddc2cc.output.json`
- runtime evidence：`/mnt/z/yingdao_bridge/evidence/TASK-P9B-ODOO-ADJ-CFM-P92-1776864344799-8bddc2cc-runtime-result.json`

### 5) API 可查（可查询）

```bash
curl -s http://127.0.0.1:8000/api/v1/tasks/
curl -s http://127.0.0.1:8000/api/v1/tasks/TASK-P9B-ODOO-ADJ-ORIG-P92-1776864344799-8bddc2cc
curl -s http://127.0.0.1:8000/api/v1/tasks/TASK-P9B-ODOO-ADJ-CFM-P92-1776864344799-8bddc2cc/steps
```

### 6) `action_executed.detail` 最小 RPA 字段已落库（可留痕）

以 confirm 任务 steps 中的 `action_executed.detail` 为准，以下 10 个字段**均已出现**：

- `rpa_vendor`
- `run_id`
- `operation_result`
- `verify_passed`
- `verify_reason`
- `page_failure_code`
- `failure_layer`
- `page_steps`
- `page_evidence_count`
- `screenshot_paths`

---

## 六、Bitable 非阻塞说明（必须后移/可选）

- `bitable_write_failed` 根因：缺少 `lark_oapi` 依赖（报错 `No module named 'lark_oapi.api'`）
- 结论：**非阻塞**，不影响本 SOP 验收；当前以 **SQLite + `/api/v1/tasks*`** 为真相源