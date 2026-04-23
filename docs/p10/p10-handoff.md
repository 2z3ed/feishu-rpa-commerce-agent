# P10 交接文档

## 一、交接状态

- 阶段：P10（A 接 B 最小集成验证）
- 状态：已收口，可演示
- 主线：A 负责飞书入口与文本回写，B 负责业务查询服务

## 二、固定运行口径

- B 服务地址：`http://127.0.0.1:8005`
- A 调 B 返回协议：Envelope
  - success: `ok=true, data!=null, error=null`
  - failed: `ok=false, data=null, error={message/code/status_code/request_id/timestamp}`
- A 禁止把 `response.json()` 直接当业务 data 使用

## 三、固定验收样本（真实）

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

## 四、后移项（不要提前开工）

- discovery 主链继续后移
- add monitor 主链继续后移
- pause / resume / delete 前台操作继续后移
- 卡片正式交互继续后移
- PostgreSQL 不属于本轮范围

## 五、接手注意事项

- 不要改写 P10 主叙事（查询链路已通过）
- 不要回头重构 A/B 集成主链
- 若进入下一阶段，按优先级从 discovery -> add monitor -> monitor 管理动作推进
