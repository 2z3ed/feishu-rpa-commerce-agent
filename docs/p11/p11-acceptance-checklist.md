# P11-D 验收清单

## 一、范围验收

- [x] 只做 pause / resume / delete
- [x] 只依赖最近一次 targets 列表
- [x] 未做卡片交互
- [x] 未做分页
- [x] 未做复杂状态机
- [x] 未做 add-by-url / discovery / add-from-candidates 扩展
- [x] 未切 PostgreSQL
- [x] 未改 P10 / P11-A / P11-B / P11-C 已收口边界

## 二、B 服务验收

- [x] B 运行在 127.0.0.1:8005
- [x] pause 可调用
- [x] resume 可调用
- [x] delete 可调用
- [x] A 能访问 B
- [x] success / failed Envelope 均可处理

## 三、上下文验收

- [x] A 能保存最近一次 targets 列表
- [x] A 能保存序号到对象 ID 的最小映射
- [x] 只对当前会话生效
- [x] 无上下文/超范围时能给出老板可读失败文本

## 四、飞书前台验收

- [x] 飞书里能先看到当前监控对象列表
- [x] 飞书里能发“暂停监控第 N 个 / 恢复监控第 N 个 / 删除监控第 N 个”
- [x] 成功时飞书能返回老板可读成功文本
- [x] 失败时飞书能返回老板可读失败文本
- [x] 不返回 Python 堆栈
- [x] 不返回原始 JSON

## 五、联动验收

- [x] pause / resume / delete 成功后，列表状态能反映变化
- [x] 至少 1 条管理动作成功样本成立
- [x] 至少 1 条失败样本成立
- [x] 不破坏 P10 / P11-A / P11-B / P11-C 已收口链路

## 六、边界验收

- [x] A 仍是飞书入口层
- [x] B 仍是业务服务层
- [x] 未把 A / B 合并成一个项目
- [x] 未让 B 长期承担飞书入口角色

## 七、固定真实样本（冻结）

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

失败样本：
- 飞书原文：`删除监控第 99 个`
- task_id：`TASK-20260424-5C0A5E`
- 回复原文：`操作失败：编号超出范围（当前最多 5 个）`