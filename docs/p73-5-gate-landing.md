# P73 开发第二轮：留痕字段最小落点

> 状态：开发落地说明。  
> 范围：仅 `warehouse.adjust_inventory`。  
> 本轮只做门禁结果的最小留痕落点，不扩字段体系，不重做 `/tasks` / `/steps`。

## 本轮确认的输入边界

- 门禁输入边界采用：`sku + (delta 或 target_inventory)`
- 这与当前单动作主线一致：
  - `sku` 必须存在
  - `delta` 可以直接提供
  - 如果已有 `target_inventory`，也允许作为最小门禁输入的一部分
- `sku` 缺失仍然拦截
- `delta` 和 `target_inventory` 同时缺失时拦截

## 本轮做了什么

- 保留 `app/graph/nodes/execute_action.py` 中的门禁入口。
- 让门禁结果以最小字段进入现有 `action_executed` 详情链路：
  - `gate_allow`
  - `gate_status`
  - `gate_reason`
- 未重做 `/tasks` / `/steps` 结构。
- 未扩展新的治理字段体系。

## 为什么只做这些字段

- 这三个字段足以表达最小门禁结论。
- 继续扩字段会开始偏离“最小落点”。
- 现阶段的目标是把门禁、留痕、回放串起来，而不是建立完整治理模型。

## 没做什么

- 没有扩第二个动作。
- 没有接真实 Odoo 生产页面。
- 没有接影刀控制台 / API Key / Flow。
- 没有让飞书直接触发影刀。
- 没有做正式生产接入。
- 没有做大重构。
- 没有重做 `/tasks` / `/steps`。
- 没有一次性扩很多治理字段。

## 如何手动验证

- 只提供 `sku`，且 `delta` 与 `target_inventory` 都缺失时，应被门禁拦截。
- 提供 `sku` + `delta` 时，应允许继续。
- 提供 `sku` + `target_inventory` 时，应允许继续。
- `action_executed` 详情中应能看到 `gate_allow`、`gate_status`、`gate_reason`。
