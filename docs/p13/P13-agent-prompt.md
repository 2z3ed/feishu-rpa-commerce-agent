# P13-D Agent 开发提示词

你现在接手的是 A/B 双仓开发任务。

当前唯一主线是：

P13-D：手动价格刷新任务留痕版

## 一、双仓说明

A 项目：

```text
feishu-rpa-commerce-agent
```

职责：

- 飞书入口
- 消息编排
- 老板交互
- 展示 refresh run id
- 查询 refresh run 详情

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

本轮允许同时修改 A/B 两个仓库。

但必须遵守：

- A 不吞 B
- A 不保存 refresh run
- A 不保存 refresh run items
- A 不重新计算刷新统计
- B 负责 run 留痕与详情查询
- A 只消费 B 返回结果并展示
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

P13-D 只做刷新任务留痕。

本轮不是定时任务，不是阈值提醒，不是调度系统。

## 三、开始前必须先读

A 项目必须读：

1. AGENTS.md
2. README.md
3. docs/p13/p13-project-plan.md
4. docs/p13/P13-agent-prompt.md
5. app/clients/b_service_client.py
6. app/graph/nodes/execute_action.py
7. app/graph/nodes/resolve_intent.py
8. tests/test_p10_b_query_integration.py
9. tests/test_p13_a_monitor_price_card.py

B 项目必须读：

1. README 或项目主说明
2. app/models/product.py
3. app/models/price_snapshot.py
4. app/schemas/monitor_management.py
5. app/services/monitor_management_service.py
6. app/api/routes_internal_monitor.py
7. app/core/db.py
8. tests/test_monitor_management_api.py

如果 B 项目目录不存在或名称不匹配，先停止并回报，不要猜。

## 四、本轮唯一目标

实现：

```text
刷新监控价格
→ 生成 refresh run
→ 保存刷新 summary 和 item 明细
→ A 展示 run_id
→ A 可查询 run 详情
```

## 五、B 项目允许做

B 项目允许：

1. 新增 price_refresh_runs 模型 / schema
2. 新增 price_refresh_run_items 模型 / schema
3. refresh-prices 创建 run_id
4. refresh-prices 保存 run summary
5. refresh-prices 保存 item 明细
6. 新增 GET /internal/monitor/price-refresh-runs/{run_id}
7. 增加 B 测试

## 六、A 项目允许做

A 项目允许：

1. BServiceClient 增加 get_price_refresh_run(run_id)
2. “刷新监控价格”回复展示 run_id
3. resolve_intent 增加 run 查询命令
4. execute_action 增加 run 详情展示
5. 增加 A 测试
6. 更新 README / docs / AGENTS

## 七、本轮禁止做

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

## 八、B 数据结构建议

price_refresh_runs：

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

price_refresh_run_items：

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

## 九、B API 要求

refresh-prices 返回新增：

```text
run_id
status
```

新增接口：

```text
GET /internal/monitor/price-refresh-runs/{run_id}
```

要求：

- run_id 不存在时返回 envelope error
- items 按对象顺序或 checked_at 稳定返回
- failed item 能带 error_message
- 不破坏 P13-C changed_items / items

## 十、A 命令要求

新增命令：

```text
查看刷新结果 PRR-20260425-xxxx
查看价格刷新批次 PRR-20260425-xxxx
查看刷新批次 PRR-20260425-xxxx
```

输出示例：

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

## 十一、测试要求

B 项目至少测试：

1. refresh-prices 返回 run_id
2. refresh-prices 保存 run summary
3. refresh-prices 保存 run items
4. run detail API 可查询
5. run_id 不存在时返回错误
6. P13-C items / changed_items 不退化

A 项目至少测试：

1. 刷新监控价格回复包含 run_id
2. run 查询命令可识别
3. run detail 有变化对象时格式化正确
4. run detail 无变化对象时格式化正确
5. run_id 不存在时返回老板可读错误
6. P13-B 价格历史不退化
7. P12 回归不退化

## 十二、必须跑的检查

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

如果新增 P13-D 测试，也必须跑。

## 十三、完成后回报格式

必须按 A/B 分开回报：

A. 先读了哪些文件  
B. B 项目 refresh run 存储锚定结果  
C. B 项目改了哪些文件  
D. B 项目 refresh run / items 如何设计  
E. B 项目 run detail API 如何设计  
F. B 项目测试结果  
G. A 项目改了哪些文件  
H. A 项目刷新回复如何展示 run_id  
I. A 项目 run 查询命令如何设计  
J. A 项目测试结果  
K. 是否可以进入 A/B 联合实机验收  
L. 提交建议：B 先提交什么，A 后提交什么  

只允许使用简体中文。

不要只给计划。
不要只贴 diff。
不要混入 P13-E。