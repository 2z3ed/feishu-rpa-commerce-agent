# P13-A 开发主线文档

## 阶段名称

P13-A：监控对象价格数据最小闭环版

## 一、阶段背景

P12 已经完成飞书卡片交互层：

- 搜索商品返回候选卡片
- 候选卡片支持加入监控
- 监控对象管理卡片支持暂停 / 恢复
- 超过 5 个对象支持查看更多
- 监控对象支持删除二次确认
- P12 已完成收口与回归脚本

现在继续深挖 P12 的搜索过滤、批量管理并不是最高优先级。

下一阶段应进入 P13：监控数据闭环。

P13-A 的目标是让 monitor target 从“URL 管理对象”升级为“有价格数据的监控对象”。

## 二、本轮唯一目标

只做：

监控对象价格数据最小闭环。

目标链路：

```text
监控对象
→ 手动刷新价格
→ 保存 current_price / last_price
→ 计算 price_delta / price_delta_percent
→ 飞书管理卡片展示价格信息
```

## 三、A/B 双仓分工

### A 项目：feishu-rpa-commerce-agent

职责：

- 飞书入口
- 文本命令解析
- 调用 B 项目价格刷新接口
- 飞书管理卡片展示价格字段
- 老板可读结果文案
- P12 卡片回归

A 不允许：

- 不直接实现价格采集业务
- 不直接保存价格数据
- 不绕过 B 写 monitor target
- 不把 B 的业务逻辑搬进 A

### B 项目：Ecom-Watch-Agent-Agent

职责：

- monitor target 价格字段
- 价格刷新能力
- 价格变化计算
- monitor target list 返回价格字段
- 价格相关 API / service / tests

B 是本轮核心改动仓库。

## 四、本轮第一步：字段锚定

开发前必须先确认 B 当前 monitor target 结构。

预计已有字段：

```text
product_id
product_name
product_url
source_type
is_active
status
created_at
updated_at
```

P13-A 最小新增字段建议：

```text
current_price
last_price
price_delta
price_delta_percent
price_changed
last_checked_at
price_source
```

字段说明：

- current_price：当前价格
- last_price：上一次价格
- price_delta：当前价格 - 上次价格
- price_delta_percent：价格变化百分比
- price_changed：价格是否变化
- last_checked_at：最后检测时间
- price_source：价格来源，如 mock_price / manual_probe / html_extract_preview

## 五、价格刷新能力

P13-A 不做复杂爬虫。

本轮允许三种最小来源：

```text
mock_price
manual_probe
html_extract_preview
```

推荐先实现 mock_price 或 manual_probe，证明闭环：

```text
读取价格
→ 保存价格
→ 比较变化
→ 返回结果
```

建议 B 提供最小接口：

```text
POST /internal/monitor/{id}/refresh-price
POST /internal/monitor/refresh-prices
```

如果只做一个，优先做单对象：

```text
POST /internal/monitor/{id}/refresh-price
```

再做批量 active 刷新：

```text
POST /internal/monitor/refresh-prices
```

但注意：

批量刷新只是遍历 active 对象，不做复杂采集治理。

## 六、A 项目飞书入口

P13-A 建议新增文本命令：

```text
刷新监控价格
刷新监控对象价格
刷新价格
```

行为：

```text
A 收到命令
→ 调 B 刷新 active 监控对象价格
→ B 返回刷新结果
→ A 回复老板可读汇总
```

汇总示例：

```text
监控价格已刷新。
- 总对象数：8
- 成功刷新：6
- 价格变化：2
- 失败：0
```

## 七、A 项目管理卡片展示

“看看当前监控对象”卡片中增加价格字段。

如果有价格：

```text
当前价格：199
上次价格：209
变化：下降 10（-4.78%）
最后检测：2026-04-25 17:30
来源：mock_price
```

如果没有价格：

```text
当前价格：暂未采集
```

注意：

- 不改 P12 的按钮主链
- 暂停 / 恢复 / 删除 / 查看更多都不能退化
- 价格展示只是附加信息

## 八、本轮允许做

允许：

1. B 增加 monitor target 价格字段
2. B 增加最小价格刷新 service
3. B 增加价格变化计算
4. B list 接口返回价格字段
5. B 增加最小价格刷新测试
6. A 增加刷新价格文本命令
7. A 增加 BServiceClient 调用
8. A 管理卡片展示价格字段
9. A 保留 P12 按钮能力
10. A/B 分别补测试

## 九、本轮禁止做

禁止：

- 不做定时任务
- 不做复杂爬虫
- 不做代理池
- 不做反爬
- 不做历史价格表
- 不做价格曲线
- 不做价格告警
- 不做库存监控
- 不做 SKU 规格矩阵
- 不做复杂数据库迁移
- 不做批量采集治理
- 不重写 P12 卡片交互层
- 不破坏 P12-B/C/D/F

## 十、推荐开发顺序

### P13-A.0：B 侧字段锚定

先检查 B 当前 schema / service / tests。

输出当前字段情况，不要直接盲改。

### P13-A.1：B 侧价格字段与 list 返回

让 monitor target 返回价格字段。

未采集时字段允许为 null。

### P13-A.2：B 侧最小刷新价格

实现：

```text
refresh_monitor_target_price(target_id)
```

至少支持 mock_price。

第二次刷新时：

```text
last_price = old current_price
current_price = new price
```

并计算：

```text
price_delta
price_delta_percent
price_changed
last_checked_at
```

### P13-A.3：B 侧刷新接口

优先实现：

```text
POST /internal/monitor/{id}/refresh-price
```

如果时间允许，再实现：

```text
POST /internal/monitor/refresh-prices
```

### P13-A.4：A 侧接入刷新命令

新增文本入口：

```text
刷新监控价格
```

A 调 B，返回老板可读汇总。

### P13-A.5：A 侧管理卡片展示价格

“看看当前监控对象”卡片展示价格字段。

### P13-A.6：回归

必须回归：

- P12-B 候选加入监控
- P12-C 暂停 / 恢复
- P12-D 查看更多
- P12-F 删除二次确认

## 十一、通过标准

P13-A 通过条件：

- B monitor target 有价格字段
- B list 返回价格字段
- B 至少一个对象能刷新 current_price
- 第二次刷新能记录 last_price
- B 能计算 price_delta / price_delta_percent
- A 能通过飞书命令触发刷新
- A 管理卡片展示价格信息
- 未采集对象显示“暂未采集”
- P12-B/C/D/F 不退化
- A/B 分别测试通过
- A/B 分别提交

## 十二、提交边界

B 项目允许提交：

- schema / service / API / tests 中与价格字段、刷新价格有关的最小改动

A 项目允许提交：

- BServiceClient 调用
- 飞书命令解析 / 执行
- 管理卡片展示
- P13-A 测试
- docs / README / AGENTS 相关阶段说明

禁止混入：

- P13-B 历史价格表
- P13-C 价格告警
- P13-D 库存 / SKU
- P13-E 定时采集
- 无关重构