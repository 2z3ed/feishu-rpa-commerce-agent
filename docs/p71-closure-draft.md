# P71 收口文档草稿：影刀受控页面最小执行链（`warehouse.adjust_inventory`）

> 状态：草稿（用于收口前稳定化对齐）。  
> 固定动作：仅 `warehouse.adjust_inventory`。  
> 固定边界：受控页面、非生产接入；不接真实 Odoo 生产页面；不接影刀控制台/API Key/Flow；不让飞书直接触发影刀。

---

## 1. 已完成（截至 P71 第三轮）

- **controlled_page 模式成立**：bridge 可在非生产环境驱动“受控库存调整页”的最小流程。
- **页面证据字段成立并可取证**：新增 `page_url/page_profile/page_steps/page_evidence_count/page_failure_code` 可从 bridge 透传到 `parsed_result`，最终进入 `/steps action_executed.detail`。
- **失败语义稳定**：`page_failure_code -> failure_layer/operation_result/verify_reason` 映射表固定且有测试覆盖。
- **固定回归样本成立**：
  - `success`
  - `timeout (page_timeout)`
  - `page_failure (element_missing)`
  - `verify_fail`
- **回放入口成立**：脚本支持 `--task-id` 生成单样本页面证据摘要与 `/steps` 对照项（人工核查用）。

---

## 2. 未完成（明确不在 P71 内做）

- 未扩第二个动作（冻结边界）。
- 未接真实 Odoo 生产页面（冻结边界）。
- 未接影刀控制台 / API Key / Flow（冻结边界）。
- 未让飞书直接触发影刀（冻结边界）。
- 未做正式生产接入（冻结边界）。

---

## 3. 仍然不是正式生产接入

原因：

- 页面目标是 **internal sandbox / 受控测试页**，不是生产后台。
- 执行链路用于验证“桥接 + 页面执行 + 证据留痕”的最小闭环，不包含生产权限、生产网络、安全与运维门禁。

---

## 4. 页面执行边界（P71）

- 仅验证最小操作流（打开 -> 定位 -> 输入 -> 提交 -> 读取回显）。
- 失败语义仅固定到最小集合（`element_missing` / `page_timeout`）。
- 页面证据以“可核查字段 + 最小 steps 对照项”为主，不引入复杂回放系统。

---

## 5. 收口判定建议（待正式收口时填写）

当满足以下条件可判 P71 收口：

- controlled_page 执行链稳定回归通过
- 三/四类固定样本回归稳定（success/timeout/page_failure/verify_fail）
- 页面证据字段与 `/steps` 一致性不回归
- 文档、脚本、测试资产齐备且可交接复验
