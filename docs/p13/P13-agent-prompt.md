# P13-H Agent 开发提示词

你现在接手的是 A/B 双仓开发任务。

当前唯一主线是：

P13-H：价格采集失败重试轻量版

## 一、双仓说明

A 项目：

```text
feishu-rpa-commerce-agent
```

职责：

- 飞书入口
- 消息编排
- 老板交互
- 触发重试
- 展示重试结果

B 项目：

```text
Ecom-Watch-Agent-Agent
```

职责：

- monitor target 数据
- HTML price probe
- probe 状态记录
- 失败对象重试
- 重试结果写回与留痕

本轮允许同时修改 A/B 两个仓库。

但必须遵守：

- B 负责执行重试
- A 只触发重试并展示结果
- A 不抓网页
- A 不解析 HTML
- A 不判断价格真假
- 不做自动重试队列
- 不做定时重试
- 不做主动通知
- 两个仓库分别测试
- 两个仓库分别清点
- 提交顺序必须是：先 B，后 A

## 二、当前现实

P13-G 已完成：

- B 能记录 price_probe_status
- B 能记录 price_probe_error
- B list / run detail 返回 probe 状态
- A 管理卡片展示采集状态
- A 能查询失败 / mock / 真实价格对象

P13-H 只做轻量重试。

本轮不是失败治理系统，不是重试队列，不是自动调度。

## 三、开始前必须先读

A 项目必须读：

1. AGENTS.md
2. README.md
3. docs/p13/p13-project-plan.md
4. docs/p13/P13-agent-prompt.md
5. app/clients/b_service_client.py
6. app/graph/nodes/resolve_intent.py
7. app/graph/nodes/execute_action.py
8. tests/test_p10_b_query_integration.py
9. tests/test_p13_a_monitor_price_card.py

B 项目必须读：

1. README 或项目主说明
2. app/services/price_probe_service.py
3. app/schemas/monitor_management.py
4. app/services/monitor_management_service.py
5. app/api/routes_internal_monitor.py
6. tests/test_monitor_management_api.py
7. tests/test_price_probe_service.py

如果 B 项目目录不存在或名称不匹配，先停止并回报，不要猜。

## 四、本轮唯一目标

实现：

```text
failed / fallback_mock / mock_price 对象
→ 手动触发重试
→ 成功则变为 success / html_extract_preview
→ 失败则更新 error / checked_at
→ A 返回重试摘要
```

## 五、B 项目允许做

B 项目允许：

1. 新增单对象重试接口
2. 新增批量重试接口
3. 复用现有 price probe
4. 重试成功写入真实价格
5. 重试失败更新 probe_error / checked_at
6. 增加 B 测试

建议接口：

```text
POST /internal/monitor/{id}/retry-price-probe
POST /internal/monitor/retry-price-probes
```

## 六、A 项目允许做

A 项目允许：

1. BServiceClient 增加 retry 调用
2. resolve_intent 增加重试命令
3. execute_action 展示重试结果
4. 增加 A 测试
5. 更新 README / docs / AGENTS

## 七、本轮禁止做

禁止：

- 不做自动重试队列
- 不做指数退避
- 不做定时重试
- 不做失败告警
- 不做主动推送
- 不做阈值提醒
- 不做代理池
- 不做 Playwright
- 不做浏览器渲染
- 不做站点适配规则库
- 不做人工修正价格
- 不做复杂失败报表
- 不破坏 P13-A/B/C/D/E/F/G
- 不破坏 P12 卡片交互
- 不混入 P13-I/J/K

## 八、命令要求

新增命令：

```text
重试价格采集
重试采集失败对象
重试mock价格对象
重试对象 7 价格采集
重试对象ID 7 价格采集
```

说明：

- 批量命令重试 failed / fallback_mock / mock_price 对象
- 单对象命令按对象ID
- 本轮不支持“第 N 个”列表序号，避免混淆

## 九、展示要求

批量重试：

```text
价格采集重试完成。

重试对象：5 个
成功转真实价格：2 个
仍失败：3 个
```

单对象成功：

```text
价格采集重试成功。
对象ID：6
当前价格：1280.0
来源：html_extract_preview
```

单对象失败：

```text
价格采集重试后仍未成功。
对象ID：9
状态：fallback_mock
原因：timeout
来源：mock_price
```

## 十、测试要求

B 项目至少测试：

1. 单对象重试成功
2. 单对象重试失败
3. 批量只选择 failed / fallback_mock / mock_price 对象
4. 批量重试成功计数
5. 批量重试失败计数
6. P13-G probe 状态不退化

A 项目至少测试：

1. 重试价格采集 intent
2. 重试mock价格对象 intent
3. 重试对象ID 7 价格采集 intent
4. 批量重试结果格式化
5. 单对象重试成功格式化
6. 单对象重试失败格式化
7. P12 / P13 回归不退化

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

如新增 P13-H 测试，也必须跑。

## 十二、完成后回报格式

必须按 A/B 分开回报：

A. 先读了哪些文件  
B. B 项目重试链路锚定结果  
C. B 项目改了哪些文件  
D. B 项目单对象重试如何设计  
E. B 项目批量重试如何设计  
F. B 项目测试结果  
G. A 项目改了哪些文件  
H. A 项目重试命令如何设计  
I. A 项目重试结果文案如何设计  
J. A 项目测试结果  
K. 是否可以进入 A/B 联合实机验收  
L. 提交建议：B 先提交什么，A 后提交什么  

只允许使用简体中文。

不要只给计划。
不要只贴 diff。
不要混入 P13-I。