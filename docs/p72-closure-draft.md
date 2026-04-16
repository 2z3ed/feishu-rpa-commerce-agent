# P72 收口文档草稿：更真实后台形态的受控库存验证（`warehouse.adjust_inventory`）

> 状态：草稿（用于 P72 收口前最后校验）。  
> 固定动作：仅 `warehouse.adjust_inventory`。  
> 固定边界：受控页面、非生产接入；不接真实 Odoo 生产页面；不接影刀控制台/API Key/Flow；不让飞书直接触发影刀。

---

## 1. 已完成（截至 P72 第四轮准备）

- **更真实受控页面已落地**：具备入口页、侧边导航、SKU 搜索、列表、编辑抽屉、提交回显。
- **controlled_page 已对齐新流程**：
  - `page_url` 指向库存概览入口页
  - `page_profile` 使用 `internal_inventory_admin_like_v1`
  - `page_steps` 覆盖入口/导航/列表/抽屉/提交/回显
- **固定样本可验证**：
  - `success`
  - `element_missing`
  - `page_timeout`
  - `verify_fail`
- **页面字段兼容旧口径**：`operation_result/verify_passed/verify_reason/failure_layer/raw_result_path/rpa_vendor` 语义保持不变，`page_*` 字段稳定进入 `/steps`。
- **人工演练清单已具备**：可用 `--task-id` 回放输出与 `/steps action_executed.detail` 做一一对照。

---

## 2. 未完成（明确不在 P72 内做）

- 未扩第二个动作。
- 未接真实 Odoo 生产页面。
- 未接影刀控制台 / API Key / Flow。
- 未让飞书直接触发影刀。
- 未做正式生产接入（权限/网络/安全/运维门禁）。
- 未新增失败码类别。

---

## 3. 仍然不是正式生产接入

原因：

- 页面目标仍是 internal sandbox 受控页面，不是生产后台。
- 执行链路仍用于“页面复杂度验证 + 证据留痕 + 回放核查”，不包含生产级账号、网络、权限和运维保障。

---

## 4. P72 收口判定条件（固定）

满足以下条件可判 P72 收口：

1. 更真实受控页面 happy path 成立。
2. `element_missing` 语义稳定（映射不漂移）。
3. `page_timeout` 固定回归稳定。
4. `verify_fail` 固定回归稳定。
5. `page_url/page_profile/page_steps` 稳定进入 `/steps action_executed.detail`。
6. 仍保持非生产接入边界。
7. 未扩第二动作。
8. 未接控制台/API/Flow。

---

## 5. 回归矩阵（稳定）

| 用例 | 触发方式 | 关键断言 |
|---|---|---|
| success | `--sample success` | `operation_result=write_adjust_inventory` + `verify_passed=True` |
| element_missing | `--sample page_failure` | `page_failure_code=element_missing` + `failure_layer=bridge_page_failed` |
| page_timeout | `--sample timeout` | `page_failure_code=page_timeout` + `failure_layer=bridge_timeout` |
| verify_fail | `--sample verify_fail` | `operation_result=write_adjust_inventory_verify_failed` + `failure_layer=verify_failed` |
| 旧主线不回归 | 运行 P6.1/P6.2/P70/P71/P72 关键回归 | 既有口径与测试仍通过 |

---

## 6. 后续主线入口（收口后）

P72 收口后建议先进入“收口评审/判定”，确认可正式收口；再评估下一阶段是否进入更严格的非生产门禁准备或更接近真实页面的受控演练深化（仍不等于生产接入）。

---

## 7. 提交范围清理（必须遵守）

明确排除：

- `feishu_rpa.db`
- `tmp/*`
- 其它无关临时产物

建议本轮仅提交：

- `docs/p72-realistic-controlled-inventory-page.md`
- `docs/p72-closure-draft.md`

