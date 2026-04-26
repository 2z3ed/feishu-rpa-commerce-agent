# P13-I Agent 开发提示词

你现在接手的是 A/B 双仓开发任务。

当前唯一主线是：

P13-I：价格可信度与异常检测最小版

## 一、双仓说明

A 项目：

```text
feishu-rpa-commerce-agent
```

职责：

- 飞书入口
- 消息编排
- 老板交互
- 展示 B 返回的可信度 / 页面类型 / 异常状态
- 查询异常对象与低可信对象

B 项目：

```text
Ecom-Watch-Agent-Agent
```

职责：

- monitor target 数据
- price probe 结果
- 页面类型识别
- 价格可信度判断
- 异常检测
- 轻量建议字段

本轮允许同时修改 A/B 两个仓库。

但必须遵守：

- B 负责判断可信度与异常
- A 不重新计算可信度
- A 不重新判断异常
- A 只展示 B 返回结果
- 决策建议只做一句轻量建议
- 不做完整决策建议系统
- 不做复杂规则引擎
- 两个仓库分别测试
- 两个仓库分别清点
- 提交顺序必须是：先 B，后 A

## 二、当前现实

P13-H 已完成：

- B 能对失败 / fallback / mock 对象重试
- A 能触发重试价格采集
- P13-G 采集状态治理不退化

P13-I 只做可信度与异常检测最小版。

## 三、开始前必须先读

A 项目必须读：

1. AGENTS.md
2. README.md
3. docs/p13/p13-project-plan.md
4. docs/p13/P13-agent-prompt.md
5. app/services/feishu/cards/monitor_targets.py
6. app/clients/b_service_client.py
7. app/graph/nodes/resolve_intent.py
8. app/graph/nodes/execute_action.py
9. tests/test_p10_b_query_integration.py
10. tests/test_p13_a_monitor_price_card.py

B 项目必须读：

1. README 或项目主说明
2. app/models/product.py
3. app/services/price_probe_service.py
4. app/schemas/monitor_management.py
5. app/services/monitor_management_service.py
6. app/api/routes_internal_monitor.py
7. tests/test_monitor_management_api.py
8. tests/test_price_probe_service.py

如果 B 项目目录不存在或名称不匹配，先停止并回报，不要猜。

## 四、本轮唯一目标

实现：

```text
price_confidence
price_page_type
price_anomaly_status
price_anomaly_reason
price_action_suggestion
```

并让 A 可展示和查询。

## 五、B 项目允许做

B 项目允许：

1. 增加 price_confidence
2. 增加 price_page_type
3. 增加 price_anomaly_status
4. 增加 price_anomaly_reason
5. 增加 price_action_suggestion
6. refresh / retry 后写入诊断字段
7. list / run detail 返回诊断字段
8. 增加 B 测试

## 六、A 项目允许做

A 项目允许：

1. 管理卡片展示诊断字段
2. 新增“查看价格异常对象”
3. 新增“查看低可信价格对象”
4. 新增“查看价格监控状态”
5. 新增“价格监控概览”
6. 增加 A 测试
7. 更新 README / docs / AGENTS

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
- 不破坏 P13-A/B/C/D/E/F/G/H
- 不破坏 P12 卡片交互
- 不混入 P13-J

## 八、规则要求

### 页面类型

```text
product_detail
listing_page
search_page
article_page
mock_page
unknown
```

### 可信度

```text
high
medium
low
unknown
```

### 异常状态

```text
normal
suspected
unknown
```

异常最小规则：

```text
abs(price_delta_percent) >= 50
abs(price_delta) >= 500
current_price > 10000
price_source=mock_price 且 price_changed=true
```

## 九、A 查询命令要求

新增：

```text
查看价格异常对象
查看低可信价格对象
查看价格监控状态
价格监控概览
```

结果最多展示前 10 条。

超过 10 条：

```text
还有 X 个对象未展示。
```

## 十、测试要求

B 项目至少测试：

1. product_detail + html success -> high
2. listing/search/article -> low
3. mock/fallback -> low
4. 大幅涨跌 -> suspected
5. current_price > 10000 -> suspected
6. 诊断字段在 list 返回
7. 诊断字段在 run detail 返回
8. P13-H 重试后诊断字段更新

A 项目至少测试：

1. 管理卡片展示可信度
2. 查看价格异常对象
3. 查看低可信价格对象
4. 查看价格监控状态
5. P13-H 重试命令不退化
6. P12 / P13 回归不退化

## 十一、必须跑的检查

B 项目：

```bash
pytest -q tests/test_monitor_management_api.py
pytest -q tests/test_price_probe_service.py
```

A 项目：

```bash
pytest -q tests/test_p10_b_query_integration.py
pytest -q tests/test_p13_a_monitor_price_card.py
bash scripts/p12_regression_check.sh
```

如新增 P13-I 测试，也必须跑。

## 十二、完成后回报格式

必须按 A/B 分开回报：

A. 先读了哪些文件  
B. B 项目诊断字段锚定结果  
C. B 项目改了哪些文件  
D. B 项目页面类型如何判断  
E. B 项目可信度如何判断  
F. B 项目异常检测如何判断  
G. B 项目测试结果  
H. A 项目改了哪些文件  
I. A 项目管理卡片如何展示诊断字段  
J. A 项目查询命令如何设计  
K. A 项目测试结果  
L. 是否可以进入 A/B 联合实机验收  
M. 提交建议：B 先提交什么，A 后提交什么  

只允许使用简体中文。

不要只给计划。
不要只贴 diff。
不要混入 P13-J。