# P13-E Agent 开发提示词

你现在接手的是 A/B 双仓开发任务。

当前唯一主线是：

P13-E：定时价格刷新任务轻量版

## 一、双仓说明

A 项目：

```text
feishu-rpa-commerce-agent
```

职责：

- 飞书入口
- 消息编排
- Celery 调度控制层
- 定时调用 B refresh-prices
- 日志记录

B 项目：

```text
Ecom-Watch-Agent-Agent
```

职责：

- monitor target 数据
- 价格刷新
- price snapshot
- refresh run
- refresh run items
- refresh run 查询 API
- trigger_source 记录

本轮允许同时修改 A/B 两个仓库。

但必须遵守：

- A 是调度控制层
- B 是价格刷新执行层
- A 不保存 refresh run
- A 不计算价格变化
- B 不做调度系统
- B 只记录 trigger_source
- 不主动推送飞书消息
- 两个仓库分别测试
- 两个仓库分别清点
- 提交顺序必须是：先 B，后 A

## 二、当前现实

P13-A 已完成：

- B monitor target 有价格字段
- B 可刷新价格
- A 可触发“刷新监控价格”
- A 管理卡片可展示价格字段

P13-B 已完成：

- B 可写入 price snapshots
- B 可查询价格历史
- A 可查看价格历史

P13-C 已完成：

- B refresh-prices 返回变化汇总
- A 刷新价格后返回变化摘要

P13-D 已完成：

- B 每次刷新生成 run_id
- B 保存 refresh run / run items
- A 刷新回复展示 run_id
- A 可按 run_id 查询刷新详情

P13-E 只做定时触发。

本轮不是主动推送，不是告警，不是阈值规则。

## 三、开始前必须先读

A 项目必须读：

1. AGENTS.md
2. README.md
3. docs/p13/p13-project-plan.md
4. docs/p13/P13-agent-prompt.md
5. app/workers/celery_app.py
6. app/tasks/ingress_tasks.py
7. app/clients/b_service_client.py
8. app/graph/nodes/execute_action.py
9. tests/test_p10_b_query_integration.py

B 项目必须读：

1. README 或项目主说明
2. app/schemas/monitor_management.py
3. app/services/monitor_management_service.py
4. app/api/routes_internal_monitor.py
5. tests/test_monitor_management_api.py

如果 B 项目目录不存在或名称不匹配，先停止并回报，不要猜。

## 四、本轮唯一目标

实现：

```text
Celery Beat 定时触发
→ A 调 B refresh-prices(trigger_source=scheduled)
→ B 生成 run_id
→ B 记录 trigger_source=scheduled
→ worker 日志可观测
```

## 五、B 项目允许做

B 项目允许：

1. refresh-prices 接收 trigger_source
2. trigger_source 写入 refresh run
3. 保持 manual_feishu / manual_api / scheduled 等值
4. 增加 B 测试
5. 保留 P13-D run 查询

## 六、A 项目允许做

A 项目允许：

1. 新增 schedule_refresh_monitor_prices Celery task
2. 接入 Celery Beat，每 5 分钟执行一次
3. BServiceClient refresh_monitor_prices 支持 trigger_source
4. 增加调度日志
5. 增加 A 测试
6. 更新 README / docs / AGENTS

## 七、本轮禁止做

禁止：

- 不做飞书主动推送
- 不做价格告警
- 不做阈值规则
- 不做用户订阅
- 不做 cron UI
- 不做复杂调度系统
- 不做失败重试队列
- 不做任务优先级
- 不做复杂并发控制
- 不做后台管理页面
- 不破坏 P13-A/B/C/D
- 不破坏 P12 卡片交互
- 不混入 P13-F/G/H

## 八、A 定时任务要求

建议新增：

```text
app/tasks/scheduler_tasks.py
```

任务名建议：

```text
schedule_refresh_monitor_prices
```

任务逻辑：

```text
记录 START
调用 B refresh-prices，trigger_source=scheduled
记录 RESULT
异常时记录 FAILED
不主动发飞书消息
```

日志要求：

```text
=== P13E SCHEDULE TRIGGER START ===
=== P13E CALL B REFRESH ===
=== P13E SCHEDULE RESULT === run_id=... total=... changed=... failed=...
=== P13E SCHEDULE FAILED === error=...
```

## 九、Celery Beat 要求

在现有 Celery app 中添加 beat_schedule。

建议：

```python
{
  "refresh-monitor-prices-every-5-minutes": {
    "task": "app.tasks.scheduler_tasks.schedule_refresh_monitor_prices",
    "schedule": crontab(minute="*/5"),
  }
}
```

如果项目使用不同 task name 约定，以仓库现状为准。

## 十、测试要求

B 项目至少测试：

1. refresh-prices 支持 trigger_source=scheduled
2. run detail 中 trigger_source=scheduled
3. manual refresh 不退化
4. P13-D run detail 不退化

A 项目至少测试：

1. schedule_refresh_monitor_prices 调用 B
2. 调用时传 trigger_source=scheduled
3. 任务异常时不抛出不可控异常
4. beat_schedule 包含每 5 分钟任务
5. P13-D run 查询不退化
6. P12 回归不退化

## 十一、必须跑的检查

B 项目：

```bash
pytest -q tests/test_monitor_management_api.py
```

A 项目：

```bash
pytest -q tests/test_p10_b_query_integration.py
pytest -q tests/test_p13_a_monitor_price_card.py
bash scripts/p12_regression_check.sh
```

如果新增 P13-E 测试，也必须跑。

## 十二、完成后回报格式

必须按 A/B 分开回报：

A. 先读了哪些文件  
B. B 项目 trigger_source 当前锚定结果  
C. B 项目改了哪些文件  
D. B 项目 scheduled trigger 如何写入 run  
E. B 项目测试结果  
F. A 项目 Celery / Beat 锚定结果  
G. A 项目改了哪些文件  
H. A 项目定时任务如何设计  
I. A 项目日志如何设计  
J. A 项目测试结果  
K. 是否可以进入 A/B 联合验收  
L. 提交建议：B 先提交什么，A 后提交什么  

只允许使用简体中文。

不要只给计划。
不要只贴 diff。
不要混入 P13-F。