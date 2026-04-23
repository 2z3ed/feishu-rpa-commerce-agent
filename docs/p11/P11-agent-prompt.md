# P11 当前阶段约束文档（收口版）

你现在接手的是 feishu-rpa-commerce-agent 项目。

P11-A 已通过，当前进入收口与交接阶段。

## 一、当前真实状态（冻结）

当前唯一结论：

P11-A：从 URL 直接加入监控（最小纳管闭环）已成立。

已冻结的真实样本：

1) 成功样本  
- 用户原文：`监控这个商品：https://example.com/product/abc`  
- task_id：`TASK-P11A-SUCC-002`  
- message_id：`om_x100b5195ddb2a8acc37bf94e86bee96`  
- 飞书回复原文：  
  - 已加入监控。  
  - URL：https://example.com/product/abc  
  - 名称：abc  
  - 对象ID：4  
  - 状态：active  

2) 失败样本  
- 用户原文：`监控这个商品：not-a-url`  
- task_id：`TASK-P11A-FAIL-002`  
- message_id：`om_x100b5195dd466ca0c33b9aaee23cab5`  
- 飞书回复原文：  
  - 加入监控失败：B 服务错误：invalid url: only http/https/mock:// are supported (code=HTTP_400, status=400)  

3) 联动验证  
- 用户原文：`看看当前监控对象`  
- task_id：`TASK-P11A-P10T-002`  
- 列表已出现：`#4 abc（active）`  

4) P10 回归  
- 用户原文：`今天有什么变化`  
- task_id：`TASK-P11A-P10S-002`  

## 二、当前工作范围（只允许）

当前只允许：
- 文档收口
- 交接说明
- 后移项冻结

当前禁止：
- 继续改业务代码
- 继续扩 discovery / add-from-candidates
- 扩卡片交互
- 切 PostgreSQL

## 三、固定后移项

- discovery 搜索后移到 P11-B
- candidate batch / add-from-candidates 后移
- pause / resume / delete 后移
- 卡片正式交互后移
- PostgreSQL 不属于本轮范围

## 四、下一阶段候选方向（只列方向）

1. P11-B：discovery 搜索 + candidate batch  
2. P11-C：add-from-candidates 编号选择最小闭环  
3. P11-D：monitor 管理动作（pause/resume/delete）  

## 五、输出要求

- 只允许使用简体中文
- 先给结论，再给证据
- 不允许只给计划不给结果