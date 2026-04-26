# P13-F 开发主线文档

## 阶段名称

P13-F：真实页面价格提取最小预演版

## 一、阶段背景

P13-A 到 P13-E 已经完成价格监控的数据链路：

- P13-A：价格字段与刷新闭环
- P13-B：价格历史记录
- P13-C：价格变化摘要
- P13-D：刷新 run 留痕
- P13-E：定时价格刷新

但当前价格来源仍然主要是：

```text
mock_price
```

这说明系统的数据链路已经通了，但还没有真正验证：

```text
商品 URL → 网页 HTML → 价格提取 → 写入 current_price
```

因此 P13-F 不做主动通知，也不做复杂爬虫，而是先做真实页面价格提取的最小预演。

## 二、本轮唯一目标

只做：

真实页面价格提取最小预演。

目标链路：

```text
读取 monitor target.product_url
→ 请求页面 HTML
→ 尝试提取价格
→ 成功：写入 current_price，price_source=html_extract_preview
→ 失败：fallback 到 mock_price 或 unknown
→ 保持 price snapshot / refresh run / 定时刷新链路不退化
```

## 三、A/B 双仓分工

### A 项目：feishu-rpa-commerce-agent

职责：

- 保留飞书入口
- 保留刷新监控价格命令
- 保留管理卡片展示
- 展示 B 返回的 current_price / price_source
- 不抓网页
- 不解析 HTML
- 不计算真实价格

### B 项目：Ecom-Watch-Agent-Agent

职责：

- 请求 product_url
- 提取 HTML 中的价格
- 决定 price_source
- 写入 current_price / last_price
- 写入 price snapshot
- 写入 refresh run / run item
- 提供测试覆盖

B 是本轮核心改动仓库。

## 四、最小验收样本

本轮第一条真实验收样本：

```text
商品：Hush Home® 深眠重力被
URL：https://www.hushhome.com/tw/products/weighted-blanket
页面价格示例：HK$1,280.00
```

最低期望：

```text
current_price = 1280.0
price_source = html_extract_preview
```

如果页面结构变化导致无法提取：

- 不允许整个刷新任务失败
- 必须返回可观测失败原因
- 可以 fallback 到 mock_price 或 unknown

## 五、B 项目价格提取设计

建议新增轻量模块：

```text
app/services/price_probe_service.py
```

或在 monitor_management_service.py 中保持最小函数，但建议独立模块，避免主 service 继续膨胀。

最小函数：

```text
probe_product_price(product_url) -> PriceProbeResult
```

返回字段：

```text
price
currency
price_source
raw_text
error_message
```

最小来源：

```text
html_extract_preview
```

fallback 来源：

```text
mock_price
unknown
```

## 六、HTML 提取规则

P13-F 不做复杂爬虫。

允许使用：

- requests / httpx
- 简单 HTML 文本正则
- 常见价格格式正则

建议识别：

```text
HK$1,280.00
$1,280.00
USD $99.99
NT$1,280
¥1280
```

最小规则：

- 提取第一个可信价格
- 去掉货币符号
- 去掉千分位逗号
- 转成 float
- raw_text 保留原始命中文本

## 七、refresh_price 集成

P13-F 中 refresh_price 应变为：

```text
如果 product_url 可访问并提取成功：
    使用 html_extract_preview 价格
否则：
    fallback 到 mock_price 或 unknown
```

注意：

- 不改变 P13-A 的 last_price/current_price 规则
- 不破坏 P13-B snapshot
- 不破坏 P13-C changed_items
- 不破坏 P13-D run item
- 不破坏 P13-E scheduled trigger

## 八、A 项目展示要求

A 侧管理卡片已有 price_source 展示。

P13-F 只要求：

- 当 B 返回 price_source=html_extract_preview 时，A 能正常展示
- 未提取时仍显示已有 fallback 文案
- 不新增复杂 UI

管理卡片示例：

```text
当前价格：1280.0
来源：html_extract_preview
```

如果 B 返回 currency，可选展示：

```text
币种：HKD
```

但本轮不强制做币种系统。

## 九、本轮允许做

B 项目允许：

1. 新增轻量价格提取 service
2. 请求 HTML 页面
3. 正则提取价格
4. refresh_price 优先使用 html_extract_preview
5. 失败时 fallback
6. 记录 price_source
7. 补 B 测试

A 项目允许：

1. 必要时调整卡片展示 price_source
2. 必要时调整测试期望
3. 更新 README / docs / AGENTS
4. 不新增复杂交互

## 十、本轮禁止做

禁止：

- 不做反爬
- 不做代理池
- 不做浏览器渲染
- 不做 Playwright
- 不做多站点完美适配
- 不做 SKU 规格选择
- 不做币种换算系统
- 不做价格告警
- 不做主动推送
- 不做定时策略调整
- 不做复杂错误治理
- 不新增历史价格之外的新数据体系
- 不破坏 P13-A/B/C/D/E
- 不破坏 P12 卡片交互

## 十一、推荐开发顺序

### P13-F.0：B 侧 refresh_price 当前锚定

先确认当前 refresh_price 如何生成 mock_price。

明确当前：

- mock_price 生成规则
- current_price / last_price 更新位置
- snapshot 写入位置
- run item 写入位置

### P13-F.1：新增 price probe

实现最小 HTML 价格提取。

优先可测试，不追求覆盖所有站点。

### P13-F.2：接入 refresh_price

refresh_price 优先调用 price probe。

成功：

```text
price_source=html_extract_preview
```

失败：

```text
fallback mock_price 或 unknown
```

### P13-F.3：测试 Hush Home 样本

使用 mock HTML 或 fixture 测试：

```text
HK$1,280.00 -> 1280.0
```

如允许联网实测，再做手动验收。

### P13-F.4：A 侧展示回归

确认 A 管理卡片展示：

```text
来源：html_extract_preview
```

### P13-F.5：回归

必须回归：

- P13-A 刷新价格
- P13-B 价格历史
- P13-C 变化摘要
- P13-D run 查询
- P13-E 定时刷新
- P12 卡片交互

## 十二、通过标准

P13-F 通过条件：

- B 能从至少一个 HTML 样本提取价格
- Hush Home 样本 HK$1,280.00 能解析为 1280.0
- 成功时 price_source=html_extract_preview
- 提取失败时刷新链路不崩
- fallback 可用
- A 管理卡片能展示 html_extract_preview
- P13-A/B/C/D/E 不退化
- P12 不退化
- A/B 分别测试通过
- A/B 分别提交

## 十三、提交边界

B 项目允许提交：

- price probe service
- monitor refresh 集成
- schema 如需补充 source/currency/raw 字段
- tests

A 项目允许提交：

- 管理卡片 price_source 展示微调
- docs / README / AGENTS 阶段说明
- tests

禁止混入：

- P13-G 主动通知
- P13-H 阈值提醒
- P13-I 采集失败治理
- 无关重构