# P13-C Agent 开发提示词

你现在接手的是 A/B 双仓开发任务。

当前唯一主线是：

P13-C：价格变化提醒最小闭环版

## 一、双仓说明

A 项目：

```text
feishu-rpa-commerce-agent
```

职责：

- 飞书入口
- 消息编排
- 老板交互
- 刷新结果提醒展示

B 项目：

```text
Ecom-Watch-Agent-Agent
```

职责：

- monitor target 数据
- 价格刷新
- 价格变化计算
- price snapshot 写入
- 刷新结果汇总

本轮允许同时修改 A/B 两个仓库。

但必须遵守：

- A 不吞 B
- A 不重新计算价格变化
- A 不保存价格历史
- B 负责刷新与变化汇总
- A 只消费 B 返回结果并做老板可读展示
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
- 对象ID / 第 N 个语义已统一

P13-C 只做刷新后的变化提醒摘要。

本轮不是阈值提醒，不是定时任务，不是主动推送。

## 三、开始前必须先读

A 项目必须读：

1. AGENTS.md
2. README.md
3. docs/p13/p13-project-plan.md
4. docs/p13/P13-agent-prompt.md
5. app/clients/b_service_client.py
6. app/graph/nodes/execute_action.py
7. app/graph/nodes/resolve_intent.py
8. tests/test_p13_a_monitor_price_card.py
9. tests/test_p10_b_query_integration.py

B 项目必须读：

1. README 或项目主说明
2. app/models/product.py
3. app/models/price_snapshot.py
4. app/schemas/monitor_management.py
5. app/services/monitor_management_service.py
6. app/api/routes_internal_monitor.py
7. tests/test_monitor_management_api.py

如果 B 项目目录不存在或名称不匹配，先停止并回报，不要猜。

## 四、本轮唯一目标

实现：

```text
刷新监控价格
→ B 返回本轮变化对象
→ A 飞书回复价格变化摘要
```

## 五、B 项目允许做

B 项目允许：

1. 增强 refresh-prices 返回结构
2. 返回 changed count
3. 返回 failed count
4. 返回 items / changed_items 列表
5. item 包含 product_id / product_name / current_price / last_price / price_delta / price_delta_percent / price_changed / price_source / last_checked_at
6. 增加 B 测试

## 六、A 项目允许做

A 项目允许：

1. 适配 B 的 refresh-prices 返回结构
2. 升级“刷新监控价格”回复文案
3. 展示变化对象前 5 条
4. 无变化时展示“本轮暂无价格变化”
5. 展示失败数
6. 增加 A 测试
7. 更新 README / docs / AGENTS

## 七、本轮禁止做

禁止：

- 不做阈值规则
- 不做价格低于多少提醒
- 不做定时任务
- 不做主动推送
- 不做订阅系统
- 不做邮件 / 短信通知
- 不做价格曲线图
- 不做图表卡片
- 不做复杂趋势分析
- 不做库存 / SKU
- 不新增数据表
- 不破坏 P13-A 刷新价格
- 不破坏 P13-B 价格历史
- 不破坏 P12 卡片交互
- 不混入 P13-D/E/F

## 八、A 文案要求

有变化时：

```text
监控价格已刷新。

本轮价格变化：3 个
1. Hush Home® 深眠重力被
   当前价：195
   上次价：190
   变化：上涨 5（+2.63%）

未变化：7 个
刷新失败：0 个
```

无变化时：

```text
监控价格已刷新。
本轮暂无价格变化。
成功刷新：10 个
失败：0 个
```

超过 5 条变化：

```text
还有 X 个价格变化对象未展示。
```

## 九、测试要求

B 项目至少测试：

1. refresh-prices 返回 changed count
2. refresh-prices 返回 changed items
3. items 包含价格变化字段
4. snapshot 写入不退化
5. refresh-price 单对象不退化

A 项目至少测试：

1. 有变化时格式化变化摘要
2. 无变化时格式化暂无变化
3. 超过 5 条时截断并提示剩余数量
4. 刷新失败数展示
5. P13-B 价格历史命令不退化
6. P12 回归不退化

## 十、必须跑的检查

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

如果新增 P13-C 测试，也必须跑。

## 十一、完成后回报格式

必须按 A/B 分开回报：

A. 先读了哪些文件  
B. B 项目 refresh-prices 当前返回结构锚定结果  
C. B 项目改了哪些文件  
D. B 项目变化汇总结构如何设计  
E. B 项目测试结果  
F. A 项目改了哪些文件  
G. A 项目刷新结果提醒文案如何设计  
H. A 项目如何限制展示前 5 条  
I. A 项目测试结果  
J. 是否可以进入 A/B 联合实机验收  
K. 提交建议：B 先提交什么，A 后提交什么  

只允许使用简体中文。

不要只给计划。
不要只贴 diff。
不要混入 P13-D。