# P11 交接文档

## 一、交接状态

- 阶段：P11-A（从 URL 直接加入监控）
- 状态：已收口，可演示
- 主线：A 负责飞书入口与文本回写，B 负责 add-by-url 业务服务

## 二、固定运行口径

- B 服务地址：`http://127.0.0.1:8005`
- A 调 B 返回协议：Envelope
  - success：`ok=true, data!=null, error=null`
  - failed：`ok=false, data=null, error={message/code/status_code/...}`
- A 不允许把 `response.json()` 当裸业务对象直接使用

## 三、固定验收样本（真实）

1) 成功样本  
- 用户原文：`监控这个商品：https://example.com/product/abc`  
- task_id：`TASK-P11A-SUCC-002`  
- message_id：`om_x100b5195ddb2a8acc37bf94e86bee96`  
- 回复：  
  - 已加入监控。  
  - URL：https://example.com/product/abc  
  - 名称：abc  
  - 对象ID：4  
  - 状态：active

2) 失败样本  
- 用户原文：`监控这个商品：not-a-url`  
- task_id：`TASK-P11A-FAIL-002`  
- message_id：`om_x100b5195dd466ca0c33b9aaee23cab5`  
- 回复：  
  - 加入监控失败：B 服务错误：invalid url: only http/https/mock:// are supported (code=HTTP_400, status=400)

3) 联动验证样本  
- 用户原文：`看看当前监控对象`  
- task_id：`TASK-P11A-P10T-002`  
- 结果：列表中出现 `#4 abc（active）`

4) P10 回归样本  
- 用户原文：`今天有什么变化`  
- task_id：`TASK-P11A-P10S-002`  
- 结果：查询链路正常

## 四、后移项（不要提前开工）

- discovery 搜索后移到 P11-B
- candidate batch / add-from-candidates 后移
- pause / resume / delete 后移
- 卡片正式交互后移
- PostgreSQL 不属于本轮范围

## 五、下一阶段候选方向（仅方向）

1. P11-B：discovery 搜索 + candidate batch  
2. P11-C：add-from-candidates 编号选择最小闭环  
3. P11-D：monitor 管理动作（pause/resume/delete）  
