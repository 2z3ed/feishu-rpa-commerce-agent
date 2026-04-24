
---

【docs/p12/P12-agent-prompt.md】

```md
# P12-C Agent 开发提示词

你现在接手的是 feishu-rpa-commerce-agent 项目。

当前唯一主线是：

P12-C：监控对象管理卡片版

## 一、当前现实

P12-A 已完成：

- discovery 搜索结果卡片展示
- 卡片失败 fallback 文本

P12-B 已完成：

- 候选卡片“加入监控”按钮
- 点击按钮可加入监控
- 群聊中优先回群聊
- open_id 仅作为 fallback
- 文本“加入监控第 N 个”仍可用

本轮不是继续改候选卡片。

本轮只做：

把“看看当前监控对象”的成功回复升级为监控对象管理卡片。

## 二、开始前必须先读

1. docs/p12/p12-project-plan.md
2. docs/p12/P12-agent-prompt.md
3. docs/p12/p12-boss-demo-sop.md
4. docs/p12/p12-acceptance-checklist.md

如果文件不存在或不是 P12-C 口径，先停止并回报。

## 三、固定原则

A 项目仍是：

- 飞书入口层
- 消息编排层
- 老板交互层

B 项目仍是：

- 业务服务层

固定原则：

- 不合并 A / B
- A 调 B 继续按 Envelope 解包
- B 默认地址继续是 http://127.0.0.1:8005
- 不把 B 的业务逻辑搬进 A
- 不重写 P12-A / P12-B

## 四、本轮唯一目标

当用户发送：

```text
看看当前监控对象
成功时，优先返回飞书管理卡片。

卡片展示：

监控对象总数
对象名称
对象ID
状态 active / inactive
URL
最小操作按钮：暂停 / 恢复

如果现有 B 服务没有 pause / resume 能力，不允许硬造业务能力，必须回报并只完成展示卡片。

五、本轮允许做

只允许做：

新增 monitor target 管理卡片 builder
“看看当前监控对象”成功路径优先发卡片
卡片失败 fallback 文本
active 对象显示“暂停监控”
inactive 对象显示“恢复监控”
如果已有 pause / resume 能力，则接入按钮回调
成功/失败后补发老板可读文本
补最小测试
六、本轮禁止做

禁止：

不做删除按钮
不做批量管理
不做分页
不做搜索过滤
不做复杂卡片状态同步
不做 PostgreSQL
不新增业务动作
不重写 P12-A / P12-B
不破坏候选卡片加入监控按钮
不破坏文本命令
七、建议实现位置

优先查看：

app/services/feishu/cards/
app/services/feishu/client.py
app/services/feishu/longconn.py
app/tasks/ingress_tasks.py
app/graph/nodes/execute_action.py
app/clients/b_service_client.py
P12-B card action 相关测试

建议新增：

app/services/feishu/cards/monitor_targets.py
tests/test_p12_c_monitor_card.py
八、最小 payload

暂停：

{
  "action": "pause_monitor_target",
  "target_id": 7,
  "source": "monitor_list_card"
}

恢复：

{
  "action": "resume_monitor_target",
  "target_id": 7,
  "source": "monitor_list_card"
}
九、测试要求

至少覆盖：

monitor 管理卡片能构建
卡片包含对象名称、状态、ID、URL
active 对象显示暂停按钮
inactive 对象显示恢复按钮
不包含 delete 按钮
P12-B 的 add_from_candidate 仍可用
P10/P11/P12-B 测试不退化

必须跑：

pytest -q tests/test_p10_b_query_integration.py
pytest -q tests/test_p12_b_card_action.py
pytest -q tests/test_p12_c_monitor_card.py
十、完成后回报格式

A. 先读了哪些文件
B. 当前 monitor list 链路锚定结果
C. B 服务是否已有 pause / resume 能力
D. 本轮实际执行了哪些命令
E. 改了哪些文件
F. 管理卡片展示了哪些字段
G. 是否接入暂停 / 恢复按钮
H. 是否保留文本 fallback
I. 测试结果
J. 是否可以进入飞书实机验收

只允许使用简体中文。

不要只给计划。
不要只贴 diff。
不要继续做 P12-D。