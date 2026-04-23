# P11 当前阶段约束文档（Agent 必须先读）

你现在接手的是 feishu-rpa-commerce-agent 项目。

当前不要发散，也不要误判主线。

## 一、你必须先接受的当前真实状态

当前阶段不是继续做 P11-A 的 add-by-url。
P11-A 已经完成并收口。

当前唯一主线已经切换为：

P11-B：discovery 搜索 + candidate batch

当前目标不是“直接纳管”，
而是先让老板在飞书里搜出候选结果。

P11-B 已通过并收口，当前不再继续改业务代码，只做文档整理与阶段交接。

## 二、开始前必须先读

先读上一阶段收口材料：

1. docs/p11/p11-closure-report.md
2. docs/p11/p11-handoff.md

再读当前阶段文件：

3. docs/p11/p11-project-plan.md
4. docs/p11/P11-agent-prompt.md
5. docs/p11/p11-boss-demo-sop.md
6. docs/p11/p11-acceptance-checklist.md

如果文件名与预期不一致，先执行：
- ls -la docs/p11

确认真实文件名后继续。
不要停在“找文件”这一步空转。

## 三、当前固定分工（必须继承）

A 负责：
- 接收飞书消息
- 解析老板意图
- 调用 B
- 把结果翻译成老板可读文本

B 负责：
- discovery
- candidate_batches
- candidate_items
- add-from-candidates
- add-by-url
- summary / detail / monitor targets
- 管理动作

不要把 A / B 合并成一个项目。

## 四、本轮唯一目标

只打通：

1. POST /internal/discovery/search
2. GET /internal/discovery/batches/{batch_id}

形成最小闭环：

老板在飞书里发搜索词
→ A 识别为 discovery 搜索
→ A 调 B discovery/search
→ A 拿到 batch_id
→ A 调 B discovery/batches/{batch_id}
→ A 返回候选列表文本

## 五、本轮固定口径

### B 服务地址
固定：
- http://127.0.0.1:8005

### Envelope 解包
A 调 B 继续按：
- ok
- data
- error

显式解包。

### 飞书回复形态
本轮先只做：
- 文本回复

### 命令口径
当前只支持：
- 搜索商品：xxx
- 帮我找一下 xxx
- 搜索：xxx

只解析：
- query

## 六、本轮你只允许先做这些事

### P11-B.0：discovery 锚定
先确认：
- B 的 search 是否可调用
- B 的 batch 查询是否可调用
- 成功 / 失败 Envelope 长什么样
- batch_id 怎么拿
- candidate 的最小字段有哪些

### P11-B.1：飞书搜索命令接入
只做：
- 最小搜索命令口径
- 最小 query 提取
- 最小意图识别

### P11-B.2：候选结果文本化
只做：
- 前 3~5 条候选结果展示
- 名称 / URL / 来源 / batch_id（若有）
- 老板可读文本
- 不返回原始 JSON
- 不返回 Python 堆栈

### P11-B.3：最小实机验收
只验证：
- 飞书前台真实搜索命令
- A 真实调到 B 的 discovery
- 飞书收到候选列表文本
- 失败文本也老板可读

## 七、当前明确不要做

当前禁止做：

- 不接 add-from-candidates
- 不做候选编号选择
- 不做 add-by-url 扩展
- 不做 pause / resume / delete
- 不做卡片交互
- 不做共享数据库
- 不切 PostgreSQL
- 不回头改 P10 / P11-A 已收口链路
- 不做 discovery 大重构

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
- 直接跳去做 add-from-candidates

## 九、输出语言要求

- 只允许使用简体中文输出
- 命令、路径、代码可保留原文
- 解释、结论必须全部使用简体中文

## 十、你下一条回复必须严格按这个格式

A. 先读了哪些文件
B. 当前 discovery 锚定结果
C. 本轮实际执行了哪些命令
D. 改了哪些文件
E. discovery/search 是否已接入
F. discovery/batch 是否已接入
G. 飞书搜索命令是否已能触发候选列表
H. 当前阶段结论
I. 下一步建议

判断标准只有 4 个：

- A 能调 B 的 discovery
- A 能解包 Envelope
- 老板能在飞书里看到候选结果
- 不破坏 P10 / P11-A 已收口主线