# P72 正式收口文档：更真实后台形态的受控库存验证（`warehouse.adjust_inventory`）

> 状态：正式收口通过。  
> 固定动作：仅 `warehouse.adjust_inventory`。  
> 固定边界：受控页面、非生产接入；不接真实 Odoo 生产页面；不接影刀控制台/API Key/Flow；不让飞书直接触发影刀。  
> 结论：P72 已正式通过，且仍然不是正式生产接入。

---

## 1. P72 阶段定义

P72 的定义不是“继续开发新能力”，而是：

- 在 **不破坏 P6.2 / P70 / P71 已收口口径** 的前提下，
- 用一个 **更像真实后台形态的受控页面** 验证 `warehouse.adjust_inventory` 的最小闭环，
- 并把页面证据、失败语义、回放核对、收口判定整理成可交接阶段成果。

P72 仍然只围绕 `warehouse.adjust_inventory`，因为整条主线已经冻结为：

飞书消息 → 幂等 → 建任务 → Celery 异步执行 → LangGraph 编排 → API / confirm / RPA / bridge 执行链 → 回飞书结果 → `/tasks` 与 `/steps` 可查询、可追踪、可留痕。

P72 的职责是把这个主线在受控页面上收口，而不是扩展动作、扩平台、或者进入正式生产接入。

---

## 2. 为什么 P72 只围绕 `warehouse.adjust_inventory`

因为项目长期原则已冻结：

- RPA 是主执行，API 是辅助执行
- 先最小闭环，再逐轮补治理、统计、门禁、留痕、总演练
- 不破坏已收口主线
- 不做大重构
- 不擅自扩平台、扩动作、跳阶段

`warehouse.adjust_inventory` 是当前唯一已收口的主线动作。P72 只是把这个动作在更真实的受控页面上完成最终验证和正式收口，不引入第二动作，不引入生产接入，不引入控制台/Flow/Key 侧扩展。

---

## 3. P72 各轮分别完成了什么

### P72 第三轮

- 建成更真实的受控库存页面形态
- 补齐入口页、侧边导航、列表、抽屉、提交回显
- 让 `controlled_page` 对齐新页面流程
- 固定 `success / element_missing / page_timeout / verify_fail` 四类样本
- 保持页面证据字段沿用既有口径

### P72 第四轮

- 没有再扩新功能
- 只补了收口准备文档
- 整理了人工演练清单、收口判定条件、回归矩阵
- 把“能跑”整理成“能判定、能交接、能收口”

### 本轮

- 不再做新开发
- 只做正式收口评审 / 判定
- 将草稿推进为正式收口文档
- 明确输出阶段通过结论与后续边界

---

## 4. 当前已成立的更真实受控页面能力

当前已经成立的是一个 **更像真实后台，但仍受控、仍非生产** 的库存页面验证环境：

- 入口页已成立
- 侧边导航已成立
- 列表检索已成立
- 抽屉编辑已成立
- 提交回显已成立
- `controlled_page` 已对齐新流程
- 页面证据字段已进入 `/steps`
- 固定样本已可回放与对照
- 人工演练清单已可直接用于交接

页面证据继续沿用既有口径：

- `page_url`
- `page_profile`
- `page_steps`
- `page_evidence_count`
- `page_failure_code`

并与既有主线字段共同留痕：

- `operation_result`
- `verify_passed`
- `verify_reason`
- `failure_layer`
- `raw_result_path`
- `rpa_vendor`

---

## 5. 当前明确没做什么

P72 明确没有做以下内容：

- 没有扩第二个动作
- 没有接真实 Odoo 生产页面
- 没有接影刀控制台 / API Key / Flow
- 没有让飞书直接触发影刀
- 没有做正式生产接入
- 没有新增失败码类别
- 没有做大重构
- 没有回头改 P6.1 / P6.2 / P70 / P71 已收口逻辑

这意味着 P72 的成果仍然是受控验证成果，不是生产系统改造成果。

---

## 6. 为什么现在可以正式收口

现在可以正式收口，是因为 P72 已经满足“收口而不是继续开发”的条件：

1. 更真实受控页面的 happy path 已成立。
2. `element_missing`、`page_timeout`、`verify_fail` 的固定样本已稳定。
3. `page_url / page_profile / page_steps` 已稳定进入 `/steps action_executed.detail`。
4. 页面证据口径已与既有主线保持一致，不漂移。
5. 回放与人工演练清单已经齐备。
6. P6.2 / P70 / P71 的已收口边界没有被破坏。
7. 没有新增不必要的动作、平台和失败码类别。
8. 仍然清楚保留了“非生产接入”的边界。

