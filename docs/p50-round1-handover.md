# P5.0 第一轮交接（骨架验证）

## 已完成
- 建立多平台骨架可识别：`woo` / `odoo` / `chatwoot`。
- 保持 Woo 深度样板链可用（`product.query_sku_status`、`product.update_price + confirm` 未变更语义）。
- 接入最小 readonly 骨架动作：
  - `warehouse.query_inventory`（Odoo）
  - `customer.list_recent_conversations`（Chatwoot）
- 新增统一 readiness 查询入口（P5.0 统一口径）：
  - 推荐入口：`GET /api/v1/internal/readiness/unified-provider?provider=...&capability=...`
  - 兼容入口：`GET /api/v1/internal/readiness/provider?provider=...&capability=...`
  - 旧接口保留：`GET /api/v1/internal/readiness/query-sku-provider?provider=...`（偏旧 Woo 语义，仅兼容）

## 本轮新增 intent
- `warehouse.query_inventory`
- `customer.list_recent_conversations`

> 以上 intent 仅用于 P5.0 骨架验证最小动作，不代表最终系统全量语义冻结。

## 手动验收证据（P5.0 Round1）

> 说明：以下证据来自已存在的 3 条手动任务（不重复触发），重点展示 `/api/v1/tasks/{task_id}`、`/api/v1/tasks/{task_id}/steps` 中的关键字段、`action_executed.detail` 的多平台同形状字段、以及 `result_summary` 的真实形态。

### Woo（样板链）任务
- **触发命令**：查 SKU A001 状态
- **task_id**：`TASK-P50-MANUAL-20260413-232625-WOO-SUCCESS`
- **/api/v1/tasks/{task_id} 关键返回**
  - `status`: `succeeded`
  - `intent_text`: `查 SKU A001 状态`
  - `result_summary`（节选）：
    - `[product.query_sku_status] SKU: A001`
    - `状态：active`
    - `库存：128`
    - `价格：59.9`
- **/api/v1/tasks/{task_id}/steps 关键返回**
  - `intent_resolved`: `intent=product.query_sku_status`
  - `action_executed.detail` 关键字段（节选，同形状字段存在）：
    - `provider_id=mock`
    - `capability=product.query_sku_status`
    - `readiness_status=n/a`
    - `endpoint_profile=mock_repo_v1`
    - `session_injection_mode=none`

### Odoo（最小 readonly）任务
- **触发命令**：查 Odoo 里 SKU A001 的库存
- **task_id**：`TASK-P50-MANUAL-20260413-232603-02-ODOO`
- **/api/v1/tasks/{task_id} 关键返回**
  - `status`: `succeeded`
  - `result_summary`（节选）：
    - `[warehouse.query_inventory] SKU: A001`
    - `库存：120`
    - `平台：odoo`
    - `provider_id：odoo`
    - `capability：warehouse.query_inventory`
- **/api/v1/tasks/{task_id}/steps 关键返回**
  - `intent_resolved`: `intent=warehouse.query_inventory`
  - `action_executed.detail` 关键字段（节选，同形状字段存在）：
    - `provider_id=odoo`
    - `capability=warehouse.query_inventory`
    - `readiness_status=ready`
    - `endpoint_profile=odoo_product_stock_v1`
    - `session_injection_mode=header`

### Chatwoot（最小 readonly）任务
- **触发命令**：查 Chatwoot 最近 5 个会话
- **task_id**：`TASK-P50-MANUAL-20260413-232603-03-CHATWOOT`
- **/api/v1/tasks/{task_id} 关键返回**
  - `status`: `succeeded`
  - `result_summary`（节选）：
    - `[customer.list_recent_conversations] 平台：chatwoot`
    - `最近会话数：5 (limit=5)`
    - `最新会话ID：123`
    - `provider_id：chatwoot`
    - `capability：customer.list_recent_conversations`
- **/api/v1/tasks/{task_id}/steps 关键返回**
  - `intent_resolved`: `intent=customer.list_recent_conversations`
  - `action_executed.detail` 关键字段（节选，同形状字段存在）：
    - `provider_id=chatwoot`
    - `capability=customer.list_recent_conversations`
    - `readiness_status=ready`
    - `endpoint_profile=chatwoot_recent_conversations_v1`
    - `session_injection_mode=header`

## 当前未完成
- 未扩展更多 Odoo / Chatwoot 业务动作。
- 未进入真实生产写链与登录自动化。
- 未进入 P5.1 深化阶段。
- 未把“Woo 样板链的 provider_id/readiness_status”等字段在所有执行模式下都强绑定到 `woo`（当前以实际执行模式输出为准）。

## 下一步（仍在 P5.0 范围）
- 保持“只扩骨架不做深挖”，继续完善统一 readiness、路由口径和最小可观测性。
- 继续补齐多平台字段口径的自动化回归（尤其是 tasks list/detail/steps + action_executed.detail 的稳定性）。
