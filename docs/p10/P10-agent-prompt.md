# P10 当前阶段约束文档（Agent 必须先读）

你现在接手的是 feishu-rpa-commerce-agent 项目。

当前不要发散，也不要误判主线。

## 一、你必须先接受的当前真实状态

当前阶段不是继续补 P9 后台主线。
当前 P9 相关链路已经收口。

当前唯一主线已经切换为：

P10：A 接 B 最小集成验证

当前目标不是继续打 RPA，
也不是继续补多维表，
而是让 A 开始作为飞书入口层，
去消费 B 的业务服务能力。

## 二、开始前必须先读

### 先读 B 的交接信息
1. 项目 B 交接摘要（用户提供）

### 再读当前阶段文件
2. docs/p10/p10-project-plan.md
3. docs/p10/P10-agent-prompt.md
4. docs/p10/p10-boss-demo-sop.md
5. docs/p10/p10-acceptance-checklist.md

如果文件名与预期不一致，先执行：
- ls -la docs/p10

不要停在“找文件”这一步空转。

## 三、当前固定分工（必须继承）

A 负责：
- 接收飞书消息
- 解析老板意图
- 保存会话上下文
- 调用 B
- 把 B 的结果翻译成老板能看懂的文本

B 负责：
- discovery
- 采集
- baseline
- summary
- detail
- monitor targets
- 管理动作

不要把 A / B 合并成一个项目。

## 四、本轮唯一目标

只打通 A → B 的查询链路。

本轮固定顺序：

### 第一优先
- GET /internal/summary/today
- GET /internal/monitor/targets
- GET /internal/products/{id}/detail

### 当前不做
- discovery
- add-from-candidates
- add-by-url
- pause / resume / delete
- 候选编号选择
- 复杂卡片交互

## 五、当前固定约束

### B 服务地址
固定：
- http://127.0.0.1:8005

### Envelope 解包
B 返回统一 Envelope：
- ok
- data
- error

A 调 B 时，必须显式解包。
不要假设返回裸业务对象。

### 飞书回复形态
本轮先只做：
- 文本回复

不要先做：
- 按钮卡片
- 编号选择
- 多轮候选交互

## 六、本轮你只允许先做这些事

### P10.0：集成锚定
先确认：
- A 当前最适合接 B 的位置在哪里
- 是否已有 integration / service 层可放 b_client
- B 的 8005 是否可达
- 3 个查询接口是否能调用
- Envelope 是否已理解

### P10.1：summary/today 接入
只做：
- 老板发“今天有什么变化”
- A 解析后调 B 的 summary/today
- A 解包 Envelope
- A 回飞书文本摘要

### P10.2：monitor/targets 接入
只做：
- 老板发“看看当前监控对象”
- A 调 B 的 monitor/targets
- A 回飞书列表文本

### P10.3：products/{id}/detail 接入
只做：
- 老板发“看看商品 123 的详情”
- A 调 B 的 detail
- A 回飞书详情文本

### P10.4：SOP 与验收
只做：
- 演示 SOP
- 验收清单
- 当前阶段入口统一

## 七、当前明确不要做

当前禁止做：

- 不接 discovery 主链
- 不接 add monitor 主链
- 不做候选层编号交互
- 不做 pause / resume / delete 前台操作
- 不做卡片正式交互版
- 不做共享数据库
- 不让 B 接管飞书入口
- 不改 P9 已收口主线
- 不扩第二项目的大重构

## 八、工作方式要求

你必须先检查仓库当前真实状态，再做最小改动。

每完成一小段，都必须按这个格式回报：

A. 本轮做了什么
B. 改了哪些文件
C. 如何启动 / 复验
D. 是否通过
E. 下一步建议

不允许：

- 只给计划，不给结果
- 只贴 diff，不给中文结论
- 输出其他语言
- 直接跳去做 discovery / add monitor

## 九、输出语言要求

- 只允许使用简体中文输出
- 命令、路径、代码可保留原文
- 解释、结论必须全部使用简体中文

## 十、P10 收口固定事实（必须继承）

- B 服务地址固定：`http://127.0.0.1:8005`
- A 调 B 必须解包 Envelope：`ok/data/error`
- 禁止把 response.json() 直接当业务 data 使用
- 成功 / 失败两条文本路径都已成立

固定样本（真实联调）：

1) 今天有什么变化  
- message_id: `om_x100b51949a80c4b0c2c5d7d60458179`  
- task_id: `TASK-20260423-DC9ED2`  
- 回复：今日监控摘要（监控商品数/变化数/高优先级/暂无异常变化）

2) 看看当前监控对象  
- message_id: `om_x100b51949aa8f8b0c3f6b6762ef618e`  
- task_id: `TASK-20260423-891A97`  
- 回复：当前监控对象（3条）

3) 看看商品 123 的详情（失败）  
- message_id: `om_x100b51949ab138a4c45dbaab6e9379b`  
- task_id: `TASK-20260423-8365B8`  
- 回复：查询失败：B 服务错误：product not found (code=HTTP_404, status=404)

4) 看看商品 1 的详情（成功）  
- message_id: `om_x100b51949a558ca4c31573be9263fa7`  
- task_id: `TASK-20260423-B2A93D`  
- 回复：商品详情 #1（名称/状态/价格）

## 十一、你下一条回复必须严格按这个格式

A. 先读了哪些文件
B. 当前 A / B 集成锚定结果
C. 本轮实际执行了哪些命令
D. 改了哪些文件
E. summary/today 是否已接入
F. monitor/targets 是否已接入
G. detail 是否已接入
H. 当前阶段结论
I. 下一步建议

判断标准只有 4 个：

- A 能调 B
- A 能解包 Envelope
- 老板能在飞书里看到查询结果
- 不破坏 A 当前主线