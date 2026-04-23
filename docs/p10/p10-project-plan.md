# P10 开发主线文档（已收口）
## 阶段名称
P10：A 接 B 最小集成验证

## 一、阶段定义

P10 不是把项目 A 和项目 B 合并成一个项目。
也不是把项目 B 扩成飞书入口机器人。
更不是一上来就接 discovery、add monitor、候选选择、复杂卡片交互。

这一轮只做一件事：

让项目 A 作为飞书入口层，
开始调用项目 B 的查询类 internal API，
先跑通一条老板在飞书里可直接使用的最小查询闭环。

一句话定义：

老板在飞书里发一句查询类命令
→ A 解析老板意图
→ A 调用 B 的 internal API
→ A 解包 Envelope
→ A 把结果翻译成老板能看懂的飞书文本回复。

## 二、为什么现在该做这一轮

项目 A 当前已经具备飞书入口、文本回执、任务链路、RPA、主系统留痕、多维表等主线能力。
项目 B 当前已经具备业务服务层能力，包括：

- 今日摘要
- 商品详情
- 最近报告
- 监控对象列表
- 发现候选
- 加入监控
- 暂停 / 恢复 / 删除监控对象

但 B 的定位不是飞书入口层，而是业务服务层。
因此当前最合理的不是继续让 B 承担飞书角色，
而是让 A 开始消费 B 的能力。

## 三、A / B 固定分工（必须继承）

### A 的定位
A 是飞书入口层、消息编排层、老板交互层。

A 负责：
- 接收飞书消息
- 解析老板意图
- 保存会话上下文
- 调用 B
- 把 B 的结果翻译成老板能看懂的文本或卡片

### B 的定位
B 是业务服务层。

B 负责：
- discovery
- scrapy / playwright 采集
- baseline
- snapshot
- diff
- analyzer
- 今日摘要
- 商品详情
- 报告查询
- 监控对象管理

### 当前原则
- 不把 A / B 合并成一个项目
- 不让 B 长期承担飞书入口角色
- 不让 A 直接吞掉 B 的业务逻辑实现

## 四、本轮唯一目标

本轮唯一目标是：

先把 A 调 B 的查询链路打通。

而且必须按固定顺序来：

### 第一优先先接
- GET /internal/summary/today
- GET /internal/monitor/targets
- GET /internal/products/{id}/detail

### 当前不优先接
- POST /internal/discovery/search
- GET /internal/discovery/batches/{batch_id}
- POST /internal/monitor/add-from-candidates
- POST /internal/monitor/add-by-url
- POST /internal/monitor/{id}/pause
- POST /internal/monitor/{id}/resume
- DELETE /internal/monitor/{id}

一句话：
先让老板能问、能看、能查，再做发现与加入监控。

## 五、本轮最小闭环建议

### 最小链路 1：今日摘要
老板在飞书里发：
- 今天有什么变化
- 看看今天摘要
- 今日监控摘要

A 做这些事：
1. 解析为“查询今日摘要”
2. 调 B：GET /internal/summary/today
3. 解包 Envelope
4. 把 data 翻译成飞书文本结果

### 最小链路 2：当前监控对象
老板在飞书里发：
- 看看当前监控对象
- 当前监控哪些商品
- 监控列表

A 做这些事：
1. 解析为“查询监控对象列表”
2. 调 B：GET /internal/monitor/targets
3. 解包 Envelope
4. 把结果翻译成飞书文本

### 最小链路 3：商品详情
老板在飞书里发：
- 看看商品 123 的详情
- 查看商品 123
- 商品 123 怎么样

A 做这些事：
1. 解析出 product_id
2. 调 B：GET /internal/products/{id}/detail
3. 解包 Envelope
4. 返回飞书文本详情

## 六、固定运行口径

### A 端口
保持项目 A 的现有口径，不要为了接 B 改 A 的主端口定义。

### B 端口
固定：
- http://127.0.0.1:8005

### 返回结构
A 调 B 时，必须按 Envelope 解包：

成功：
{
  "ok": true,
  "data": {},
  "error": null
}

失败：
{
  "ok": false,
  "data": null,
  "error": {
    "message": "...",
    "code": "...",
    "status_code": 400,
    "request_id": "...",
    "timestamp": "..."
  }
}

