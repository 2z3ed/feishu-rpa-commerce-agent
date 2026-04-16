# P73 开发第一轮：门禁检查入口

> 状态：开发落地说明。  
> 范围：仅 `warehouse.adjust_inventory`。  
> 本轮只做门禁检查入口的最小落地，不扩第二动作，不接生产，不做大重构。

## 本轮做了什么

- 在 `app/graph/nodes/execute_action.py` 中，为 `warehouse.adjust_inventory` 增加了最小门禁检查入口。
- 门禁位置放在动作分支进入最小确认流之前，先判断 `sku` 与 `delta` 是否满足最小执行条件。
- 门禁结果以最小方式回写到现有状态链中：
  - `gate_allow`
  - `gate_status`
  - `gate_reason`
  - 失败时复用 `parsed_result` 与 `error_message`
- 未改动 `/tasks` 与 `/steps` 的结构。
- 未改动 confirm 唯一放行语义。

## 没做什么

- 没有扩第二个动作。
- 没有接真实 Odoo 生产页面。
- 没有接影刀控制台 / API Key / Flow。
- 没有让飞书直接触发影刀。
- 没有做正式生产接入。
- 没有做大重构。
- 没有一次性实现留痕字段、样本矩阵、升级准入。

## 如何手动验证

- 缺少 `sku` 时，`warehouse.adjust_inventory` 应被门禁拦截。
- 缺少 `delta` 时，`warehouse.adjust_inventory` 应被门禁拦截。
- 同时提供 `sku` 和 `delta` 时，应继续进入原有高风险确认流。
- 现有 confirm 回归样本应保持兼容。
