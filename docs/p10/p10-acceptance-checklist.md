# P10 验收清单

## 一、范围验收

- [x] 只做 A 接 B 查询链路
- [x] 未接 discovery 主链
- [x] 未接 add monitor 主链
- [x] 未做 pause / resume / delete 前台操作
- [x] 未做卡片正式交互
- [x] 未做共享数据库
- [x] 未改 P9 已收口边界

## 二、B 服务验收

- [x] B 运行在 127.0.0.1:8005
- [x] summary/today 可调用
- [x] monitor/targets 可调用
- [x] products/{id}/detail 可调用
- [x] A 能正确访问 B

## 三、Envelope 验收

- [x] A 没有假设裸对象返回
- [x] A 能处理 ok=true
- [x] A 能处理 ok=false
- [x] A 能把 error 翻译成老板可读文本

## 四、飞书前台验收

### 今日摘要
- [x] 飞书里“今天有什么变化”可得到文本回复（TASK-20260423-DC9ED2）

### 当前监控对象
- [x] 飞书里“看看当前监控对象”可得到文本回复（TASK-20260423-891A97）

### 商品详情（可选）
- [x] 飞书里“看看商品 123 的详情”可得到失败文本回复（TASK-20260423-8365B8）
- [x] 飞书里“看看商品 1 的详情”可得到成功文本回复（TASK-20260423-B2A93D）

## 五、边界验收

- [x] A 仍是飞书入口层
- [x] B 仍是业务服务层
- [x] 未把 A / B 合并成一个项目
- [x] 未让 B 长期承担飞书入口角色
- [x] 未破坏 A 原有链路

## 六、固定样本回填

- 今天有什么变化
  - message_id: `om_x100b51949a80c4b0c2c5d7d60458179`
  - task_id: `TASK-20260423-DC9ED2`
- 看看当前监控对象
  - message_id: `om_x100b51949aa8f8b0c3f6b6762ef618e`
  - task_id: `TASK-20260423-891A97`
- 看看商品 123 的详情（失败）
  - message_id: `om_x100b51949ab138a4c45dbaab6e9379b`
  - task_id: `TASK-20260423-8365B8`
- 看看商品 1 的详情（成功）
  - message_id: `om_x100b51949a558ca4c31573be9263fa7`
  - task_id: `TASK-20260423-B2A93D`