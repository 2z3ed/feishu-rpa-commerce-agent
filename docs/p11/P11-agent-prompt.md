# P11 当前阶段约束文档（Agent 必须先读）

你现在接手的是 feishu-rpa-commerce-agent 项目。

当前主线已经完成收口，不要误判阶段目标。

## 一、当前真实状态（冻结）

当前阶段结论：

P11-C：add-from-candidates 编号选择最小闭环 **已通过并收口**。

已成立：
- 发现 → 编号选择 → 正式纳管闭环已成立
- 无上下文失败路径已成立
- A/B 分工未破坏

## 二、固定分工（继续继承）

A 负责：
- 飞书入口
- 意图识别
- 最小会话上下文
- 调用 B
- 老板可读文本回写

B 负责：
- discovery
- candidate_batches / candidate_items
- add-from-candidates
- add-by-url
- summary / detail / targets
- 管理动作

不要把 A/B 合并成一个项目。

## 三、固定运行口径

- B 服务地址：`http://127.0.0.1:8005`
- A 调 B 必须按 Envelope 解包：`ok/data/error`
- 当前前台形态仍为飞书文本回复

## 四、固定样本（本阶段冻结）

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

## 五、当前明确不要做

- 不再改 P11-C 业务逻辑
- 不做卡片交互
- 不做分页
- 不做 pause / resume / delete
- 不切 PostgreSQL
- 不开新主线代码开发

## 六、后移项

- P11-D：monitor 管理动作（pause/resume/delete）
- 卡片正式交互继续后移
- PostgreSQL 不属于当前范围

## 七、下一阶段候选方向（仅方向，不开工）

1. P11-D：monitor 管理动作（pause/resume/delete）
2. 飞书卡片正式交互
3. PostgreSQL 切换与回归验证