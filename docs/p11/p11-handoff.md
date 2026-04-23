# P11 交接文档

## 一、交接状态

- 阶段：P11-B（discovery 搜索 + candidate batch）
- 状态：已收口，可演示
- 主线：A 负责飞书入口与文本回写，B 负责 discovery 业务服务

## 二、固定运行口径

- B 服务地址：`http://127.0.0.1:8005`
- A 调 B 返回协议：Envelope
  - success：`ok=true, data!=null, error=null`
  - failed：`ok=false, data=null, error={message/code/status_code/...}`
- A 不允许把 `response.json()` 当裸业务对象直接使用

## 三、固定验收样本（真实）

### 1) 成功样本
- 用户原文：`搜索商品：蓝牙耳机`
- task_id：`TASK-20260423-8089C1`
- 回复原文：
  - 搜索结果：蓝牙耳机
  - 批次：4
  - 候选（展示前 5 条）：
    1. 藍牙耳機 - Fortress豐澤
    2. 蓝牙耳机 | 香港蘇寧 SUNING
    3. 2026年蓝牙耳机选购指南，高性价比蓝牙耳机推荐（4月更新） - 知乎
    4. 小米耳機| 小米®香港官方商城 - Xiaomi
    5. 蓝牙耳机_百度百科

### 2) 失败样本
- 用户原文：`搜索商品：`
- task_id：`TASK-20260423-8765A3`
- 回复原文：`搜索失败：请输入搜索关键词`

### 3) 回归验证样本
- 用户原文：`今天有什么变化`
- 结果：查询链路正常

### 4) 联动验证样本
- 用户原文：`看看当前监控对象`
- 结果：P10 / P11-A 链路保持正常

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
