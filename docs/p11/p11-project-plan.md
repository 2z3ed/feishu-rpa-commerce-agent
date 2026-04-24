# P11 开发主线文档
## 当前阶段
P11-D：monitor 管理动作（pause / resume / delete）最小闭环

## 一、阶段定义

P11-D 不是继续做 add-by-url。
也不是继续做 discovery / candidate batch / add-from-candidates。
更不是直接做卡片交互、公网回调、PostgreSQL、共享数据库。

这一轮只做一件事：

让老板在飞书里对“已经纳管的对象”执行最小生命周期管理动作。

一句话定义：

老板在飞书里查看当前监控对象
→ 指定某个对象
→ 发暂停 / 恢复 / 删除命令
→ A 调 B 的 monitor 管理接口
→ A 返回老板可读结果
→ 再查看当前监控对象时能看到状态变化

## 二、为什么现在做这一轮

P10 已完成“可看”：
- 今天有什么变化
- 当前监控对象
- 商品详情

P11-A 已完成“直链纳管”：
- 给 URL
- 直接加入监控

P11-B 已完成“可发现”：
- 搜索商品
- 返回候选

P11-C 已完成“发现 → 编号纳管”：
- 搜索候选
- 选第 N 个
- 正式纳管

所以当前最自然的下一步，不是再扩发现能力，
而是补“已纳管对象如何管理”。

也就是：

- 暂停监控
- 恢复监控
- 删除（软删除/停用）

## 三、A / B 固定分工（必须继承）

### A 的定位
A 是飞书入口层、消息编排层、老板交互层。

A 负责：
- 接收飞书消息
- 解析老板意图
- 调用 B
- 把结果翻译成老板能看懂的文本

### B 的定位
B 是业务服务层。

B 负责：
- summary / detail / targets
- discovery
- add-by-url
- add-from-candidates
- pause / resume / delete
- 监控对象状态承载

### 当前原则
- 不把 A / B 合并成一个项目
- A 继续作为飞书入口层
- B 继续作为业务服务层
- A 调 B 必须按 Envelope 解包
- A 不直接操作 B 数据库

## 四、本轮唯一目标

本轮唯一目标是打通以下 3 个动作：

- POST /internal/monitor/{id}/pause
- POST /internal/monitor/{id}/resume
- DELETE /internal/monitor/{id}

形成最小闭环：

老板先在飞书里发：
- 看看当前监控对象

A 返回对象列表。

老板再发：
- 暂停监控第 N 个
或
- 恢复监控第 N 个
或
- 删除监控第 N 个

A 从当前会话里取最近一次 monitor targets 列表映射，
把第 N 个映射成 monitor target / product id，
再调用 B 对应管理接口，
最后把成功 / 失败结果返回给老板。

## 五、本轮固定范围（必须收窄）

### 只做 3 个管理动作
固定只做：
- pause
- resume
- delete

### 只依赖最近一次“当前监控对象”结果
本轮只允许：
- 基于当前会话中最近一次成功 monitor/targets 列表
- 做最小编号选择

### 只做飞书文本回复
本轮不做：
- 卡片按钮
- 列表分页
- 多轮复杂会话状态机

### 只做最小命令口径
查看列表命令继续沿用：
- 看看当前监控对象
- 当前监控哪些商品
- 监控列表

管理命令本轮固定只做：
- 暂停监控第 1 个
- 恢复监控第 1 个
- 删除监控第 1 个
- 暂停第 1 个
- 恢复第 1 个
- 删除第 1 个

### 只解析两个字段
- action（pause / resume / delete）
- index

### 继续按 Envelope 解包
成功：
- ok=true
- data=...
- error=null

失败：
- ok=false
- data=null
- error={...}

## 六、本轮明确不做什么

本轮不做：

- 不做 add-by-url 扩展
- 不做 discovery 扩展
- 不做 add-from-candidates 扩展
- 不做卡片正式交互
- 不做多页翻页
- 不做复杂状态机
- 不做共享数据库
- 不切 PostgreSQL
- 不回头改 P10 / P11-A / P11-B / P11-C 已收口链路

## 七、本轮开发拆分

### P11-D.0：管理动作锚定
确认：
- pause / resume / delete 三个接口是否可调用
- success / failed Envelope 长什么样
- targets 列表里最小字段有哪些
- A 当前最适合把“最近一次 targets 列表上下文”存在哪里

