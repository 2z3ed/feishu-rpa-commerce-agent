# P11 收口报告

## 一、阶段结论

P11-A（从 URL 直接加入监控）已通过并收口。

本轮结论：
- A 已完成 URL 加监控意图识别与单字段 `url` 提取
- A 已稳定调用 B：`POST /internal/monitor/add-by-url`
- A 已按 Envelope（`ok/data/error`）显式解包
- 飞书成功/失败文本路径均已成立
- 联动“看看当前监控对象”可看到新增对象
- P10 查询链路保持正常

## 二、固定真实样本（冻结）

### 1) 成功样本
- 用户原文：`监控这个商品：https://example.com/product/abc`
- task_id：`TASK-P11A-SUCC-002`
- message_id：`om_x100b5195ddb2a8acc37bf94e86bee96`
- 飞书回复原文：
  - 已加入监控。
  - URL：https://example.com/product/abc
  - 名称：abc
  - 对象ID：4
  - 状态：active

### 2) 失败样本
- 用户原文：`监控这个商品：not-a-url`
- task_id：`TASK-P11A-FAIL-002`
- message_id：`om_x100b5195dd466ca0c33b9aaee23cab5`
- 飞书回复原文：
  - 加入监控失败：B 服务错误：invalid url: only http/https/mock:// are supported (code=HTTP_400, status=400)

### 3) 联动验证样本
- 用户原文：`看看当前监控对象`
- task_id：`TASK-P11A-P10T-002`
- 验证结果：列表中已出现 `#4 abc（active）`

### 4) P10 回归样本
- 用户原文：`今天有什么变化`
- task_id：`TASK-P11A-P10S-002`
- 验证结果：查询链路正常返回摘要

## 三、收口范围确认

本轮已做：
- add-by-url 主链（成功 / 失败）
- 飞书文本回复成型
- A→B Envelope 解包
- 联动与回归验证

本轮未做（后移）：
- discovery 搜索
- candidate batch / add-from-candidates
- pause / resume / delete
- 卡片正式交互
- PostgreSQL 切换

## 四、下一阶段候选方向（仅方向，不开工）

1. **P11-B：discovery 搜索 + candidate batch**  
   原因：先补“发现候选”入口，为后续编号纳管提供输入。

2. **P11-C：add-from-candidates 编号选择最小闭环**  
   原因：把候选集转成可执行纳管动作，完成 discovery 到纳管闭环。

3. **P11-D：monitor 管理动作（pause/resume/delete）**  
   原因：生命周期管理价值高，但优先级在“发现+纳管”闭环之后。
