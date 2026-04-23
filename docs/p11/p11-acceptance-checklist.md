# P11 验收清单

## 一、范围验收

- [x] 只做 add-by-url
- [x] 未接 discovery 搜索
- [x] 未接 candidate batch
- [x] 未接 add-from-candidates
- [x] 未做 pause / resume / delete
- [x] 未做卡片正式交互
- [x] 未切 PostgreSQL
- [x] 未改 P10 已收口边界

## 二、B 服务验收

- [x] B 运行在 127.0.0.1:8005
- [x] POST /internal/monitor/add-by-url 可调用
- [x] A 能访问 B
- [x] 成功 / 失败 Envelope 均可处理

## 三、Envelope 验收

- [x] A 没有假设裸对象返回
- [x] A 能处理 ok=true
- [x] A 能处理 ok=false
- [x] A 能把失败翻译成老板可读文本

## 四、飞书前台验收

- [x] 飞书里支持 URL 加入监控命令
- [x] 成功时飞书能返回老板可读文本
- [x] 失败时飞书能返回老板可读文本
- [x] 不返回 Python 堆栈

## 五、联动验收

- [x] add-by-url 成功后，B 中新增正式监控对象
- [x] 如继续执行“看看当前监控对象”，新增对象可见（若 B 返回语义允许）
- [x] 不破坏 P10 查询链路

## 六、边界验收

- [x] A 仍是飞书入口层
- [x] B 仍是业务服务层
- [x] 未把 A / B 合并成一个项目
- [x] 未让 B 长期承担飞书入口角色

## 七、固定样本验收（冻结）

- [x] 成功样本原文：`监控这个商品：https://example.com/product/abc`
- [x] 成功样本 task_id：`TASK-P11A-SUCC-002`
- [x] 成功样本 message_id：`om_x100b5195ddb2a8acc37bf94e86bee96`
- [x] 成功回复原文包含：
  - 已加入监控。
  - URL：https://example.com/product/abc
  - 名称：abc
  - 对象ID：4
  - 状态：active
- [x] 失败样本原文：`监控这个商品：not-a-url`
- [x] 失败样本 task_id：`TASK-P11A-FAIL-002`
- [x] 失败样本 message_id：`om_x100b5195dd466ca0c33b9aaee23cab5`
- [x] 失败回复原文：
  - 加入监控失败：B 服务错误：invalid url: only http/https/mock:// are supported (code=HTTP_400, status=400)
- [x] 联动验证样本：`看看当前监控对象`
  - task_id：`TASK-P11A-P10T-002`
  - 列表中出现：`#4 abc（active）`
- [x] P10 回归样本：`今天有什么变化`
  - task_id：`TASK-P11A-P10S-002`