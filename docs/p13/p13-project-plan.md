# P13-D 开发主线文档

## 阶段名称

P13-D：手动价格刷新任务留痕版

## 一、阶段背景

P13-A 已完成价格数据最小闭环：

- monitor target 有当前价格字段
- 可以刷新价格
- A 侧可以展示价格字段

P13-B 已完成价格历史留痕：

- 每次刷新可写入 price snapshot
- 可查询某个对象最近价格历史

P13-C 已完成价格变化摘要：

- 手动刷新后，A 可以展示本轮价格变化摘要
- B 可以返回 changed items

现在的问题是：

“刷新监控价格”仍然更像一次即时动作。

如果后续要做定时任务、失败治理、重试、告警，就必须先让每次刷新都有可追踪记录。

所以 P13-D 只做：

手动价格刷新任务留痕。

## 二、本轮唯一目标

只做：

每次执行“刷新监控价格”时，生成一个 refresh run，并保存本次刷新 summary 和明细。

目标链路：

```text
刷新监控价格
→ B 创建 refresh_run
→ B 刷新 active 监控对象
→ B 记录 total / refreshed / changed / failed
→ B 记录每个对象刷新结果
→ A 回复 run_id
→ 飞书可通过 run_id 查询本次刷新详情
```

## 三、A/B 双仓分工

### A 项目：feishu-rpa-commerce-agent

职责：

- 调用 B 的 refresh-prices
- 展示刷新批次 run_id
- 解析“查看刷新结果 xxx”命令
- 调用 B 查询 refresh run 详情
- 展示老板可读刷新详情

A 不允许：

- 不保存 refresh run
- 不保存 refresh run items
- 不重新计算刷新统计
- 不绕过 B 查询刷新明细
- 不做定时任务

### B 项目：Ecom-Watch-Agent-Agent

职责：

- 创建 refresh_run
- 保存 refresh_run summary
- 保存 refresh_run_items
- 提供 run_id 查询接口
- 保留 P13-A/B/C 现有刷新、历史、变化摘要能力

B 是本轮核心改动仓库。

## 四、B 项目数据结构建议

### price_refresh_runs

最小字段：

```text
id
run_id
status
total
refreshed
changed
failed
started_at
finished_at
duration_ms
trigger_source
```

字段说明：

- run_id：对外展示的刷新批次号，例如 PRR-20260425-xxxx
- status：succeeded / partial_failed / failed
- total：本次待刷新对象总数
- refreshed：成功刷新数量
- changed：价格变化数量
- failed：失败数量
- started_at：开始时间
- finished_at：结束时间
- duration_ms：耗时
- trigger_source：manual_feishu / manual_api / mock 等

### price_refresh_run_items

最小字段：

```text
id
run_id
product_id
product_name
status
current_price
last_price
price_delta
price_delta_percent
price_changed
price_source
error_message
checked_at
```

字段说明：

- status：succeeded / failed / skipped
- error_message：失败原因，可为空
- checked_at：对象检测时间

## 五、B 项目 API 要求

保留现有：

```text
POST /internal/monitor/refresh-prices
```

增强返回：

```json
{
  "run_id": "PRR-20260425-xxxx",
  "status": "succeeded",
  "total": 10,
  "refreshed": 10,
  "changed": 3,
  "failed": 0,
  "items": []
}
```

新增：

```text
GET /internal/monitor/price-refresh-runs/{run_id}
```

返回本次刷新详情：

```json
{
  "run_id": "PRR-20260425-xxxx",
  "status": "succeeded",
  "total": 10,
  "refreshed": 10,
  "changed": 3,
  "failed": 0,
  "started_at": "...",
  "finished_at": "...",
  "duration_ms": 1200,
  "items": []
}
```

本轮可不做 run 列表接口。

## 六、A 项目飞书命令

“刷新监控价格”回复增加刷新批次：

```text
监控价格已刷新。
刷新批次：PRR-20260425-xxxx

本轮价格变化：3 个
...
```

新增查询命令：

```text
查看刷新结果 PRR-20260425-xxxx
查看价格刷新批次 PRR-20260425-xxxx
查看刷新批次 PRR-20260425-xxxx
```

返回示例：

```text
价格刷新结果：PRR-20260425-xxxx
状态：succeeded
总对象数：10
成功刷新：10
价格变化：3
失败：0
耗时：1200ms

变化对象：
1. xxx
   当前价：199
   上次价：209
   变化：下降 10（-4.78%）
```

## 七、本轮允许做

B 项目允许：

1. 新增 refresh run 模型 / schema
2. 新增 refresh run item 模型 / schema
3. refresh-prices 创建 run
4. refresh-prices 保存 item 明细
5. 新增 run detail 查询 API
6. 增加 B 测试

A 项目允许：

1. BServiceClient 增加 run detail 查询
2. 刷新价格回复展示 run_id
3. resolve_intent 增加刷新结果查询命令
4. execute_action 增加刷新结果展示
5. 增加 A 测试
6. 更新 README / docs / AGENTS

## 八、本轮禁止做

禁止：

- 不做定时任务
- 不做主动推送
- 不做阈值告警
- 不做失败重试队列
- 不做复杂调度
- 不做价格图表
- 不做后台管理页面
- 不做大量历史报表
- 不做 run 列表页面
- 不破坏 P13-A 刷新价格
- 不破坏 P13-B 价格历史
- 不破坏 P13-C 变化摘要
- 不破坏 P12 卡片交互
- 不混入 P13-E/F/G

## 九、推荐开发顺序

### P13-D.0：B 侧刷新现状锚定

先确认当前 refresh-prices 返回结构，以及 P13-C 的 changed items 是否已稳定。

### P13-D.1：B 侧 refresh run 模型

新增 price_refresh_runs 与 price_refresh_run_items。

优先保持 SQLite 轻量初始化，不引入复杂迁移系统。

### P13-D.2：B 侧 refresh-prices 写 run

执行 refresh-prices 时：

- 创建 run
- 记录 started_at
- 刷新对象
- 写 item
- 更新 run summary
- 写 finished_at / duration_ms / status

### P13-D.3：B 侧 run 查询接口

实现：

```text
GET /internal/monitor/price-refresh-runs/{run_id}
```

### P13-D.4：A 侧刷新回复显示 run_id

在“刷新监控价格”回复中展示：

```text
刷新批次：PRR-...
```

### P13-D.5：A 侧 run 查询命令

新增：

```text
查看刷新结果 PRR-...
```

### P13-D.6：回归

必须回归：

- P13-A 当前价格
- P13-B 价格历史
- P13-C 变化摘要
- P12-B/C/D/F

## 十、通过标准

P13-D 通过条件：

- B 每次 refresh-prices 生成 run_id
- B 保存 run summary
- B 保存 run items
- B 可通过 run_id 查询详情
- A 刷新监控价格回复展示 run_id
- A 可通过 run_id 查询刷新详情
- P13-A 不退化
- P13-B 不退化
- P13-C 不退化
- P12 不退化
- A/B 分别测试通过
- A/B 分别提交

## 十一、提交边界

B 项目允许提交：

- refresh run 模型 / schema / service / API / tests
- db 初始化中必要建表逻辑

A 项目允许提交：

- BServiceClient run detail 查询
- resolve_intent / execute_action 刷新结果查询
- P13-D 测试
- docs / README / AGENTS 阶段说明

禁止混入：

- P13-E 定时刷新
- P13-F 阈值提醒
- P13-G 采集失败治理
- 无关重构