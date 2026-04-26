# P13-G Agent 开发提示词

你现在接手的是 A/B 双仓开发任务。

当前唯一主线是：

P13-G：价格采集失败治理轻量版

## 一、双仓说明

A 项目：

```text
feishu-rpa-commerce-agent
```

职责：

- 飞书入口
- 消息编排
- 老板交互
- 展示 B 返回的采集状态
- 查询 failed / fallback / true html 对象

B 项目：

```text
Ecom-Watch-Agent-Agent
```

职责：

- monitor target 数据
- HTML price probe
- probe 状态记录
- probe 错误原因记录
- run item 采集状态留痕

本轮允许同时修改 A/B 两个仓库。

但必须遵守：

- B 负责记录 probe 状态
- A 不抓网页
- A 不解析 HTML
- A 不判断价格真假
- A 只展示 B 返回结果
- 不做主动通知
- 不做失败重试队列
- 两个仓库分别测试
- 两个仓库分别清点
- 提交顺序必须是：先 B，后 A

## 二、当前现实

P13-F 已完成：

- B 支持 html_extract_preview
- Hush Home 可提取 1280.0
- 提取失败 fallback mock_price
- 批量刷新不会因单个 URL 超时拖垮

但现在还缺：

- 哪些对象真实采集成功
- 哪些对象 fallback
- 哪些对象失败
- 失败原因是什么
- run detail 中能否追踪这些状态

P13-G 只做采集失败治理轻量版。

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
probe 成功 / fallback / 失败
→ B 记录状态和原因
→ B list 与 run detail 返回状态
→ A 展示和查询采集状态
```

## 五、B 项目允许做

B 项目允许：

1. 增加 price_probe_status
2. 增加 price_probe_error
3. 增加 price_probe_checked_at
4. 可选增加 price_probe_raw_text
5. refresh_price 写入 probe 状态
6. refresh run item 写入 probe 状态
7. list / run detail 返回 probe 状态
8. 增加 B 测试

## 六、A 项目允许做

A 项目允许：

1. 管理卡片展示采集状态
2. 展示失败原因
3. 新增命令：查看价格采集失败
4. 新增命令：查看mock价格对象
5. 新增命令：查看真实价格对象
6. 增加 A 测试
7. 更新 README / docs / AGENTS

## 七、本轮禁止做

禁止：

- 不做主动推送
- 不做价格告警
- 不做阈值规则
- 不做自动重试
- 不做失败重试队列
- 不做 Playwright
- 不做浏览器渲染
- 不做代理池
- 不做站点适配规则库
- 不做人工修正价格
- 不做复杂失败报表
- 不破坏 P13-A/B/C/D/E/F
- 不破坏 P12 卡片交互
- 不混入 P13-H/I/J

## 八、状态语义

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

- success：真实网页价格提取成功
- fallback_mock：真实提取失败，但 mock_price 兜底成功
- failed：无可用价格
- unknown：未采集或未知

## 九、A 查询命令要求

新增：

```text
查看价格采集失败
查看采集失败对象
查看mock价格对象
查看真实价格对象
```

查询逻辑：

- 失败对象：status in failed / fallback_mock
- mock 对象：price_source=mock_price 或 status=fallback_mock
- 真实对象：price_source=html_extract_preview 或 status=success

输出最多展示前 10 条。

超过 10 条：

```text
还有 X 个对象未展示。
```

## 十、测试要求

B 项目至少测试：

1. probe 成功写 success
2. fallback 写 fallback_mock
3. no_price_found 写失败原因
4. monitor list 返回 probe 状态
5. run detail 返回 probe 状态
6. P13-F Hush Home 样本不退化
7. refresh-prices 不退化

A 项目至少测试：

1. 管理卡片展示 success
2. 管理卡片展示 fallback_mock + error
3. 查看价格采集失败
4. 查看mock价格对象
5. 查看真实价格对象
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

如新增 P13-G 测试，也必须跑。

## 十二、完成后回报格式

必须按 A/B 分开回报：

A. 先读了哪些文件  
B. B 项目 probe 信息锚定结果  
C. B 项目改了哪些文件  
D. B 项目 probe 状态如何写入 product / run item  
E. B 项目 list / run detail 如何返回 probe 状态  
F. B 项目测试结果  
G. A 项目改了哪些文件  
H. A 项目管理卡片如何展示采集状态  
I. A 项目查询命令如何设计  
J. A 项目测试结果  
K. 是否可以进入 A/B 联合实机验收  
L. 提交建议：B 先提交什么，A 后提交什么  

只允许使用简体中文。

不要只给计划。
不要只贴 diff。
不要混入 P13-H。