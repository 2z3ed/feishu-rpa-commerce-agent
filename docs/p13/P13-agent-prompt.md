# P13-F Agent 开发提示词

你现在接手的是 A/B 双仓开发任务。

当前唯一主线是：

P13-F：真实页面价格提取最小预演版

## 一、双仓说明

A 项目：

```text
feishu-rpa-commerce-agent
```

职责：

- 飞书入口
- 消息编排
- 老板交互
- 展示 B 返回的价格与来源

B 项目：

```text
Ecom-Watch-Agent-Agent
```

职责：

- monitor target 数据
- 价格刷新
- HTML 页面价格提取
- price_source 记录
- snapshot / run 留痕

本轮允许同时修改 A/B 两个仓库。

但必须遵守：

- B 负责真实页面价格提取
- A 不抓网页
- A 不解析 HTML
- A 不计算真实价格
- A 只展示 B 返回结果
- 失败时不能破坏刷新链路
- 两个仓库分别测试
- 两个仓库分别清点
- 提交顺序必须是：先 B，后 A

## 二、当前现实

P13-A 到 P13-E 已完成：

- 刷新价格
- 保存 current_price / last_price
- 计算变化
- 写入价格历史
- 写入 refresh run
- 定时刷新

但当前真实价格来源仍是：

```text
mock_price
```

P13-F 只做真实页面价格提取最小预演。

本轮不是反爬，不是代理池，不是浏览器渲染。

## 三、开始前必须先读

A 项目必须读：

1. AGENTS.md
2. README.md
3. docs/p13/p13-project-plan.md
4. docs/p13/P13-agent-prompt.md
5. app/services/feishu/cards/monitor_targets.py
6. tests/test_p13_a_monitor_price_card.py
7. tests/test_p10_b_query_integration.py

B 项目必须读：

1. README 或项目主说明
2. app/models/product.py
3. app/schemas/monitor_management.py
4. app/services/monitor_management_service.py
5. app/api/routes_internal_monitor.py
6. tests/test_monitor_management_api.py

如果 B 项目目录不存在或名称不匹配，先停止并回报，不要猜。

## 四、本轮唯一目标

实现：

```text
product_url
→ 请求 HTML
→ 提取价格
→ current_price 使用真实价格
→ price_source=html_extract_preview
```

提取失败时：

```text
fallback 到 mock_price 或 unknown
```

## 五、本轮验收样本

第一条真实验收样本：

```text
Hush Home® 深眠重力被
https://www.hushhome.com/tw/products/weighted-blanket
页面价格示例：HK$1,280.00
```

目标：

```text
current_price ≈ 1280.0
price_source = html_extract_preview
```

## 六、B 项目允许做

B 项目允许：

1. 新增 price probe service
2. 请求 HTML 页面
3. 使用正则提取常见价格格式
4. refresh_price 优先使用 html_extract_preview
5. 提取失败时 fallback
6. 保留 mock_price 作为兜底
7. 增加 B 测试

## 七、A 项目允许做

A 项目允许：

1. 必要时调整管理卡片展示 price_source
2. 必要时调整 A 测试
3. 更新 README / docs / AGENTS
4. 不新增复杂交互

## 八、本轮禁止做

禁止：

- 不做反爬
- 不做代理池
- 不做 Playwright
- 不做浏览器渲染
- 不做多站点完美适配
- 不做 SKU 规格选择
- 不做币种换算系统
- 不做价格告警
- 不做主动推送
- 不做定时策略调整
- 不做复杂采集失败治理
- 不破坏 P13-A/B/C/D/E
- 不破坏 P12 卡片交互
- 不混入 P13-G/H/I

## 九、价格提取最小规则

支持常见格式：

```text
HK$1,280.00
$1,280.00
USD $99.99
NT$1,280
¥1280
```

规则：

- 提取可信价格文本
- 去掉货币符号
- 去掉千分位逗号
- 转 float
- 保留 raw_text
- 可识别 HK$ 时 currency 可记录为 HKD，但不强制做完整币种系统

## 十、测试要求

B 项目至少测试：

1. HK$1,280.00 解析为 1280.0
2. 常见价格格式能解析
3. 无价格 HTML 返回失败结果
4. refresh_price 成功时 price_source=html_extract_preview
5. HTML 提取失败时 fallback mock_price
6. P13-A/B/C/D/E 刷新链路不退化

A 项目至少测试：

1. 管理卡片可展示 price_source=html_extract_preview
2. 未采集 / fallback 文案不退化
3. P12 / P13 回归不退化

## 十一、必须跑的检查

B 项目：

```bash
pytest -q tests/test_monitor_management_api.py
```

如新增 price probe 测试，也必须跑。

A 项目：

```bash
pytest -q tests/test_p10_b_query_integration.py
pytest -q tests/test_p13_a_monitor_price_card.py
bash scripts/p12_regression_check.sh
```

如新增 P13-F 测试，也必须跑。

## 十二、完成后回报格式

必须按 A/B 分开回报：

A. 先读了哪些文件  
B. B 项目当前 mock_price 生成链路锚定结果  
C. B 项目改了哪些文件  
D. B 项目 HTML price probe 如何设计  
E. B 项目 fallback 如何设计  
F. B 项目测试结果  
G. A 项目改了哪些文件  
H. A 项目如何展示 html_extract_preview  
I. A 项目测试结果  
J. 是否可以进入 A/B 联合实机验收  
K. 提交建议：B 先提交什么，A 后提交什么  

只允许使用简体中文。

不要只给计划。
不要只贴 diff。
不要混入 P13-G。