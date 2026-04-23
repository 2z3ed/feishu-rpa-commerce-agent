# P11 开发主线文档
## 当前阶段
P11-C：add-from-candidates 编号选择最小闭环（已收口）

## 一、阶段结论

P11-C 已通过并收口，闭环已成立：

老板在飞书里发搜索词
→ A 调 B 完成 discovery 并返回候选列表
→ 老板发“加入监控第 N 个”
→ A 从最近一次 discovery 上下文读取 batch_id + 编号映射
→ A 调 B：`POST /internal/monitor/add-from-candidates`
→ A 按 Envelope 解包并返回老板可读结果
→ “看看当前监控对象”可见新增对象

本阶段明确成立：
- 发现 → 编号选择 → 正式纳管闭环已成立
- 无上下文失败路径已成立
- A/B 分层边界保持不变（A 入口与编排，B 业务服务）

## 二、固定真实样本（冻结）

### 1) 无上下文失败样本
- 飞书原文：`加入监控第 2 个`
- task_id：`TASK-20260423-A74551`
- 回复原文：
  - `加入监控失败：未找到最近一次搜索结果，请先发送“搜索商品：关键词”`

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

## 三、本阶段范围确认

本阶段已完成：
- `POST /internal/monitor/add-from-candidates` 接入
- 最近一次 discovery 上下文最小绑定
- 飞书编号命令最小口径接入（只解析 `index`）
- 成功/失败文本回写成型
- 实机闭环样本冻结

本阶段明确未做：
- 卡片交互
- candidate 多页翻页
- pause / resume / delete
- PostgreSQL 切换

## 四、后移项（冻结）

- P11-D：monitor 管理动作（pause/resume/delete）
- 卡片正式交互继续后移
- PostgreSQL 不属于当前范围

## 五、下一阶段候选方向（仅方向，不开工）

1. P11-D：monitor 管理动作（pause/resume/delete）  
2. 飞书卡片正式交互（基于已收口文本链路升级）  
3. PostgreSQL 切换与回归验证（独立阶段推进）  