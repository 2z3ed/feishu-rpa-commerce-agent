
---

# 3）docs/p12/P12-agent-prompt.md

```md
# P12-B Agent 开发提示词

你现在接手的是 feishu-rpa-commerce-agent 项目。

先不要发散，也不要误判当前主线。

当前不是继续补 P12-A，也不是做监控管理卡片。

当前唯一主线是：

P12-B：候选结果卡片按钮回调版

## 一、当前现实

P12-A 已完成并通过实机验收：

- 搜索商品可返回候选结果卡片
- 卡片展示 query / batch_id / 前 3~5 条候选
- “加入监控第 N 个”文本纳管链路仍然可用
- 搜索失败仍返回老板可读文本

本轮不是新增 discovery 能力。

本轮只做：

给候选结果卡片增加“加入监控”按钮，并把按钮回调接入现有 add-from-candidates 链路。

## 二、开始前必须先读

1. docs/p12/p12-project-plan.md
2. docs/p12/P12-agent-prompt.md
3. docs/p12/p12-boss-demo-sop.md
4. docs/p12/p12-acceptance-checklist.md

如果文件不存在或内容不是 P12-B，先停止并回报，不要自己编造阶段口径。

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
- 不重写 discovery 主链
- 不重写 add-from-candidates 主链

## 四、本轮唯一目标

搜索商品成功后，飞书候选卡片中每条候选旁边都有：

加入监控

点击按钮后：

1. A 接收飞书卡片 action 回调
2. A 解析按钮 payload
3. A 复用现有 add-from-candidates 能力
4. 成功后补发文本“已加入监控”
5. 失败后补发老板可读错误

## 五、本轮允许做

你只允许做：

1. 给候选卡片增加“加入监控”按钮
2. 增加最小 card action 回调入口
3. 设计并解析最小 payload
4. 回调后复用 add-from-candidates
5. 成功/失败后补发文本
6. 补最小测试
7. 更新 P12-B 文档中的执行结果

## 六、本轮禁止做

禁止：

- 不做监控对象管理卡片
- 不做 pause / resume / delete 按钮
- 不做分页
- 不做表单
- 不做复杂卡片更新状态
- 不做公网回调平台化
- 不切 PostgreSQL
- 不新增业务动作
- 不重构 P10 / P11 / P12-A 主链
- 不破坏“加入监控第 N 个”文本链路

## 七、建议实现位置

优先查看：

- app/services/feishu/cards/discovery_candidates.py
- app/services/feishu/client.py
- app/services/feishu/longconn.py
- app/tasks/ingress_tasks.py
- app/clients/b_service_client.py 或当前 B 调用封装
- app/graph/nodes/execute_action.py
- tests/test_p10_b_query_integration.py
- P12 相关测试文件

注意：

- 卡片 JSON 不要散写在业务节点里
- 回调入口不要直接堆一整条新业务链
- 能复用现有 add-from-candidates 就不要新建重复逻辑
- 结果反馈优先补发文本，不要先做复杂卡片更新

## 八、最小 payload

按钮 value 至少包含：

```json
{
  "action": "add_from_candidate",
  "batch_id": 1,
  "candidate_index": 1,
  "query": "重力毯"
}
要求：

candidate_index 从 1 开始
action 必须校验
batch_id 必须校验
candidate_index 必须校验
payload 不合法时返回老板可读错误
不允许静默失败
九、最小测试要求

至少覆盖：

候选卡片中存在按钮
按钮 value 包含 action / batch_id / candidate_index / query
非 add_from_candidate 的 action 不会误触发纳管
candidate_index 非法时返回错误
文本方式“加入监控第 N 个”不受影响

如现有测试框架不方便覆盖飞书 SDK 回调，至少补 service/helper 层测试。

十、完成后回报格式

你完成后必须按这个格式回报：

A. 先读了哪些文件
B. P12-B 回调入口锚定结果
C. 本轮实际执行了哪些命令
D. 改了哪些文件
E. 按钮 payload 如何设计
F. 是否复用旧 add-from-candidates 链路
G. 是否保留“加入监控第 N 个”
H. 测试结果
I. 是否可以进入飞书实机验收

只允许使用简体中文。

不要只贴 diff。

不要只讲计划。

必须给出实际结果。