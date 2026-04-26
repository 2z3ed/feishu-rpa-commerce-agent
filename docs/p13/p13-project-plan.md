# P13-E 开发主线文档

## 阶段名称

P13-E：定时价格刷新任务轻量版

## 一、阶段背景

P13-A 已完成价格数据最小闭环：

- monitor target 有价格字段
- 可以刷新价格
- 可以展示 current_price / last_price / price_delta

P13-B 已完成价格历史：

- 每次刷新写入 price snapshot
- 可以查询价格历史

P13-C 已完成变化摘要：

- 手动刷新后，飞书能返回本轮价格变化摘要

P13-D 已完成刷新任务留痕：

- 每次刷新生成 run_id
- 保存 run summary 与 run items
- 飞书可按 run_id 查询刷新详情

现在缺口是：

所有价格刷新仍然依赖人工发送“刷新监控价格”。

P13-E 只补齐自动执行的最小能力：

通过 A 项目的 Celery Beat 定时触发 B 的 refresh-prices。

## 二、本轮唯一目标

只做：

定时价格刷新任务轻量版。

目标链路：

```text
Celery Beat 定时触发
→ A 执行 schedule_refresh_monitor_prices
→ A 调 B refresh-prices，trigger_source=scheduled
→ B 生成 run_id
→ B 写入 run / run items
→ worker 日志记录 run_id / total / changed / failed
→ run 可通过 P13-D 查询
```

## 三、A/B 双仓分工

### A 项目：feishu-rpa-commerce-agent

职责：

- 作为调度控制层
- 配置 Celery Beat
- 新增定时 task
- 定时调用 B refresh-prices
- 输出调度日志
- 不主动推送飞书消息

A 不允许：

- 不保存 refresh run
- 不保存价格历史
- 不计算价格变化
- 不做告警规则
- 不做飞书主动推送
- 不做复杂调度平台

### B 项目：Ecom-Watch-Agent-Agent

职责：

- 执行 refresh-prices
- 接收 trigger_source=scheduled
- 在 refresh run 中记录 trigger_source
- 保留 P13-D run 留痕与查询能力

B 不允许：

- 不实现调度器
- 不做 Celery Beat
- 不做主动推送
- 不做告警规则

## 四、B 项目要求

B 项目需要让 refresh-prices 支持 trigger_source。

推荐方式：

```json
{
  "trigger_source": "scheduled"
}
```

或 query 参数：

```text
POST /internal/monitor/refresh-prices?trigger_source=scheduled
```

固定取值：

```text
manual_feishu
scheduled
manual_api
```

P13-E 最小要求：

- A 定时任务调用时传 scheduled
- 飞书手动刷新仍为 manual_feishu 或既有默认值
- refresh run 中 trigger_source 正确保存

## 五、A 项目定时任务要求

新增 Celery task，建议命名：

```text
schedule_refresh_monitor_prices
```

建议文件：

```text
app/tasks/scheduler_tasks.py
```

逻辑：

```text
记录 P13E START 日志
调用 B refresh-prices，trigger_source=scheduled
记录 run_id / total / changed / failed
异常时记录错误
不主动发送飞书消息
```

## 六、Celery Beat 配置

在现有 Celery 配置中增加 beat_schedule。

建议：

```python
beat_schedule = {
    "refresh-monitor-prices-every-5-minutes": {
        "task": "app.tasks.scheduler_tasks.schedule_refresh_monitor_prices",
        "schedule": crontab(minute="*/5"),
    }
}
```

如项目当前 Celery task name 有既有命名规范，必须遵守现有规范，不要硬套。

## 七、日志要求

worker / beat 日志必须能看到：

```text
=== P13E SCHEDULE TRIGGER START ===
=== P13E CALL B REFRESH ===
=== P13E SCHEDULE RESULT === run_id=... total=... changed=... failed=...
```

失败时：

```text
=== P13E SCHEDULE FAILED === error=...
```

## 八、本轮允许做

B 项目允许：

1. refresh-prices 接收 trigger_source
2. refresh run 保存 trigger_source
3. 补 B 测试确认 scheduled 被写入 run
4. 保留 P13-D run 查询能力

A 项目允许：

1. 新增 scheduler task
2. 配置 Celery Beat
3. BServiceClient 支持传 trigger_source
4. 增加 A 测试
5. 更新 README / docs / AGENTS

## 九、本轮禁止做

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
- 不做价格图表
- 不做后台管理页面
- 不破坏 P13-A 刷新价格
- 不破坏 P13-B 价格历史
- 不破坏 P13-C 变化摘要
- 不破坏 P13-D run 查询
- 不破坏 P12 卡片交互
- 不混入 P13-F/G/H

## 十、推荐开发顺序

### P13-E.0：A 侧 Celery 现状锚定

先确认：

- Celery app 在哪里
- 现有 task 如何注册
- worker 启动方式
- beat 是否已有配置
- 是否已有 beat_schedule

### P13-E.1：B 支持 trigger_source

让 refresh-prices 支持 trigger_source=scheduled，并写入 run。

### P13-E.2：A 新增定时任务

新增 schedule_refresh_monitor_prices。

该任务只做：

```text
调用 B refresh-prices
记录日志
```

### P13-E.3：A 接入 Celery Beat

增加每 5 分钟调度。

### P13-E.4：测试与回归

必须回归：

- 手动刷新价格
- run_id 查询
- 价格历史查询
- 管理卡片价格字段
- P12 卡片交互

## 十一、通过标准

P13-E 通过条件：

- B 支持 trigger_source=scheduled
- B refresh run 正确保存 scheduled
- A 有 schedule_refresh_monitor_prices 任务
- Celery Beat 配置每 5 分钟触发
- 定时任务可手动调用测试
- 定时任务执行后生成 run_id
- run 可通过 P13-D 查询
- 手动刷新不退化
- P13-A/B/C/D 不退化
- P12 不退化
- A/B 分别测试通过
- A/B 分别提交

## 十二、提交边界

B 项目允许提交：

- refresh-prices trigger_source 适配
- schema / service / API / tests 相关最小改动

A 项目允许提交：

- scheduler task
- celery beat 配置
- BServiceClient trigger_source 适配
- P13-E 测试
- docs / README / AGENTS 阶段说明

禁止混入：

- P13-F 主动推送
- P13-G 失败重试
- P13-H 阈值提醒
- 无关重构