# P13-I 开发主线文档

## 阶段名称

P13-I：价格可信度与异常检测最小版

## 一、阶段背景

P13-F 已经让系统具备真实页面价格提取能力。

P13-G 已经让系统能记录采集状态和失败原因。

P13-H 已经让系统能对失败 / fallback / mock 对象进行手动重试。

现在系统已经能回答：

```text
是否采集成功？
失败原因是什么？
是否能重试？
```

但还缺少一个关键判断：

```text
这个价格值本身是否可信？
这个页面类型是否适合做价格监控？
这个价格变化是否异常？
```

例如：

```text
1280 → 15020
20 → 500
Amazon 榜单页提取到某个价格
文章页提取到价格
mock_price 连续变化
```

这些都不应该被系统当成稳定可信的业务价格。

所以 P13-I 只做：

价格可信度与异常检测最小版。

## 二、本轮唯一目标

只做：

```text
价格可信度 + 页面类型 + 异常检测 + 一句轻量建议
```

目标链路：

```text
刷新监控价格 / 重试价格采集
→ B 根据 price_source / probe_status / URL / page_type / delta 判断
→ B 写入诊断字段
→ A 管理卡片展示诊断字段
→ A 可查询异常对象 / 低可信对象 / 价格监控状态
```

## 三、A/B 双仓分工

### A 项目：feishu-rpa-commerce-agent

职责：

- 展示 B 返回的可信度与异常字段
- 查询异常对象
- 查询低可信对象
- 展示价格监控状态摘要
- 不重新计算可信度
- 不重新判断异常
- 不生成复杂决策建议

### B 项目：Ecom-Watch-Agent-Agent

职责：

- 判断页面类型
- 判断价格可信度
- 判断异常价格
- 生成轻量建议
- 写入或返回诊断字段
- 保留 P13-A 到 P13-H 既有链路

## 四、B 项目最小诊断字段

建议在 product / monitor target 上增加：

```text
price_confidence
price_page_type
price_anomaly_status
price_anomaly_reason
price_action_suggestion
```

字段语义：

### price_confidence

```text
high
medium
low
unknown
```

建议规则：

```text
html_extract_preview + success + product_detail → high
html_extract_preview + success + unknown page type → medium
html_extract_preview + success + listing_page/article_page → low
mock_price / fallback_mock / failed / unknown → low
```

### price_page_type

```text
product_detail
listing_page
search_page
article_page
mock_page
unknown
```

建议规则：

- URL 含 `/products/`、`/product/`、`/dp/` 可判为 product_detail
- URL 含 `/search`、`s?k=`、`keyword=` 可判为 search_page
- URL 含 `/bestsellers`、`/new-releases` 可判为 listing_page
- URL 含 `article`、`zhihu`、`vocus`、`post` 可判为 article_page
- URL 为 `mock://` 可判为 mock_page
- 其他为 unknown

### price_anomaly_status

```text
normal
suspected
unknown
```

最小规则：

```text
abs(price_delta_percent) >= 50 → suspected
abs(price_delta) >= 500 → suspected
current_price > 10000 → suspected
price_source=mock_price 且 price_changed=true → suspected
otherwise → normal
```

### price_anomaly_reason

示例：

```text
价格变化幅度超过 50%
价格变化金额超过 500
当前价格超过 10000，疑似误提取
mock_price 出现价格变化，不应作为真实价格判断
```

### price_action_suggestion

本轮只做一句轻量建议。

示例：

```text
建议优先人工复查该对象价格来源。
建议更换为商品详情页 URL。
建议先重试价格采集。
该价格可作为当前监控参考。
```

## 五、A 项目展示要求

### 管理卡片

“看看当前监控对象”中增加：

```text
可信度：high / medium / low
页面类型：product_detail / listing_page / article_page
异常状态：normal / suspected
异常原因：-
建议：该价格可作为当前监控参考
```

如果字段为空：