因此，P72 现在已经从“更真实受控页面验证”进入“正式收口判定”阶段。

---

## 7. 当前阶段通过结论

### 结论：P72 正式通过。

通过原因：

- 更真实的受控页面已经把 `warehouse.adjust_inventory` 的最小执行链补齐到可演练、可回放、可留痕的程度。
- 关键样本和页面证据字段已经稳定，能够支撑收口判定。
- 收口文档、演练清单、回归矩阵和边界说明已经具备，满足交接要求。
- 没有引入任何会破坏已收口阶段的扩展。

边界仍然清楚的原因：

- 仍然只围绕 `warehouse.adjust_inventory`
- 仍然是受控页面
- 仍然不是正式生产接入
- 仍然不接影刀控制台 / API Key / Flow
- 仍然不让飞书直接触发影刀

---

## 8. P72 收口判定条件与回归矩阵

### 固定判定条件

1. 更真实受控页面 happy path 成立。
2. `element_missing` 语义稳定。
3. `page_timeout` 固定回归稳定。
4. `verify_fail` 固定回归稳定。
5. `page_url/page_profile/page_steps` 稳定进入 `/steps action_executed.detail`。
6. 仍保持非生产接入边界。
7. 未扩第二动作。
8. 未接控制台/API/Flow。

### 稳定回归矩阵

| 用例 | 触发方式 | 关键断言 |
|---|---|---|
| success | `--sample success` | `operation_result=write_adjust_inventory` + `verify_passed=True` |
| element_missing | `--sample page_failure` | `page_failure_code=element_missing` + `failure_layer=bridge_page_failed` |
| page_timeout | `--sample timeout` | `page_failure_code=page_timeout` + `failure_layer=bridge_timeout` |
| verify_fail | `--sample verify_fail` | `operation_result=write_adjust_inventory_verify_failed` + `failure_layer=verify_failed` |
| 旧主线不回归 | 运行 P6.1/P6.2/P70/P71/P72 关键回归 | 既有口径与测试仍通过 |

---

## 9. 为什么当前仍不是正式生产接入

P72 通过，不等于正式生产接入。

原因是：

- 页面目标仍是 internal sandbox 受控页面，不是生产后台
- 执行链路仍用于验证复杂度、证据留痕和回放核查
- 没有生产级账号、网络、权限、审计、运维门禁保障
- 没有接入影刀控制台 / API Key / Flow
- 没有让飞书直接驱动生产侧执行

所以 P72 的定位是“受控验证正式收口”，不是“生产上线准备完成”。

---

## 10. 下一阶段入口怎么定义

P72 收口后的下一阶段，不应继续扩展 P72 本身，而应由后续主线决定，建议入口定义为：

- 继续沿用 `warehouse.adjust_inventory` 主线
- 只在既有受控链路上做更严格的门禁、统计、留痕或演练深化
- 如果后续阶段要推进，也必须先保持非生产边界，再谈更严格的接入治理

下一阶段的关键不是“再加动作”，而是“在不破坏当前主线的前提下，继续把交接、门禁、留痕和演练做稳”。

---

## 11. 交接索引

### 可以直接复用的资产

- `docs/p72-realistic-controlled-inventory-page.md`
- 本正式收口文档
- 已稳定的 `controlled_page` 页面证据口径
- 固定样本：`success / element_missing / page_timeout / verify_fail`
- P72 人工演练清单与回归矩阵

### 当前仍未做的正式生产接入边界

- 真实 Odoo 生产页面接入
- 影刀控制台 / API Key / Flow 接入
- 飞书直连影刀执行
- 生产权限、网络、安全、审计和运维门禁
- 第二动作扩展

---

## 12. 提交范围清理

本轮如果只涉及文档，提交范围应仅限于文档文件，不应带入任何数据库或临时产物。

明确排除：

- `feishu_rpa.db`
- `tmp/*`
- 其它无关临时产物

建议本轮提交：

- `docs/p72-realistic-controlled-inventory-page.md`
- `docs/p72-closure-draft.md`

---

## 13. 最终阶段结论

**P72 已正式通过并正式收口。**

它完成了“更像真实后台的受控验证”这一阶段目标，并把边界、证据、回放、判定和交接索引整理为可继承成果；同时，它仍然没有进入正式生产接入，也没有突破既定主线与冻结边界。

