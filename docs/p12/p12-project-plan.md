# P12-C 开发主线文档

## 阶段名称

P12-C：监控对象管理卡片版

## 一、阶段背景

P12-A 已完成候选结果卡片展示。  
P12-B 已完成候选卡片“加入监控”按钮回调。

当前老板交互中，还有一条仍然是纯文本：

看看当前监控对象
它现在能返回监控对象列表，但展示形态还是文本，不利于老板快速判断哪些对象 active、inactive，也不方便后续做管理动作。

所以 P12-C 的目标不是新增业务能力，而是把已有 monitor list 结果升级为飞书管理卡片。

二、本轮唯一目标

只做：

把“看看当前监控对象”的成功回复升级为监控对象管理卡片。

卡片最小展示：

当前监控对象总数
对象名称
对象ID
状态 active / inactive
URL
最小操作按钮：暂停 / 恢复
三、当前固定边界

A 项目仍是：

飞书入口层
消息编排层
老板交互层

B 项目仍是：

业务服务层
monitor target 数据与动作提供方

固定原则：

不合并 A / B
A 调 B 继续按 Envelope 解包
B 默认地址继续为 http://127.0.0.1:8005
不把 B 的业务逻辑搬进 A
不重写 P12-A / P12-B
四、本轮允许做

允许：

新增 monitor target 管理卡片 builder
“看看当前监控对象”成功时优先返回卡片
卡片失败时 fallback 文本
卡片展示前 5 条监控对象
active 对象展示“暂停监控”按钮
inactive 对象展示“恢复监控”按钮
点击暂停 / 恢复后复用现有 monitor 管理能力
成功后补发老板可读文本
失败后补发老板可读错误
五、本轮禁止做

禁止：

不做删除按钮
不做批量暂停 / 批量恢复
不做分页
不做搜索过滤
不做复杂卡片状态同步
不做卡片局部刷新
不做 PostgreSQL 切换
不新增业务动作
不重写 P12-A / P12-B
不破坏候选卡片“加入监控”按钮
不破坏文本命令
六、最小按钮 payload

暂停按钮：

{
  "action": "pause_monitor_target",
  "target_id": 7,
  "source": "monitor_list_card"
}

恢复按钮：

{
  "action": "resume_monitor_target",
  "target_id": 7,
  "source": "monitor_list_card"
}

字段说明：

action：固定动作名
target_id：监控对象ID
source：用于排查来源
七、建议实现顺序
P12-C.0：锚定现有监控对象查询链

先确认：

“看看当前监控对象”当前 intent_code 是什么
当前 execute_action 如何调用 B
当前 result_summary 文本如何生成
当前是否已有 pause / resume 文本命令能力
如果没有 pause / resume 能力，本轮先只做展示卡片，不做按钮落地
P12-C.1：管理卡片 builder

新增独立 builder，建议位置：

app/services/feishu/cards/monitor_targets.py

不要把卡片 JSON 散写在 execute_action 或 ingress_tasks 中。

P12-C.2：成功路径替换

当“看看当前监控对象”成功时：

优先构建管理卡片
优先发送 interactive 卡片
发送失败 fallback 原文本列表
P12-C.3：暂停 / 恢复按钮回调

如果现有 B 服务已有 pause / resume 能力，则接入。

如果没有，则不要硬造业务能力，先回报：

当前 B 未提供 pause/resume 能力，P12-C 本轮只能完成管理卡片展示，按钮动作后移。
P12-C.4：最小验收

必须验证：

看看当前监控对象 → 返回管理卡片
卡片展示对象名称、状态、URL、ID
卡片失败时 fallback 文本
P12-A 搜索卡片不退化
P12-B 加入监控按钮不退化
文本加入监控仍可用
八、通过标准

P12-C 通过条件：

“看看当前监控对象”优先返回管理卡片
卡片展示信息完整
失败 fallback 文本
不破坏 P12-A
不破坏 P12-B
不混入删除 / 分页 / PostgreSQL
如果 pause / resume 已接入，必须实机验证成功
如果 pause / resume 未接入，必须明确记录后移原因
九、提交边界

允许提交：

AGENTS.md
README.md 增量
docs/p12 四份约束文件
monitor card builder
P12-C 最小回调代码
P12-C 最小测试

禁止提交：

无关重构
P12-D 内容
删除按钮
分页
PostgreSQL
临时日志