# P13-G 开发主线文档

## 阶段名称

P13-G：价格采集失败治理轻量版

## 一、阶段背景

P13-F 已经完成真实页面价格提取最小预演：

- B 侧支持 html_extract_preview
- Hush Home 样本可提取 1280.0
- 提取失败可 fallback 到 mock_price
- 批量刷新通过 timeout / budget / fallback 避免拖垮整批刷新

但真实网页价格采集天然不稳定。

如果后续要做主动通知、价格告警、阈值规则，就必须先知道：

```text
当前价格到底来自真实页面，还是 fallback？
失败原因是什么？
哪些对象仍然没有真实价格？
```

所以 P13-G 只做一件事：

采集状态与失败原因治理。

## 二、本轮唯一目标

只做：

记录、返回并展示价格采集状态。

目标链路：

```text
刷新监控价格
→ B 尝试 html price probe
→ 成功：price_probe_status=success，price_source=html_extract_preview
→ 失败 fallback：price_probe_status=fallback_mock，price_probe_error=timeout/no_price_found/...
→ 完全失败：price_probe_status=failed 或 unknown
→ A 管理卡片展示采集状态
→ A 可查询采集失败 / mock / 真实价格对象
```

## 三、A/B 双仓分工

### A 项目：feishu-rpa-commerce-agent

职责：

- 展示 B 返回的采集状态
- 展示采集失败原因
- 提供简单查询命令
- 不抓网页
- 不解析 HTML
- 不判断价格真假
- 不做主动通知

### B 项目：Ecom-Watch-Agent-Agent

职责：

- 在 monitor target 上记录 probe 状态
- 在 run item 中记录 probe 状态
- 返回采集状态字段
- 保留 P13-F 的真实提取与 fallback
- 保留 P13-A/B/C/D/E 链路

## 四、B 项目最小字段

建议在 product / monitor target 上增加：

```text
price_probe_status
price_probe_error
price_probe_checked_at
price_probe_raw_text
```

最低必须有：

```text
price_probe_status
price_probe_error
price_probe_checked_at
```

建议状态值：

```text
success
fallback_mock
failed
unknown
```

建议错误值：

```text
timeout
no_price_found
http_error
parse_error
budget_exceeded
unknown
```

说明：

- success：真实页面提取成功
- fallback_mock：真实提取失败，但 mock_price 兜底成功
- failed：没有可用价格
- unknown：状态未知或未采集

## 五、B API 返回要求

现有列表接口：

```text
GET /internal/monitor/targets
```

需要返回：

```text
price_probe_status
price_probe_error
price_probe_checked_at
price_probe_raw_text
```

现有 run detail：

```text
GET /internal/monitor/price-refresh-runs/{run_id}
```

run items 中需要返回：

```text
price_probe_status
price_probe_error
```

如有 raw_text，也可返回：

```text
price_probe_raw_text
```

## 六、A 项目展示要求

### 管理卡片

“看看当前监控对象”中增加：

成功时：

```text
采集状态：success
来源：html_extract_preview
```

fallback 时：

```text
采集状态：fallback_mock
采集原因：timeout
来源：mock_price
```

失败时：

```text
采集状态：failed
采集原因：no_price_found
来源：unknown
```

### 查询命令

新增文本命令：

```text
查看价格采集失败
查看采集失败对象
查看mock价格对象
查看真实价格对象
```

返回示例：

```text
价格采集失败对象（共 3 个）：

1. XXX
   对象ID：8
   来源：mock_price
   状态：fallback_mock
   原因：timeout

2. XXX
   对象ID：12
   来源：unknown
   状态：failed
   原因：no_price_found
```

真实价格对象：

```text
真实价格对象（共 5 个）：
1. Hush Home® 深眠重力被
   对象ID：6
   当前价格：1280.0
   来源：html_extract_preview
```

## 七、本轮允许做

B 项目允许：

1. 增加 probe 状态字段
2. refresh_price 写入 probe 状态
3. run item 写入 probe 状态
4. list 返回 probe 状态
5. run detail 返回 probe 状态
6. 增加 B 测试

A 项目允许：

1. 管理卡片展示采集状态
2. 新增采集状态查询命令
3. BServiceClient 复用 monitor targets list
4. execute_action 增加查询结果格式化
5. 增加 A 测试
6. 更新 README / docs / AGENTS

## 八、本轮禁止做

禁止：

- 不做主动推送
- 不做价格告警
- 不做阈值规则
- 不做自动重试
- 不做失败重试队列
- 不做复杂采集失败治理系统
- 不做 Playwright
- 不做浏览器渲染
- 不做代理池
- 不做站点适配规则库
- 不做人工修正价格
- 不做白名单 / 黑名单配置
- 不做复杂失败报表
- 不破坏 P13-A/B/C/D/E/F
- 不破坏 P12 卡片交互
- 不混入 P13-H/I/J

## 九、推荐开发顺序

### P13-G.0：B 侧 probe 信息锚定

先检查 P13-F 是否已在 raw_payload 中保存 probe 信息。

如果已有：

- 尽量复用
- 不重复设计

如果没有：

- 增加最小字段

### P13-G.1：B 侧字段与返回

让 product / monitor target 返回：

```text
price_probe_status
price_probe_error
price_probe_checked_at
```

可选：

```text
price_probe_raw_text
```

### P13-G.2：B 侧 run item 扩展

让 refresh run item 也记录 probe 状态，方便追溯某次刷新采集情况。

### P13-G.3：A 管理卡片展示

“看看当前监控对象”中增加采集状态和失败原因。

### P13-G.4：A 查询命令

新增：

```text
查看价格采集失败
查看mock价格对象
查看真实价格对象
```

本轮先做文本结果，不做新卡片。

### P13-G.5：回归

必须回归：

- P13-F Hush Home 提取
- P13-E 定时刷新
- P13-D run 查询
- P13-B 价格历史
- P13-C 变化摘要
- P12 卡片交互

## 十、通过标准

P13-G 通过条件：

- B 能记录 price_probe_status
- B 能记录 price_probe_error
- B 能记录 price_probe_checked_at
- B list 返回 probe 状态
- B run detail 返回 probe 状态
- A 管理卡片展示采集状态
- A 查询 failed / fallback / true html 对象可用
- P13-F 真实价格提取不退化
- P13-E 定时刷新不退化
- P13-A/B/C/D 不退化
- P12 不退化
- A/B 分别测试通过
- A/B 分别提交

## 十一、提交边界

B 项目允许提交：

- product / schema / service / run item / tests 中与 probe 状态有关的最小改动

A 项目允许提交：

- 卡片展示采集状态
- 查询命令
- P13-G 测试
- docs / README / AGENTS 阶段说明

禁止混入：

- P13-H 主动通知
- P13-I 阈值提醒
- P13-J 采集重试治理
- 无关重构