### P11-D.1：最小 targets 上下文接入
只做：
- 保存最近一次 monitor targets 列表
- 保存序号到对象 ID 的最小映射
- 只对当前会话生效

### P11-D.2：管理命令接入
只做：
- 暂停监控第 N 个
- 恢复监控第 N 个
- 删除监控第 N 个
- 暂停第 N 个
- 恢复第 N 个
- 删除第 N 个

### P11-D.3：调用 B 管理接口
A 需要：
- 根据 index 找到最近 targets 中的对象
- 根据 action 决定调用 pause / resume / delete
- 解包 Envelope
- 返回老板可读成功 / 失败文本

### P11-D.4：最小实机验收
只验证：

成功样本：
- 看看当前监控对象
- 暂停监控第 2 个
- 看看当前监控对象（确认状态变化）
- 恢复监控第 2 个
- 看看当前监控对象（确认状态恢复）

失败样本至少 1 条：
- 没有最近 targets 上下文时直接发“暂停监控第 2 个”
或
- 选超出范围的编号

## 八、建议实现位置

### 1. 继续复用现有 b_client
继续在：
- app/clients/b_service_client.py

新增最小方法，例如：
- pause_monitor_target(target_id)
- resume_monitor_target(target_id)
- delete_monitor_target(target_id)

### 2. 继续在 A 的意图层识别
沿用：
- resolve_intent

增加一个最小意图，例如：
- ecom_watch.manage_monitor_target

### 3. 继续在 A 的执行层处理
沿用：
- execute_action

### 4. 最小上下文保存位置
本轮建议：
- 只保存“最近一次 targets 列表 → 编号映射”
- 不做复杂长期记忆

## 九、本轮最低通过标准

1. A 能调通 B 的 pause / resume / delete
2. A 能利用最近一次 targets 结果做编号选择
3. 飞书里至少有 1 条真实 pause 或 resume 成功样本
4. 至少有 1 条老板可读失败文本成立
5. 再看“当前监控对象”时能看到状态变化
6. 不破坏 P10 / P11-A / P11-B / P11-C 已收口链路

## 十、固定真实样本（冻结）

列表样本：
- 飞书原文：`看看当前监控对象`
- task_id：`TASK-20260424-35D9F2`
- 回复原文：

  当前监控对象（共 5 个）：

  * 1. Mock Phone X（inactive，ID=1）
  * 2. Mock Headphone Pro（active，ID=2）
  * 3. Mock Keyboard Mini（inactive，ID=3）
  * 4. abc（active，ID=4）
  * 5. 蓝牙耳机 | 香港蘇寧 SUNING（active，ID=5）

暂停成功样本：
- 飞书原文：`暂停监控第 2 个`
- task_id：`TASK-20260424-240919`
- 回复原文：

  已暂停监控。

  * 选择编号：第 2 个
  * 名称：Mock Headphone Pro
  * 对象ID：2

暂停后联动验证：
- 飞书原文：`看看当前监控对象`
- task_id：`TASK-20260424-E20D19`
- 验证点：回复原文中第 2 个对象状态变为 `inactive`

恢复成功样本：
- 飞书原文：`恢复监控第 2 个`
- task_id：`TASK-20260424-219943`
- 回复原文：

  已恢复监控。

  * 选择编号：第 2 个
  * 名称：Mock Headphone Pro
  * 对象ID：2

恢复后联动验证：
- 飞书原文：`看看当前监控对象`
- task_id：`TASK-20260424-84BF42`
- 验证点：回复原文中第 2 个对象状态恢复 `active`

失败样本（超范围编号）：
- 飞书原文：`删除监控第 99 个`
- task_id：`TASK-20260424-5C0A5E`
- 回复原文：`操作失败：编号超出范围（当前最多 5 个）`

## 十一、后移项（冻结）

- 飞书卡片正式交互继续后移
- 更口语化编号命令（如“第二个”）可作为后续小优化
- PostgreSQL 不属于当前范围

## 十二、下一阶段候选方向（仅方向，不开工）

按优先级（仅方向）：
1. 飞书卡片正式交互
2. 命令口径小优化（更口语化编号、容错）
3. PostgreSQL 切换与回归验证