```text
可信度：unknown
页面类型：unknown
异常状态：unknown
```

### 查询命令

新增：

```text
查看价格异常对象
查看低可信价格对象
查看价格监控状态
价格监控概览
```

### 价格异常对象文案

```text
价格异常对象（共 2 个）：
1. XXX
   对象ID：9
   当前价格：15020.0
   上次价格：1280.0
   异常状态：suspected
   异常原因：当前价格超过 10000，疑似误提取
   建议：建议优先人工复查该对象价格来源
```

### 低可信对象文案

```text
低可信价格对象（共 5 个）：
1. XXX
   对象ID：10
   来源：mock_price
   可信度：low
   页面类型：search_page
   建议：建议更换为商品详情页 URL
```

### 价格监控状态文案

```text
价格监控状态

监控对象总数：13
高可信价格：3
中可信价格：2
低可信价格：8
异常价格：2
mock/fallback：6

建议：
- 优先复查 2 个异常价格对象
- 处理 8 个低可信对象
- mock/fallback 对象不建议用于价格决策
```

## 六、本轮允许做

B 项目允许：

1. 增加诊断字段
2. 页面类型判断
3. 可信度判断
4. 异常检测
5. 轻量建议生成
6. list / run detail 返回诊断字段
7. 增加 B 测试

A 项目允许：

1. 管理卡片展示诊断字段
2. 新增异常对象查询命令
3. 新增低可信对象查询命令
4. 新增价格监控状态命令
5. 增加 A 测试
6. 更新 README / docs / AGENTS

## 七、本轮禁止做

禁止：

- 不做完整决策建议系统
- 不做建议分级
- 不做处理优先级系统
- 不做阈值订阅
- 不做主动推送
- 不做复杂规则引擎
- 不做 LLM 自动判断
- 不做图表看板
- 不做后台页面
- 不做 Playwright
- 不做浏览器渲染
- 不做代理池
- 不做站点规则库
- 不做复杂页面解析系统
- 不破坏 P13-A/B/C/D/E/F/G/H
- 不破坏 P12 卡片交互
- 不混入 P13-J

## 八、推荐开发顺序

### P13-I.0：B 侧字段锚定

先确认当前 product/list/run item 中已有字段。

不要重复设计已有的 probe 字段。

### P13-I.1：B 增加诊断函数

建议新增轻量函数：

```text
classify_price_page_type(url)
evaluate_price_confidence(...)
detect_price_anomaly(...)
build_price_action_suggestion(...)
```

### P13-I.2：B 集成 refresh / retry

在 refresh_price 和 retry 结束后写入诊断字段。

### P13-I.3：A 展示字段

管理卡片展示诊断字段。

### P13-I.4：A 查询命令

新增异常 / 低可信 / 状态概览查询。

### P13-I.5：回归

必须回归：

- P13-H 重试
- P13-G 采集状态查询
- P13-F 真实价格提取
- P13-E 定时刷新
- P13-D run 查询
- P13-B 价格历史
- P12 卡片交互

## 九、通过标准

P13-I 通过条件：

- B 能输出 price_confidence
- B 能输出 price_page_type
- B 能输出 price_anomaly_status
- B 能输出 price_anomaly_reason
- B 能输出 price_action_suggestion
- A 管理卡片展示诊断字段
- A 可查询异常价格对象
- A 可查询低可信对象
- A 可查看价格监控状态
- P13-H 不退化
- P13-A/B/C/D/E/F/G 不退化
- P12 不退化
- A/B 分别测试通过
- A/B 分别提交

## 十、提交边界

B 项目允许提交：

- product / schema / service / tests 中与诊断字段有关的最小改动

A 项目允许提交：

- 卡片展示
- 查询命令
- P13-I 测试
- docs / README / AGENTS 阶段说明

禁止混入：

- P13-J 决策建议增强
- 主动通知
- 阈值订阅
- 无关重构