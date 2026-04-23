# P11 交接文档

## 一、交接状态

- 阶段：P11-C（add-from-candidates 编号选择最小闭环）
- 状态：已收口，可演示
- 主线：A 负责飞书入口与文本回写，B 负责 discovery 与纳管业务服务

## 二、固定运行口径

- B 服务地址：`http://127.0.0.1:8005`
- A 调 B 返回协议：Envelope
  - success：`ok=true, data!=null, error=null`
  - failed：`ok=false, data=null, error={message/code/status_code/...}`
- A 不允许把 `response.json()` 当裸业务对象直接使用

## 三、固定验收样本（真实）

### 1) 无上下文失败样本
- 飞书原文：`加入监控第 2 个`
- task_id：`TASK-20260423-A74551`
- 回复原文：`加入监控失败：未找到最近一次搜索结果，请先发送“搜索商品：关键词”`

### 2) discovery 成功样本
- 飞书原文：`搜索商品：蓝牙耳机`
- task_id：`TASK-20260423-FFC984`
- 回复原文：
  - `搜索结果：蓝牙耳机`
  - `批次：8`
  - `候选（展示前 5 条）：`
    1. `藍牙耳機 - Fortress豐澤`
    2. `蓝牙耳机| 香港蘇寧SUNING`
    3. `小米耳機| 小米®香港官方商城 - Xiaomi`
    4. `AirPods - Apple (香港)`
    5. `2026年真無線藍牙耳機推薦！依用途精選13款高評價藍牙耳機`

### 3) 编号纳管成功样本
- 飞书原文：`加入监控第 2 个`
- task_id：`TASK-20260423-544156`
- 回复原文：
  - `已加入监控。`
  - `选择编号：第 2 个`
  - `名称：蓝牙耳机 | 香港蘇寧 SUNING`
  - `URL：https://search.hksuning.com/search/result?keyword=%E8%93%9D%E7%89%99%E8%80%B3%E6%9C%BA`
  - `对象ID：5`
  - `状态：active`

### 4) 联动验证样本
- 飞书原文：`看看当前监控对象`
- task_id：`TASK-20260423-6FAF67`
- 回复原文：
  - `当前监控对象（共 5 个）：`
  - `#1 Mock Phone X（inactive）`
  - `#2 Mock Headphone Pro（active）`
  - `#3 Mock Keyboard Mini（active）`
  - `#4 abc（active）`
  - `#5 蓝牙耳机 | 香港蘇寧 SUNING（active）`

## 四、边界与后移项

当前已确认：
- 发现 → 编号选择 → 正式纳管闭环已成立
- 无上下文失败路径已成立
- 当前未扩卡片交互
- 当前未做 pause / resume / delete
- 当前未切 PostgreSQL

后移项：
- P11-D：monitor 管理动作（pause/resume/delete）
- 卡片正式交互继续后移
- PostgreSQL 不属于当前范围

## 五、下一阶段候选方向（仅方向）

1. P11-D：monitor 管理动作（pause/resume/delete）
2. 飞书卡片正式交互
3. PostgreSQL 切换与回归验证
