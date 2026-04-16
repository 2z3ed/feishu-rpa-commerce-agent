# P71 收口文档（准备版）：影刀受控页面最小执行链（`warehouse.adjust_inventory`）

> 状态：准备版（P71 收口前最后校验用；通过后可直接判收口）。  
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

---

## 6. 端到端人工演练清单（回放输出 vs `/steps` 对照）

目标：用脚本回放输出（`task_id_replay`）与真实接口 `/tasks/{confirm_task_id}/steps` 的 `action_executed.detail` 做一一对照。

### 6.1 前置环境（非生产）

- 仍只围绕 `warehouse.adjust_inventory`
- 不接真实 Odoo 生产页面，不接影刀控制台/API/Flow
- 推荐环境变量（示例）：

```bash
export ODOO_ADJUST_INVENTORY_CONFIRM_EXECUTION_BACKEND=yingdao_bridge
export YINGDAO_BRIDGE_EXECUTION_MODE=controlled_page
export YINGDAO_CONTROLLED_PAGE_BASE_URL=http://127.0.0.1:8000
```

### 6.2 覆盖样本（至少三类，尽量四类）

1. `success`
2. `page_failure (element_missing)`
3. `timeout (page_timeout)`
4. `verify_fail`（尽量带上）

### 6.3 回放命令（示例）

以 `success` 为例（其它样本替换 `--sample` 即可）：

```bash
python script/p70_yingdao_bridge_rehearsal.py --sample success --task-id TASK-MANUAL-1 --confirm-task-id TASK-MANUAL-CFM-1
```

关注输出中的 `task_id_replay` 字段：

- `task_id_replay.actual.*`：桥接实际输出（包含页面字段）
- `task_id_replay.steps_checklist`：应当在 `/steps action_executed.detail` 中可核查的字段清单

### 6.4 `/steps` 对照（示例）

```bash
curl -s "http://127.0.0.1:8000/api/v1/tasks/TASK-MANUAL-CFM-1/steps"
```

找到 `step_code=action_executed` 的那一条，拿到 `detail`（KV 串）。

### 6.5 固定对照项（必须一致）

以下字段必须在 `detail` 中出现且语义一致（按 `steps_checklist` 核查）：

- 旧字段（P6/P70 口径，不可漂）：
  - `operation_result`
  - `verify_passed`
  - `verify_reason`
  - `failure_layer`
  - `raw_result_path`
  - `rpa_vendor`
  - `confirm_task_id`
  - `target_task_id`
- 页面证据字段（P71 口径）：
  - `page_url`
  - `page_profile`
  - `page_steps`（`|` 拼接）
  - `page_evidence_count`
  - `page_failure_code`

### 6.6 样本预期核对要点

- `success`：`page_failure_code` 为空或缺省；`verify_passed=True`；`failure_layer` 为空。
- `page_failure(element_missing)`：`page_failure_code=element_missing`，且映射为 `failure_layer=bridge_page_failed`。
- `timeout(page_timeout)`：`page_failure_code=page_timeout`，且映射为 `failure_layer=bridge_timeout`。
- `verify_fail`：`operation_result=write_adjust_inventory_verify_failed`，`failure_layer=verify_failed`。

---

## 7. 回归矩阵（稳定）

最小矩阵（固定）：

| 样本 | 触发方式 | 关键断言 |
|---|---|---|
| success | `--sample success` | `operation_result=write_adjust_inventory` + `verify_passed=True` |
| page_failure | `--sample page_failure` | `page_failure_code=element_missing` + 映射稳定 |
| timeout | `--sample timeout` | `page_failure_code=page_timeout` + 映射稳定 |
| verify_fail | `--sample verify_fail` | `operation_result=write_adjust_inventory_verify_failed` |
| 旧主线 | 运行 P6.1/P6.2/P70/P71 相关回归 | 不回归既有口径/测试 |

---

## 8. 提交范围清理（必须遵守）

明确排除（禁止提交）：

- `feishu_rpa.db`
- `tmp/*`

建议只提交：

- `docs/`（P71 文档）
- `script/`（回放/演练脚本）
- `tests/`（回归测试）
