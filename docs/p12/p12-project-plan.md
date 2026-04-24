# P12-B 开发主线文档

## 当前阶段

P12-B：候选结果卡片按钮回调版

## 一、阶段背景

P12-A 已完成：

- discovery 成功结果已可优先返回飞书候选结果卡片
- 卡片展示 query / batch_id / 前 3~5 条候选
- 卡片失败可降级文本
- 文本方式“加入监控第 N 个”仍然可用

P12-B 不重新做 discovery，也不重新做候选卡片展示。

本轮只在 P12-A 的卡片基础上增加一个前台交互能力：

用户点击候选旁边的“加入监控”按钮后，系统复用已有 add-from-candidates 链路完成纳管。

## 二、当前唯一目标

只做：

候选结果卡片中的“加入监控”按钮回调。

目标链路：

1. 飞书发送：搜索商品：xxx
2. 系统返回候选结果卡片
3. 每条候选有“加入监控”按钮
4. 用户点击按钮
5. A 项目接收卡片 action 回调
6. A 根据 payload 解析 batch_id 与候选编号
7. A 调用 B 项目现有 add-from-candidates 能力
8. 成功后补发文本：“已加入监控”
9. 失败时返回老板可读错误

## 三、项目分工不变

A 项目：feishu-rpa-commerce-agent

职责：

- 飞书入口层
- 消息编排层
- 老板交互层
- 卡片展示与回调接入层

B 项目：Ecom-Watch-Agent-Agent

职责：

- discovery 搜索
- candidate batch 保存
- add-from-candidates 纳管
- monitor 对象管理

固定原则：

- 不合并 A / B
- A 调 B 继续按 Envelope 解包
- B 默认地址继续使用 http://127.0.0.1:8005
- 不把 B 的业务逻辑搬进 A

## 四、本轮允许做

允许：

1. 给 P12-A 候选卡片增加“加入监控”按钮
2. 增加最小卡片 action 回调入口
3. 在按钮 value 中携带最小 payload
4. 回调后复用现有 add-from-candidates 能力
5. 点击成功后补发文本结果
6. 点击失败后补发老板可读错误文本
7. 保留原文本方式“加入监控第 N 个”

## 五、本轮禁止做

禁止：

- 不做监控对象管理卡片
- 不做 pause / resume / delete 按钮
- 不做分页
- 不做卡片表单
- 不做复杂卡片状态同步
- 不做卡片更新态系统
- 不做公网回调平台化
- 不切 PostgreSQL
- 不新增业务动作
- 不重写 discovery 主链
- 不重写 add-from-candidates 主链
- 不破坏 P10 / P11 / P12-A 已收口链路

## 六、最小 payload 设计

按钮 value 最小字段：

```json
{
  "action": "add_from_candidate",
  "batch_id": 1,
  "candidate_index": 1,
  "query": "重力毯"
}
字段说明：

action：固定为 add_from_candidate
batch_id：来自 discovery batch
candidate_index：候选序号，从 1 开始
query：原始搜索词，仅用于展示和排查

注意：

candidate_index 面向老板展示，从 1 开始
内部取数组时如需转换，必须显式处理 index - 1
不允许只传 URL 后绕过 batch 体系
不允许绕过 B 的 add-from-candidates 能力
七、建议实现顺序
P12-B.0：回调入口锚定

先确认：

当前长连接入口是否支持卡片 action trigger
SDK 注册方法是否存在
action payload 在 raw event 中的位置
回调能否拿到 open_id / chat_id / message_id
回调失败时如何安全返回

不确定时先打印最小结构，不要大改主链。

P12-B.1：按钮建模

在 P12-A 卡片 builder 中给每条候选增加按钮。

要求：

按钮文案：加入监控
每条候选一个按钮
value 中携带 action / batch_id / candidate_index / query
不做 pause / resume / delete
不做分页
P12-B.2：回调任务接入

卡片回调入口不要直接堆复杂业务。

建议：

入口只做解析、校验、入队或调用既有服务函数
业务执行复用 add-from-candidates
成功/失败结果统一老板可读文本
P12-B.3：结果反馈

本轮优先用“补发文本”反馈，不做复杂卡片更新。

成功文本至少包含：

已加入监控
选择编号
名称
URL
对象ID
状态

失败文本至少包含：

未能加入监控
失败原因
可继续使用“加入监控第 N 个”重试
P12-B.4：最小回归

必须确认：

搜索商品仍能返回卡片
点击按钮能加入监控
文本方式“加入监控第 N 个”仍能加入监控
搜索失败仍是文本错误
看看当前监控对象仍能返回
八、通过标准

P12-B 通过必须满足：

搜索商品：重力毯 能返回候选卡片
每条候选都有“加入监控”按钮
点击第 1 条按钮后能成功纳管
成功后能补发老板可读文本
再发“加入监控第 2 个”仍能成功
失败场景不吐堆栈
P12-A 展示能力不退化
P10 / P11 主链不被破坏
九、提交边界

本轮允许提交：

AGENTS.md
docs/p12/p12-project-plan.md
docs/p12/P12-agent-prompt.md
docs/p12/p12-boss-demo-sop.md
docs/p12/p12-acceptance-checklist.md
P12-B 相关最小代码
P12-B 相关最小测试

不允许混入：

P12-C 监控管理卡片
PostgreSQL 切换
其他重构
无关文档
临时日志