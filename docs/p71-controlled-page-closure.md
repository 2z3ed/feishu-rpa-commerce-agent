# P71 阶段收口文档：影刀受控页面最小执行链（`warehouse.adjust_inventory`）

> **阶段定位**：P71 = 在 P70 本地 bridge PoC（契约/失败/回放）基础上，把 `warehouse.adjust_inventory` 推进到“**受控页面最小执行链**”，并在收口前完成稳定化与可交接校验。  
> **固定动作**：仅 `warehouse.adjust_inventory`。  
> **固定边界**：单动作、单页面、非生产接入；不接真实 Odoo 生产页面；不接影刀控制台 / API Key / Flow；不让飞书直接触发影刀。

---

## 1. P71 阶段定义

P71 只做一件事：在保持 P6.1/P6.2/P70 已收口口径不变的前提下，形成：

**confirm 放行后 → yingdao bridge → controlled_page 受控页面执行 → 页面证据字段透传 → `/steps` 可取证**  

并将“页面失败语义 + 回放核对”钉死到可复验、可回归的最小集合。

---

## 2. 为什么 P71 只围绕 `warehouse.adjust_inventory`

- **最小变量**：P6.1/P6.2 已为该动作建立高风险写链与治理口径，适合作为唯一样板承载页面执行验证。
- **可对照**：桥接结果可直接映射到既有 `operation_result/verify_* /failure_layer` 语义，不引入新治理体系。
- **避免范围漂移**：扩第二动作会把“页面自动化问题”和“动作扩展问题”混在一起，降低收口可信度。

---

## 3. P71 各轮分别做了什么（收口摘要）

| 轮次 | 主题 | 核心产出 |
|---|---|---|
| **第一轮** | 现状锚定 | 明确差距在“页面证据/失败语义”；锁定受控页面目标与最小边界 |
| **第二轮** | 受控页面最小执行链落地 | controlled_page 最小链路（happy + page_failure + verify_fail）；新增页面证据字段并打通到 `/steps`；固定样本可回放 |
| **第三轮** | 收口前稳定化 | 固化 `page_failure_code -> failure_layer` 映射；把 `page_timeout` 纳入固定回归；补 `--task-id` 单样本回放结构 |
| **第四轮** | 收口准备校验 | 端到端人工演练清单；收口判定条件；回归矩阵；提交范围清理（禁止 db/tmp） |

---

## 4. 当前已成立的受控页面执行能力（交接版）

下一位 agent **不看聊天**也可据此判断 “P71 已过”：

1. **controlled_page 模式成立（非生产）**：bridge 可驱动受控页面最小流程（打开→定位→输入→提交→读取回显）。  
2. **页面证据字段已成立并可取证**：`page_url/page_profile/page_steps/page_evidence_count/page_failure_code` 可从 bridge 透传到 `parsed_result`，并进入 `/steps action_executed.detail`。  
3. **旧口径完全兼容**：`operation_result/verify_passed/verify_reason/failure_layer/raw_result_path/rpa_vendor` 语义不变。  
4. **固定样本回归矩阵成立**：success / element_missing / page_timeout / verify_fail。  
5. **失败语义稳定可解释**：`page_failure_code -> failure_layer/operation_result/verify_reason` 映射已固定且有测试覆盖。  
6. **单样本回放入口成立**：脚本支持 `--task-id` 输出单样本页面证据摘要与 `/steps` 对照项（人工核查）。  

---

## 5. 当前明确没做什么（边界声明）

- 未扩第二个动作。  
- 未接真实 Odoo 生产页面。  
- 未接影刀控制台 / API Key / Flow。  
- 未让飞书直接触发影刀。  
- 未做正式生产接入（权限/网络/安全/运维门禁均未进入）。  
- 未回头改 P6.1 / P6.2 / P70 已收口逻辑与口径。  

---

## 6. 为什么现在可以正式收口

- P71 的目标是“受控页面最小执行链 + 可取证 + 失败语义稳定 + 可回放校验”，而不是扩展更多动作或做生产接入。
- 关键不确定性（页面执行可行性、证据可落地、失败语义可稳定）已被：
  - 固定样本回归
  - 映射表测试
  - `/steps` 对照清单
 共同钉死。
- 继续留在 P71 补开发将进入收益递减，并模糊“非生产单页验证”的阶段边界。

---

## 7. 当前阶段通过结论

**P71 正式判通过。**

依据：

- `warehouse.adjust_inventory` 的 **controlled_page** 受控页面执行链已成立且可回归
- 页面证据字段可稳定进入 `/steps`
- `element_missing/page_timeout` 的失败语义映射稳定
- `success/element_missing/page_timeout/verify_fail` 固定样本齐全且可回放
- 全程遵守冻结边界：单动作、单页面、非生产、不接控制台/API/Flow、不改既有收口主线

---

## 8. 下一阶段入口怎么定义（仅定义入口，不在本阶段实施）

下一阶段建议入口：在保持“非生产/不接控制台”的前提下，评估是否进入 **更接近真实页面的受控演练** 或 **更严格的证据/回放规范**（仍不等同于生产接入）。

> P71 只负责证明“桥接 PoC 可驱动受控页面并可取证”，不负责生产化。

---

## 9. 为什么当前仍不是正式生产接入

因为当前仍处于 PoC/受控演练边界：

- 页面目标是 internal sandbox/受控测试页，不是生产后台
- 未涉及生产权限、生产网络、安全基线、运维门禁
- 未接影刀控制台/API/Flow 托管能力

因此结论是“**P71 可交接收口**”，不是“**可直接生产上线**”。

---

## 10. 交接索引（最小）

- 受控页面与字段说明：`docs/p71-controlled-page-minimal-execution.md`
- P71 收口（本文）：`docs/p71-controlled-page-closure.md`
- 回放脚本（含 `--task-id` 结构）：`script/p70_yingdao_bridge_rehearsal.py`
- 关键测试（示例）：
  - `tests/test_yingdao_local_bridge.py`
  - `tests/test_p70_yingdao_bridge_rehearsal.py`
  - `tests/test_ingress_action_executed_detail_multi_platform.py`

---

## 11. 最小提交建议（若本轮仅收口文档）

```bash
git add docs/p71-controlled-page-closure.md
git commit -m "docs: P71 closure for controlled page execution chain"
```

