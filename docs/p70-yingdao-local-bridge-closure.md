# P70 阶段收口文档：影刀本地桥接 PoC（`warehouse.adjust_inventory`）

> **阶段定位**：P70 = 在 P6.1/P6.2 已收口基础上，为 `warehouse.adjust_inventory` 建立“主系统 -> 本地 bridge -> 本机执行器 -> 回写证据面”的最小桥接 PoC。  
> **固定动作**：仅 `warehouse.adjust_inventory`。  
> **固定边界**：不扩第二动作、不接真实 Odoo 页面、不接影刀控制台/API/Flow、不做生产接入。

---

## 1. P70 阶段定义

P70 只做一件事：把影刀当作**本机执行器**接入主系统 confirm 写链，形成可复验的本地桥接 PoC 骨架。

阶段目标不是扩功能，而是验证以下最小能力是否成立：

- bridge 契约稳定
- runner 调用稳定
- 失败表达稳定
- `/tasks` 与 `/steps` 可取证
- 固定样本可重复回放

---

## 2. 为什么 P70 只围绕 `warehouse.adjust_inventory`

- 该动作已具备 P6.1/P6.2 完整治理上下文，最适合承载桥接 PoC。  
- 单动作能最小化变量，避免把 bridge 验证与业务扩展混在一起。  
- 目标是验证“桥接方法”，不是扩展业务覆盖面。

---

## 3. 三轮分别做了什么（收口摘要）

| 轮次 | 主题 | 核心产出 |
|------|------|----------|
| **第一轮** | 主系统接本地 bridge 骨架 | 定义 bridge 输入输出契约；落地 `GET /health` + `POST /run`；新增 `YingdaoRunner`；confirm 写链可切到 `yingdao_bridge`；结果回写 `/tasks` 与 `/steps` |
| **第二轮** | 最小稳态 | 失败分类与超时口径稳定化（runner + bridge + confirm 回写）；补失败回归测试；补最小手动演练入口与排查文档 |
| **第三轮** | 最小发布演练口径 | 固定三类样本（success/timeout/verify_fail）可重复回放；形成 `/steps` 对照检查清单；补与既有治理理解最小对齐说明与测试 |

---

## 4. 当前已成立的本地桥接 PoC 能力（交接版）

下一位 agent 不看聊天也可据此判断 “P70 已过”：

1. 本地 HTTP bridge 可用（`/health`、`/run`）。  
2. `YingdaoRunner` 已从主系统侧隔离影刀依赖（主系统只调 bridge）。  
3. confirm 放行后可按开关走 `yingdao_bridge`，默认仍保持 `internal_sandbox`。  
4. 失败分类与超时口径稳定（不可达/超时/HTTP错误/结果非法/缺字段等）。  
5. 桥接结果可回写现有证据面，`action_executed.detail` 能看到：
   - `rpa_vendor`
   - `operation_result`
   - `verify_passed`
   - `verify_reason`
   - `failure_layer`
   - `confirm_task_id / target_task_id`
   - `raw_result_path`（及证据计数）
6. 固定成功/失败样本可回放，且可做 `/steps` 一一对照核查。  
7. 与既有 P6.2 治理理解不冲突（桥接样本可映射到既有 summary/gate 语义）。

---

## 5. 当前明确没做什么（边界声明）

- 未扩第二个动作。  
- 未接真实 Odoo 页面。  
- 未接影刀控制台 / API Key / Flow。  
- 未让飞书直接触发影刀。  
- 未做生产接入、生产权限、生产稳定性治理。  
- 未回改 P6.1 / P6.2 已收口逻辑。  
- 未触碰 Woo 已收口主线。

---

## 6. 为什么现在应先收口，而不是继续留在 P70 补开发

- P70 目标是“本地桥接 PoC 口径成立”，不是“桥接功能无限扩展”。  
- 三轮后核心资产已齐：骨架、稳态、发布演练口径。  
- 继续在 P70 内补小开发会进入收益递减，并模糊阶段边界。  
- 先收口可将桥接契约、失败口径、演练方式固定成后续阶段输入。

---

## 7. 当前阶段通过结论

**P70 正式判通过。**

依据：`warehouse.adjust_inventory` 的本地桥接 PoC 已具备“可调、可失败、可取证、可回放、可对照”的最小完整能力，且边界清晰、未越界扩张。

---

## 8. 下一阶段入口定义（仅定义，不在本阶段编码）

建议下一阶段主线：在保持单动作边界下，进入“后续主线推进（可选：P70 收口后下一阶段桥接深化）”，重点评估：

- 是否需要把本地 bridge 能力升级为更严格的准生产演练规范  
- 是否需要在不引入控制台依赖前提下补最小运行保障（如更细粒度诊断/回放记录）

> 本文只定义入口，不提前实现正式生产接入能力。

---

## 9. 为什么当前还不是正式生产接入

因为当前仍是 PoC 边界：

- 执行器是本机桥接模型，不是正式控制台编排/托管模型。  
- 未涉及生产权限、生产网络、生产安全基线。  
- 未覆盖真实 Odoo 页面与生产级异常矩阵。  
- 未建立正式上线门禁与运维机制。

因此当前结论是“PoC 成立可交接”，不是“可直接生产上线”。

---

## 10. 交接索引（最小）

- PoC 说明：`docs/p70-yingdao-local-bridge-poc.md`
- 收口文档（本文）：`docs/p70-yingdao-local-bridge-closure.md`
- 演练脚本：`script/p70_yingdao_bridge_rehearsal.py`
- 核心测试：
  - `tests/test_yingdao_local_bridge.py`
  - `tests/test_yingdao_runner.py`
  - `tests/test_p70_yingdao_bridge_rehearsal.py`
  - `tests/test_ingress_action_executed_detail_multi_platform.py`（桥接字段证据面）

---

## 11. 最小提交建议（若本轮仅收口文档）

```bash
git add docs/p70-yingdao-local-bridge-closure.md
git commit -m "docs: P70 closure for yingdao local bridge poc"
```

---

## 12. Tag 建议（可选）

- `p70-yingdao-local-bridge-poc-closed`
- 或日期版本：`p70-yingdao-local-bridge-poc-closed-20260416`
