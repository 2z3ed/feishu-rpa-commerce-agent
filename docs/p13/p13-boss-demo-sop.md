# P13-E 老板演示 SOP

## 一、演示目标

P13-E 的演示目标是证明：

系统可以通过 Celery Beat 自动定时刷新监控价格，并生成可查询的刷新批次 run_id。

本轮不是飞书主动推送，不是价格告警，也不是阈值规则。

本轮只演示：

```text
定时触发
→ 调用 B refresh-prices
→ 生成 run_id
→ 可查询 run detail
```

## 二、演示前提

需要启动：

A 项目：

```text
feishu-rpa-commerce-agent
```

B 项目：

```text
Ecom-Watch-Agent-Agent
```

需要确保：

- B 服务运行在 http://127.0.0.1:8005
- A worker 正常
- A Celery Beat 正常
- Redis / broker 正常
- 已有 active 监控对象
- P13-D run 查询可用

## 三、演示步骤

### 步骤 1：启动 worker

按项目当前命令启动 worker，例如：

```bash
celery -A app.workers.celery_app worker --loglevel=info
```

以仓库实际命令为准。

### 步骤 2：启动 beat

按项目当前命令启动 beat，例如：

```bash
celery -A app.workers.celery_app beat --loglevel=info
```

以仓库实际命令为准。

### 步骤 3：观察定时触发日志

等待定时任务触发。

worker 日志应出现：

```text
=== P13E SCHEDULE TRIGGER START ===
=== P13E CALL B REFRESH ===
=== P13E SCHEDULE RESULT === run_id=... total=... changed=... failed=...
```

### 步骤 4：查询 run detail

复制日志中的 run_id，在飞书发送：

```text
查看刷新结果 PRR-...
```

预期：

- 能查询到 run detail
- trigger_source 为 scheduled 或对应字段可验证
- total / refreshed / changed / failed 正常

### 步骤 5：回归手动刷新

飞书发送：

```text
刷新监控价格
```

预期：

- 手动刷新仍可用
- 仍返回 run_id
- 仍有变化摘要

### 步骤 6：回归 P13-B / P12

飞书发送：

```text
查看价格历史 7
看看当前监控对象
```

预期：

- 价格历史仍可用
- 管理卡片仍可用
- P12 按钮不退化

## 四、失败场景

可选：

1. B 服务关闭时定时触发
2. Redis / broker 未启动
3. beat 启动但 worker 未启动

预期：

- 日志可见失败原因
- 不主动乱发飞书消息
- 不影响手动命令

## 五、验收记录模板

```text
P13-E 实机验收记录

时间：
A commit：
B commit：
B 服务状态：
worker 状态：
beat 状态：

1. beat 是否启动：
结果：通过 / 未通过

2. worker 是否收到定时任务：
结果：通过 / 未通过

3. 定时刷新是否生成 run_id：
结果：通过 / 未通过
run_id：

4. 飞书查询 run detail：
结果：通过 / 未通过

5. 手动刷新回归：
结果：通过 / 未通过

6. P13-B / P12 回归：
结果：通过 / 未通过

最终结论：
P13-E 是否通过：
```