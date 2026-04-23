# P11 开发主线文档（已收口）
## 阶段名称
P11：A 接 B 纳管最小闭环

## 一、阶段结论

P11-A（从 URL 直接加入监控）已通过，当前阶段收口。

本轮已完成闭环：

- 飞书命令进入 A
- A 识别 URL 加监控意图
- A 调 B：`POST /internal/monitor/add-by-url`
- A 按 Envelope（`ok/data/error`）解包
- A 回写老板可读文本
- “看看当前监控对象”可看到新增对象
- P10 查询链路未被破坏

## 二、固定样本（冻结）

### 1) 成功样本（P11-A 主样本）
- 用户原文：`监控这个商品：https://example.com/product/abc`
- task_id：`TASK-P11A-SUCC-002`
- message_id：`om_x100b5195ddb2a8acc37bf94e86bee96`
- 飞书回复原文：
  - 已加入监控。
  - URL：https://example.com/product/abc
  - 名称：abc
  - 对象ID：4
  - 状态：active

### 2) 失败样本（P11-A 失败分支）
- 用户原文：`监控这个商品：not-a-url`
- task_id：`TASK-P11A-FAIL-002`
- message_id：`om_x100b5195dd466ca0c33b9aaee23cab5`
- 飞书回复原文：
  - 加入监控失败：B 服务错误：invalid url: only http/https/mock:// are supported (code=HTTP_400, status=400)

### 3) 联动验证样本
- 用户原文：`看看当前监控对象`
- task_id：`TASK-P11A-P10T-002`
- 结果：列表中已出现 `#4 abc（active）`

### 4) P10 回归样本
- 用户原文：`今天有什么变化`
- task_id：`TASK-P11A-P10S-002`
- 结果：查询链路正常返回“今日监控摘要”

## 三、当前范围边界（冻结）

本轮只做并已完成：
- `POST /internal/monitor/add-by-url`
- 飞书文本回复闭环

本轮明确不做且继续后移：
- discovery 搜索
- candidate batch / add-from-candidates
- pause / resume / delete
- 卡片正式交互
- PostgreSQL 切换

## 四、后移项（下一阶段再做）

1. discovery 搜索继续后移到 P11-B  
2. candidate batch / add-from-candidates 继续后移  
3. pause / resume / delete 继续后移  
4. 卡片正式交互继续后移  
5. PostgreSQL 不属于本轮范围  

## 五、下一阶段候选方向（只列方向，不开工）

1. **P11-B：discovery 搜索 + candidate batch**  
   原因：先补“发现候选”的上游能力，为后续编号纳管建立输入。

2. **P11-C：add-from-candidates 编号选择最小闭环**  
   原因：把 discovery 候选转为实际纳管动作，形成“先发现再纳管”闭环。

3. **P11-D：monitor 管理动作（pause/resume/delete）**  
   原因：属于存量对象生命周期管理，价值在纳管闭环之后。