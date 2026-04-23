# P11 老板演示 SOP

## 一、演示目标

让老板在飞书里直接体验（P11-A 已通过版）：

发一个商品 URL
→ 系统把它加入监控
→ 飞书返回成功或失败结果
→ 如需要，再查看当前监控对象确认新增已生效

## 二、演示固定样本

成功样本固定发送：

- 监控这个商品：https://example.com/product/abc

失败样本固定发送：

- 监控这个商品：not-a-url

联动验证可追加发送：

- 看看当前监控对象

P10 回归可追加发送：

- 今天有什么变化

## 三、演示前准备

1. 启动 A 主系统
2. 启动 A 的飞书 listener
3. 启动 B 服务
4. 确认 B 运行在 127.0.0.1:8005
5. 确认 B 的 POST /internal/monitor/add-by-url 可调用
6. 确认 A → B HTTP 调用可用
7. 确认 Envelope 解包正常

## 四、演示步骤

### 第一步：发送成功样本
发送：
- 监控这个商品：https://example.com/product/abc

### 第二步：展示飞书返回
预期至少包含：

- 已加入监控
- URL
- 名称或对象信息（若返回）

参考冻结样本：
- task_id：`TASK-P11A-SUCC-002`
- message_id：`om_x100b5195ddb2a8acc37bf94e86bee96`
- 回复：
  - 已加入监控。
  - URL：https://example.com/product/abc
  - 名称：abc
  - 对象ID：4
  - 状态：active

### 第三步：发送失败样本
发送：
- 监控这个商品：not-a-url

预期返回：
- 加入监控失败
- 原因可读
- 不出现 Python 堆栈

参考冻结样本：
- task_id：`TASK-P11A-FAIL-002`
- message_id：`om_x100b5195dd466ca0c33b9aaee23cab5`
- 回复：
  - 加入监控失败：B 服务错误：invalid url: only http/https/mock:// are supported (code=HTTP_400, status=400)

### 第四步：联动验证新增对象
在飞书里发送：

看看当前监控对象

预期飞书返回：
- 当前监控对象列表
- 能看到 `#4 abc（active）`

参考冻结样本：
- task_id：`TASK-P11A-P10T-002`

### 第五步：P10 回归验证
在飞书里发送：

今天有什么变化

参考冻结样本：
- task_id：`TASK-P11A-P10S-002`

## 五、演示成功标准

1. 飞书 URL 命令能进入 A
2. A 能真实调到 B 的 add-by-url
3. A 能正确解包 Envelope
4. 飞书里能看到成功或失败文本
5. “看看当前监控对象”里能看到 `#4 abc（active）`
6. “今天有什么变化”仍可正常返回