# P11 交接文档（P11-D 收口后）

## 一、交接状态

- 阶段：P11-D（monitor 管理动作：pause / resume / delete 最小闭环）
- 状态：已收口，可演示
- 主线分工（冻结）：
  - A：飞书入口层 / 消息编排层 / 老板交互层（文本回写）
  - B：业务服务层（targets / pause / resume / delete 等）

## 二、固定运行口径

- B 服务地址：`http://127.0.0.1:8005`
- A 调 B 返回协议：Envelope（必须显式解包）
  - success：`ok=true, data!=null, error=null`
  - failed：`ok=false, data=null, error={message/code/status_code/...}`
- A 不允许把 `response.json()` 当裸业务对象直接使用（必须先判断 `ok` 再取 `data`）

## 三、固定验收样本（真实，冻结）

### 1) 列表样本
- 飞书原文：`看看当前监控对象`
- task_id：`TASK-20260424-35D9F2`
- 回复原文：

  当前监控对象（共 5 个）：

  * 1. Mock Phone X（inactive，ID=1）
  * 2. Mock Headphone Pro（active，ID=2）
  * 3. Mock Keyboard Mini（inactive，ID=3）
  * 4. abc（active，ID=4）
  * 5. 蓝牙耳机 | 香港蘇寧 SUNING（active，ID=5）

### 2) 暂停成功样本
- 飞书原文：`暂停监控第 2 个`
- task_id：`TASK-20260424-240919`
- 回复原文：

  已暂停监控。

  * 选择编号：第 2 个
  * 名称：Mock Headphone Pro
  * 对象ID：2

### 3) 暂停后联动验证
- 飞书原文：`看看当前监控对象`
- task_id：`TASK-20260424-E20D19`
- 验证点：回复原文中第 2 个对象状态变为 `inactive`

### 4) 恢复成功样本
- 飞书原文：`恢复监控第 2 个`
- task_id：`TASK-20260424-219943`
- 回复原文：

  已恢复监控。

  * 选择编号：第 2 个
  * 名称：Mock Headphone Pro
  * 对象ID：2

### 5) 恢复后联动验证
- 飞书原文：`看看当前监控对象`
- task_id：`TASK-20260424-84BF42`
- 验证点：回复原文中第 2 个对象状态恢复 `active`

### 6) 失败样本（超范围编号）
- 飞书原文：`删除监控第 99 个`
- task_id：`TASK-20260424-5C0A5E`
- 回复原文：`操作失败：编号超出范围（当前最多 5 个）`

## 四、边界与后移项

当前已确认（冻结）：
- pause / resume / delete 最小闭环已成立
- 列表 → 编号管理 → 再看列表 的联动已成立
- 当前未扩卡片交互
- 当前未切 PostgreSQL
- 当前未回头改 P10 / P11-A / P11-B / P11-C 已收口链路

后移项（冻结）：
- 飞书卡片正式交互继续后移
- 更口语化编号命令（如“第二个”）可作为后续小优化
- PostgreSQL 不属于当前范围

## 五、下一阶段候选方向（仅方向，不开工）

按优先级（仅方向）：
1. 飞书卡片正式交互（在不改 A/B 分工的前提下提升交互）
2. 命令口径小优化（更口语化编号、容错）
3. PostgreSQL 切换与回归验证（不作为当前阶段前置）
