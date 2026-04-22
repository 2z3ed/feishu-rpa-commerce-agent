# P9-B：主系统留痕回接（SQLite 验证版）agent 提示词

你现在继续接手 feishu-rpa-commerce-agent 项目。

当前不要再回头修改：
- ShadowBot success 主流程
- failure 副本/注入式 failure
- P93 success 收口文档
- evidence 兜底逻辑
- latest-file 临时方案
- PostgreSQL 作为首轮验收环境

当前唯一主线已经重新收窄为：

**P9-B：主系统留痕回接（SQLite 验证版）**

---

## 一、当前必须继承的真实状态

当前已经成立的内容，不要回头重做：

1. ShadowBot real-runtime success 真点击链已经成立
2. self-hosted real_nonprod_page 已真实执行成功
3. success 样本已经验证过 `100 -> 105`
4. runtime `done.json` 已成立
5. 左侧 `outbox.output.json` 已成立
6. success 样本中的 `bridge_result_timeout` 已收住
7. evidence 至少已有 `runtime-result.json` 兜底文件
8. 当前未继续收口的 failure 分支已经明确后移，不作为本轮阻塞项

---

## 二、本轮唯一目标

把已经跑通的 real-runtime success 结果，正式回接到主系统数据库留痕。

本轮最低要求：

- 8000 主系统可启动
- worker 可启动
- success 样本经过主系统执行
- `task_records` 有记录
- `task_steps` 有记录
- `action_executed.detail` 有最小 RPA 字段
- `/tasks`
- `/tasks/{task_id}`
- `/tasks/{task_id}/steps`
  可查
- 后续再由主系统异步写飞书多维表

---

## 三、本轮数据库策略

当前阶段固定：

- **先用 SQLite 做主系统留痕回接验证**
- PostgreSQL 回归后移

原则固定为：

- 数据库是真相源
- 多维表只是业务台账
- ShadowBot 不直接写多维表
- RPA 结果必须先回主系统，再由主系统写台账

---

## 四、本轮范围收窄

本轮只围绕：

- `warehouse.adjust_inventory`
- success 主链
- 主系统留痕
- SQLite 验证
- 多维表字段设计

本轮不做：

- failure 真实分支收口
- 真实截图增强
- latest-file 临时方案回收
- PostgreSQL 联调
- 第二个动作
- `product.update_price`
- 真实生产页
- 让 ShadowBot 直接写飞书/多维表

---

## 五、本轮必须完成的事

### 1. SQLite 验证环境锚定
需要完成：

- 明确 `USE_SQLITE=true`
- 明确 SQLite 文件路径
- 确认 8000 主系统可启动
- 确认 Celery worker 可启动
- 确认 success 固定运行命令

### 2. success 结果正式落库
需要完成：

- 通过主系统链路触发一次 `warehouse.adjust_inventory`
- 在数据库中生成任务记录
- 在数据库中生成步骤记录
- 把 RPA 最小字段写进 `action_executed.detail`

`action_executed.detail` 最小必须包含：

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

### 3. API 可查验收
需要完成：

- `/api/v1/tasks/` 可查
- `/api/v1/tasks/{task_id}` 可查
- `/api/v1/tasks/{task_id}/steps` 可查

### 4. Bitable 方案冻结
需要完成：

- 保留原任务业务台账主表
- 设计并冻结一张新的 `RPA执行证据台账`
- 本轮先冻结字段，不强求把多维表写入彻底做完

---

## 六、本轮允许修改的文件

优先允许修改：

- `script/p91_yingdao_real_rehearsal.py`
- `app/rpa/yingdao_runner.py`
- `app/bridge/yingdao_local_bridge.py`
- 任务写库相关节点
- `/tasks` `/steps` 相关读取逻辑
- 与 SQLite 验证相关的配置与文档

如确有必要，可以极小修改：

- `README.md`
- RPA 基线文档
- handoff 文档

但不要重写总叙事。

---

## 七、本轮绝对禁止做的事

不要做：

- 不要继续修改 ShadowBot success 主流程
- 不要继续打磨 failure 副本
- 不要把多维表当唯一留痕源
- 不要跳去 PostgreSQL 做第一轮验收
- 不要扩第二个动作
- 不要切到 `product.update_price`
- 不要接真实生产页
- 不要重构既有任务系统主链
- 不要对外宣称“飞书留痕已完成”，除非数据库留痕和台账都已验收

---

## 八、本轮固定 success 验证命令

```bash
./venv/bin/python script/p91_yingdao_real_rehearsal.py --mode real-runtime --clean-all --reset-db-inventory 100 --sku A001 --old-inventory 100 --delta 5 --target-inventory 105 --bridge-wait-timeout-s 180
```

---

## 九、P9-B 验收环境锚定（冻结）

### 1) python / venv

- 必须使用项目 venv：`./venv/bin/python`（Python 3.12.3）

### 2) SQLite 文件路径

- 固定为：`sqlite:///./feishu_rpa.db`（仓库根目录 `./feishu_rpa.db`）

### 3) 端口与启动命令（仅用于本地验收）

stub（18081）：

```bash
cd ~/feishu-rpa-commerce-agent
source venv/bin/activate
bash script/run_nonprod_admin_stub.sh
```

主系统（8000）：

```bash
cd ~/feishu-rpa-commerce-agent
./venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

worker：

```bash
cd ~/feishu-rpa-commerce-agent
./venv/bin/python -m celery -A app.workers.celery_app worker --loglevel=info -n p9b@%h -c 1
```

---

## 十、P9-B.1/P9-B.2 success 样本硬证据（冻结）

- task_id：`TASK-P9B-ODOO-ADJ-ORIG-P92-1776864344799-8bddc2cc`
- confirm_task_id：`TASK-P9B-ODOO-ADJ-CFM-P92-1776864344799-8bddc2cc`
- run_id：`TASK-P9B-ODOO-ADJ-CFM-P92-1776864344799-8bddc2cc`

文件路径：

- done：`/mnt/z/yingdao_bridge/done/TASK-P9B-ODOO-ADJ-CFM-P92-1776864344799-8bddc2cc.done.json`
- outbox：`tmp/yingdao_bridge/outbox/TASK-P9B-ODOO-ADJ-CFM-P92-1776864344799-8bddc2cc.output.json`
- runtime evidence：`/mnt/z/yingdao_bridge/evidence/TASK-P9B-ODOO-ADJ-CFM-P92-1776864344799-8bddc2cc-runtime-result.json`

可查接口：

- `/api/v1/tasks/`
- `/api/v1/tasks/{task_id}`
- `/api/v1/tasks/{task_id}/steps`

`action_executed.detail` 最小字段（10 项）已落库可查：

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

## 十一、Bitable 非阻塞说明（边界冻结）

- `bitable_write_failed` 根因：缺少 `lark_oapi` 依赖（`No module named 'lark_oapi.api'`）
- 结论：非阻塞，不影响当前 P9-B 验收成立
- 边界：当前以 **SQLite + `/api/v1/tasks*`** 为真相源；飞书多维表写入后移或可选