# P13-A Agent 开发提示词

你现在接手的是 A/B 双仓开发任务。

当前唯一主线是：

P13-A：监控对象价格数据最小闭环版

## 一、双仓说明

A 项目：

```text
feishu-rpa-commerce-agent
```

职责：

- 飞书入口
- 消息编排
- 老板交互
- 卡片展示
- 调用 B 服务

B 项目：

```text
Ecom-Watch-Agent-Agent
```

职责：

- monitor target 数据
- 价格字段
- 价格刷新
- 价格变化计算
- 业务 API

本轮允许同时修改 A/B 两个仓库。

但必须遵守：

- A 不吞 B
- A 不写 B 的价格业务逻辑
- B 先实现价格数据能力
- A 再接飞书入口与展示
- 两个仓库分别测试
- 两个仓库分别清点
- 提交顺序必须是：先 B，后 A

## 二、当前现实

P12 已完成飞书卡片交互层：

- 搜索候选卡片
- 加入监控按钮
- 监控对象管理卡片
- 查看更多分页
- 暂停 / 恢复
- 删除二次确认
- P12 回归脚本

P13-A 进入监控数据层。

本轮不是继续做 UI 按钮。

本轮只做：

价格数据最小闭环。

## 三、开始前必须先读

A 项目必须读：

1. AGENTS.md
2. README.md
3. docs/p12/p12-closure-summary.md
4. app/services/feishu/cards/monitor_targets.py
5. app/services/feishu/longconn.py
6. app/tasks/ingress_tasks.py
7. app/clients/b_service_client.py

B 项目必须读：

1. README 或项目主说明
2. app/schemas/monitor_management.py
3. app/services/monitor_management_service.py
4. tests/test_monitor_management_api.py
5. monitor target 相关 API / route 文件

如果 B 项目目录不存在或名称不匹配，先停止并回报，不要猜。

## 四、本轮第一步：B 侧字段锚定

必须先检查 B 当前 monitor target 字段。

预计已有：

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

然后再设计最小价格字段：

```text
current_price
last_price
price_delta
price_delta_percent
price_changed
last_checked_at
price_source
```

不要直接上历史价格表。

## 五、本轮唯一目标

实现链路：

```text
监控对象
→ 刷新价格
→ 保存 current_price / last_price
→ 计算 price_delta / price_delta_percent
→ 飞书管理卡片展示价格信息
```

## 六、本轮允许做

B 项目允许：

1. monitor target schema 增加价格字段
2. monitor target list 返回价格字段
3. 新增最小价格刷新 service
4. 新增单对象刷新接口
5. 可选新增 active 对象批量刷新接口
6. 增加价格变化计算
7. 增加 B 测试

A 项目允许：

1. BServiceClient 增加价格刷新调用
2. 增加文本命令：刷新监控价格
3. 调 B 刷新价格
4. 回复老板可读汇总
5. 管理卡片展示价格字段
6. 增加 A 测试
7. 更新 README / docs / AGENTS

## 七、本轮禁止做

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
- 不破坏 P12 卡片交互层
- 不混入 P13-B/C/D/E

## 八、价格刷新最小规则

第一次刷新：

```text
last_price = null
current_price = new_price
price_delta = null
price_delta_percent = null
price_changed = false
last_checked_at = now
price_source = mock_price
```

第二次刷新：

```text
last_price = old current_price
current_price = new_price
price_delta = current_price - last_price
price_delta_percent = price_delta / last_price * 100
price_changed = price_delta != 0
last_checked_at = now
```

如果价格未知：

```text
current_price = null
price_source = null 或 unknown
```

A 卡片显示：

```text
当前价格：暂未采集
```

## 九、建议接口

B 单对象刷新：

```text
POST /internal/monitor/{id}/refresh-price
```

B 批量刷新 active 对象：

```text
POST /internal/monitor/refresh-prices
```

如果时间有限，必须至少完成单对象刷新。

如果 A 要支持“刷新监控价格”，建议 B 完成批量 active 刷新。

## 十、A 飞书命令

新增文本命令：

```text
刷新监控价格
刷新监控对象价格
刷新价格
```

返回示例：

```text
监控价格已刷新。
- 总对象数：8
- 成功刷新：6
- 价格变化：2
- 失败：0
```

## 十一、A 管理卡片展示

“看看当前监控对象”卡片中增加：

如果有价格：

```text
当前价格：199
上次价格：209
变化：下降 10（-4.78%）
最后检测：2026-04-25 17:30
来源：mock_price
```

如果无价格：

```text
当前价格：暂未采集
```

## 十二、测试要求

B 项目至少测试：

1. list 返回价格字段
2. 第一次刷新写入 current_price
3. 第二次刷新写入 last_price
4. price_delta / price_delta_percent 正确
5. 删除 / pause / resume 不退化

A 项目至少测试：

1. 管理卡片展示暂未采集
2. 管理卡片展示价格变化
3. 刷新监控价格命令能调用 B
4. P12-B/C/D/F 回归不退化

## 十三、完成后回报格式

必须按 A/B 分开回报：

A. 先读了哪些文件

B. B 项目字段锚定结果

C. B 项目改了哪些文件

D. B 项目价格刷新链路如何设计

E. B 项目测试结果

F. A 项目改了哪些文件

G. A 项目飞书命令如何设计

H. A 项目卡片价格展示如何设计

I. A 项目测试结果

J. 是否可以进入 A/B 联合实机验收

K. 提交建议：B 先提交什么，A 后提交什么

只允许使用简体中文。

不要只给计划。
不要只贴 diff。
不要混入 P13-B。