A 不允许假设 B 返回裸业务对象。

## 七、建议实现位置

### 1. 在 A 中新增最小 b_client
不要在 message handler 里零散写 requests.get(...)。
建议在 A 的 service / integration 层新增一个最小 HTTP client。

### 2. 先实现 3 个最小方法
- get_today_summary()
- get_monitor_targets()
- get_product_detail(product_id)

### 3. 统一处理 Envelope
b_client 统一做：
- HTTP 请求
- ok/data/error 解包
- 错误翻译为 A 内部异常或老板可读提示

### 4. A 的消息层只做两件事
- 识别老板在问什么
- 调 b_client
- 再把结果翻译成老板能看懂的文本

## 八、本轮开发拆分

### P10.0：A / B 集成锚定
确认：
- B 服务是否稳定运行在 127.0.0.1:8005
- A 能否从本地访问 B
- 3 个查询接口是否都可调用
- Envelope 解包策略是否明确

### P10.1：今日摘要链路接入
打通：
老板发“今天有什么变化”
→ A 调 summary/today
→ A 回飞书文本摘要

### P10.2：监控对象列表链路接入
打通：
老板发“看看当前监控对象”
→ A 调 monitor/targets
→ A 回飞书文本

### P10.3：商品详情链路接入
打通：
老板发“看看商品 123 的详情”
→ A 调 products/{id}/detail
→ A 回飞书文本

### P10.4：演示 SOP 与验收
补：
- 演示 SOP
- 验收清单
- 文档入口统一

## 九、本轮明确不做什么

本轮不做：

- 不接 discovery + add monitor 主链
- 不做候选批次编号选择
- 不做暂停 / 恢复 / 删除前台指令
- 不做 A / B 共享数据库
- 不做公网回调
- 不做 B 端飞书入口扩展
- 不做前端
- 不做卡片正式交互版
- 不把 A / B 合并成一个项目

## 十、本轮最低通过标准

1. A 能访问 B 的 8005
2. A 能正确解包 B 的 Envelope
3. 飞书里至少有 1 条真实查询闭环跑通
4. 第一条闭环建议为 summary/today
5. 第二条闭环建议为 monitor/targets
6. 不破坏 A 当前 P9 主线
7. 不让 B 长期承担飞书入口角色

## 十一、真实联调固定样本（收口冻结）

> B 固定地址：`http://127.0.0.1:8005`  
> A 调 B 固定按 Envelope 解包（ok/data/error），不假设裸对象。

### 样本 1：今天有什么变化
- message_id：`om_x100b51949a80c4b0c2c5d7d60458179`
- task_id：`TASK-20260423-DC9ED2`
- 飞书回复文本：
  - 今日监控摘要：
  - 今日监控商品数：2
  - 今日变化商品数：0
  - 高优先级数量：0
  - 今日暂无异常变化。

### 样本 2：看看当前监控对象
- message_id：`om_x100b51949aa8f8b0c3f6b6762ef618e`
- task_id：`TASK-20260423-891A97`
- 飞书回复文本：
  - 当前监控对象（共 3 个）：
  - #1 Mock Phone X（inactive）
  - #2 Mock Headphone Pro（active）
  - #3 Mock Keyboard Mini（active）

### 样本 3：看看商品 123 的详情（失败路径）
- message_id：`om_x100b51949ab138a4c45dbaab6e9379b`
- task_id：`TASK-20260423-8365B8`
- 飞书回复文本：
  - 查询失败：B 服务错误：product not found (code=HTTP_404, status=404)

### 样本 4：看看商品 1 的详情（成功路径）
- message_id：`om_x100b51949a558ca4c31573be9263fa7`
- task_id：`TASK-20260423-B2A93D`
- 飞书回复文本：
  - 商品详情 #1
  - 名称：Mock Phone X
  - 状态：active
  - 价格：N/A

## 十二、后移项（冻结）

- discovery 主链继续后移
- add monitor 主链继续后移
- pause / resume / delete 前台操作继续后移
- 卡片正式交互继续后移
- PostgreSQL 切换不属于本轮范围