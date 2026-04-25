# P13-C 开发主线文档

## 阶段名称

P13-C：价格变化提醒最小闭环版

## 一、阶段背景

P13-A 已完成价格数据最小闭环：

- monitor target 有 current_price / last_price
- 可以刷新价格
- 可以计算 price_delta / price_delta_percent
- 飞书管理卡片可以展示价格字段

P13-B 已完成价格历史留痕：

- 刷新价格时追加 price snapshot
- 可以查询最近价格历史
- 飞书可以查看某个监控对象的价格历史
- 对象ID与“第 N 个”语义已统一

现在下一步不是做定时任务，也不是做阈值规则，而是先把“手动刷新价格后的变化结果”讲清楚。

P13-C 只做：

刷新监控价格后，如果有对象价格变化，飞书返回老板可读的价格变化摘要。

## 二、本轮唯一目标

只做：

手动刷新后的价格变化提醒摘要。

目标链路：

```text
刷新监控价格
→ B 刷新 active 监控对象价格
→ B 写入 price snapshot
→ B 返回本轮刷新汇总与变化对象
→ A 格式化价格变化提醒
→ 飞书返回老板可读摘要
```

## 三、A/B 双仓分工

### A 项目：feishu-rpa-commerce-agent

职责：

- 接收“刷新监控价格”
- 调用 B 的 refresh-prices
- 读取 B 返回的 changed items
- 生成老板可读提醒文案
- 保留 P13-A / P13-B / P12 回归

A 不允许：

- 不重新计算价格变化
- 不直接写 price snapshots
- 不保存价格历史
- 不做阈值规则
- 不做主动推送

### B 项目：Ecom-Watch-Agent-Agent

职责：

- 刷新价格
- 计算 price_changed / price_delta / price_delta_percent
- 写入 price snapshots
- 返回 refreshed / changed / failed / items 等汇总信息

B 是本轮结果结构增强的核心。

## 四、B refresh-prices 返回结构要求

当前 B 已有：

```text
POST /internal/monitor/refresh-prices
```

P13-C 需要增强它的返回结果。

建议返回：

```json
{
  "total": 10,
  "refreshed": 10,
  "changed": 3,
  "failed": 0,
  "items": [
    {
      "product_id": 7,
      "product_name": "Hush Home® 深眠重力被",
      "product_url": "https://...",
      "current_price": 195,
      "last_price": 190,
      "price_delta": 5,
      "price_delta_percent": 2.63,
      "price_changed": true,
      "price_source": "mock_price",
      "last_checked_at": "2026-04-25T..."
    }
  ]
}
```

说明：

- items 可以返回本轮所有刷新对象，或至少返回变化对象
- A 只展示 price_changed=true 的前 5 条
- failed 必须可展示
- 不改变 P13-A 价格计算规则
- 不破坏 P13-B snapshot 写入

## 五、A 刷新结果提醒文案

有变化时：

```text
监控价格已刷新。

本轮价格变化：3 个
1. Hush Home® 深眠重力被
   当前价：195
   上次价：190
   变化：上涨 5（+2.63%）

2. XXX
   当前价：180
   上次价：200
   变化：下降 20（-10.00%）

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

变化超过 5 条时：

```text
还有 3 个价格变化对象未展示。
```

## 六、本轮允许做

B 项目允许：

1. 增强 refresh-prices 返回结构
2. 返回 changed count
3. 返回 changed items 或 items 列表
4. 保留 price snapshot 写入
5. 增加 B 测试

A 项目允许：

1. 升级“刷新监控价格”回复文案
2. 展示本轮变化摘要
3. 变化对象最多展示前 5 条
4. 无变化时展示“本轮暂无价格变化”
5. 增加 A 测试
6. 更新 README / docs / AGENTS

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
- 不做复杂采集治理
- 不新增数据表
- 不破坏 P13-A 刷新价格
- 不破坏 P13-B 价格历史
- 不破坏 P12 卡片交互层

## 八、推荐开发顺序

### P13-C.0：B refresh-prices 结构锚定

先检查当前 B 的 refresh-prices 返回结构。

确认当前是否已经有：

- total
- refreshed
- changed
- failed
- items

### P13-C.1：B 返回变化对象

增强 refresh-prices 返回：

- changed count
- failed count
- items 列表
- 每个 item 包含名称、价格、变化值、变化百分比、来源、检测时间

不要改变价格计算规则。

不要删除 snapshot 写入。

### P13-C.2：A 文案格式化

A 的“刷新监控价格”回复从简单汇总升级为变化摘要。

A 不重新计算变化，只读取 B 返回结果。

### P13-C.3：限制展示数量

A 默认只展示前 5 条变化对象。

超过 5 条时提示：

```text
还有 X 个价格变化对象未展示。
```

### P13-C.4：回归

必须回归：

- P13-A 管理卡片价格字段
- P13-B 价格历史查询
- P12-B 候选加入监控
- P12-C 暂停 / 恢复
- P12-D 查看更多
- P12-F 删除二次确认

## 九、通过标准

P13-C 通过条件：

- B refresh-prices 返回 changed count
- B refresh-prices 返回变化对象信息
- A 刷新监控价格回复显示变化摘要
- 有变化时展示前 5 条变化
- 无变化时展示暂无变化
- 失败数正常展示
- P13-A 不退化
- P13-B 不退化
- P12 不退化
- A/B 分别测试通过
- A/B 分别提交

## 十、提交边界

B 项目允许提交：

- refresh-prices 返回结构增强
- schema / service / API / tests 相关最小改动

A 项目允许提交：

- BServiceClient 适配
- execute_action 刷新价格文案增强
- P13-C 测试
- docs / README / AGENTS 阶段说明

禁止混入：

- P13-D 定时刷新
- P13-E 价格阈值提醒
- P13-F 采集失败治理
- 无关重构