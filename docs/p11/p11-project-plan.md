# P11 开发主线文档
## 当前阶段
P11-B：discovery 搜索 + candidate batch

## 阶段收口结论

P11-B 已通过并收口。

本阶段只保留 discovery 搜索 + candidate batch 的最小闭环，不再继续扩展 add-from-candidates、编号选择、卡片交互或 PostgreSQL 切换。

固定真实样本已冻结：
- 成功样本：`搜索商品：蓝牙耳机`
- 失败样本：`搜索商品：`

## 一、阶段定义

P11-B 不是继续做 add-by-url。
也不是马上做 add-from-candidates、编号选择、卡片交互、多轮状态管理。
更不是 pause / resume / delete、PostgreSQL、共享数据库。

这一轮只做一件事：

让老板在飞书里发一个搜索词，
A 调 B 的 discovery/search，
再根据 batch_id 查询候选结果，
最后把候选列表翻译成老板看得懂的飞书文本。

一句话定义：

老板在飞书里发搜索词
→ A 识别为 discovery 搜索
→ A 调 B：POST /internal/discovery/search
→ A 拿到 batch_id
→ A 再调 B：GET /internal/discovery/batches/{batch_id}
→ A 把候选结果回给老板看

## 二、为什么现在做这一轮

P10 已经完成“可看”：
- 今天有什么变化
- 看看当前监控对象
- 看看商品详情

P11-A 已经完成“可纳管（直链）”：
- 发一个 URL
- 直接加入监控

现在最自然的下一步不是直接做复杂纳管，
而是补“发现”这条上游能力：

先让老板能搜出候选，
再在后续阶段决定是否把候选转成正式监控对象。

所以 P11-B 的本质是：

从“能直接纳管一个已知 URL”
推进到
“能先发现候选，再为后续纳管做准备”。

## 三、当前固定分工（必须继承）

### A 的定位
A 是飞书入口层、消息编排层、老板交互层。

A 负责：
- 接收飞书消息
- 解析老板意图
- 调用 B
- 把 B 的结果翻译成老板能看懂的文本

### B 的定位
B 是业务服务层。

B 负责：
- discovery
- candidate_batches
- candidate_items
- add-from-candidates
- add-by-url
- summary / detail / monitor targets
- 管理动作

### 当前原则
- 不把 A / B 合并成一个项目
- A 继续作为飞书入口层
- B 继续作为业务服务层
- A 调 B 必须按 Envelope 解包
- A 不直接操作 B 的数据库

## 四、本轮唯一目标

本轮唯一目标是打通以下两条接口：

1. POST /internal/discovery/search
2. GET /internal/discovery/batches/{batch_id}

形成最小闭环：

老板在飞书里发搜索命令
→ A 识别并提取 query
→ A 调 B 的 discovery/search
→ A 拿到 batch_id
→ A 调 B 的 discovery/batches/{batch_id}
→ A 把候选结果翻译成文本返回老板

## 五、本轮固定范围（必须收窄）

### 只做两个 discovery 接口
固定只做：
- POST /internal/discovery/search
- GET /internal/discovery/batches/{batch_id}

### 只做飞书文本回复
本轮不做：
- 候选编号选择
- 从候选加入监控
- discovery 结果卡片
- 多轮状态机

### 只做最小命令口径
建议先只支持：
- 搜索商品：xxx
- 帮我找一下 xxx
- 搜索：xxx

最小提取字段只做：
- query

### 继续按 Envelope 解包
成功：
- ok=true
- data=...
- error=null

失败：
- ok=false
- data=null
- error={...}

A 不允许假设 B 返回裸业务对象。

## 六、本轮明确不做什么

本轮不做：

- 不接 add-from-candidates
- 不做候选编号选择
- 不接 add-by-url 扩展
- 不做 pause / resume / delete
- 不做卡片正式交互
- 不做共享数据库
- 不切 PostgreSQL
- 不回头改 P10 / P11-A 已收口边界
- 不做 discovery 全链大重构

## 七、本轮开发拆分

### P11-B.0：discovery 锚定
确认：
- B 的 POST /internal/discovery/search 是否可调用
- B 的 GET /internal/discovery/batches/{batch_id} 是否可调用
- success / failed Envelope 长什么样
- batch_id 在响应中的位置
- candidate 最小字段有哪些

### P11-B.1：飞书搜索命令接入
只做：
- 搜索商品：xxx
- 帮我找一下 xxx
- 搜索：xxx

只解析：
- query

### P11-B.2：候选结果文本化
A 需要：
1. 调 discovery/search
2. 再调 discovery/batches/{batch_id}
3. 把前 3~5 条候选结果翻成老板可读文本

建议至少展示：
- 序号
- 名称
- URL
- 来源 / 站点（若有）
- batch_id

### P11-B.3：最小实机验收
只验证：
- 飞书前台真实搜索命令
- A 真实调到 B 的 discovery
- 飞书能看到候选列表文本
- 失败时也返回老板可读错误文本

## 八、建议实现位置

### 1. 继续使用 A 中现有 b_client
建议继续在：
- app/clients/b_service_client.py

中新增最小方法，例如：
- discovery_search(query)
- get_discovery_batch(batch_id)

### 2. 继续在 A 的意图层识别
建议沿用：
- resolve_intent

增加最小意图，例如：
- ecom_watch.discovery_search

### 3. 继续在 A 的执行层解包并翻译文本
建议沿用：
- execute_action

不要在消息入口层散写调用细节。

## 九、本轮最低通过标准

1. A 能调通 B 的 discovery/search
2. A 能调通 B 的 discovery/batches/{batch_id}
3. A 能按 Envelope 正确解包
4. 飞书里至少有 1 条真实搜索闭环跑通
5. 失败场景返回老板可读文本
6. 不破坏 P10 / P11-A 已收口链路