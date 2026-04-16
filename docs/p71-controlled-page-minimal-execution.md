# P71 第二轮：受控页面最小执行链落地（`warehouse.adjust_inventory`）

> 阶段定位：在 P70 本地 bridge PoC 基础上，把 `warehouse.adjust_inventory` 推进到“受控页面最小执行链”。  
> 固定边界：单动作、单页面、非生产接入；不接真实 Odoo 生产页面，不接影刀控制台/API Key/Flow。

---

## 1. 本轮目标

仅围绕 `warehouse.adjust_inventory` 落地：

- happy path：打开页面 -> 定位 SKU -> 输入参数 -> 提交 -> 读取回显
- failed path：页面失败（固定 `element_missing` / `page_timeout`）
- verify_fail：写后核验失败仍走既有口径

并在不破坏旧字段语义前提下，补齐页面证据字段透传到 `/steps`。

---

## 2. 受控页面最小执行链（非生产）

桥接层新增 `controlled_page` 执行模式（配置：`YINGDAO_BRIDGE_EXECUTION_MODE=controlled_page`）：

1. 打开受控页面入口（`page_url`）
2. 定位 SKU（语义步骤）
3. 输入 `delta/target_inventory`（语义步骤）
4. 提交（调用 internal sandbox 的受控库存调整接口）
5. 读取回显并计算核验结果

> 说明：这是受控页面 PoC，不是生产 UI 自动化，不引入生产权限。

---

## 3. 页面证据字段（新增，可选）

在保持旧字段兼容基础上新增：

- `page_url`
- `page_profile`
- `page_steps`
- `page_evidence_count`
- `page_failure_code`

旧字段继续保持原语义：

- `operation_result`
- `verify_passed`
- `verify_reason`
- `failure_layer`
- `raw_result_path`
- `rpa_vendor`

---

## 4. 字段透传路径

`yingdao_local_bridge` -> `yingdao_runner` -> `execute_action(parsed_result)` -> `ingress_tasks(action_executed.detail)`。

其中 `action_executed.detail` 新增输出：

- `page_url`
- `page_profile`
- `page_steps`（`|` 拼接）
- `page_evidence_count`
- `page_failure_code`

---

## 5. 三类固定样本

脚本：`script/p70_yingdao_bridge_rehearsal.py`

1. `success`
2. `page_failure`（固定 `element_missing`）
3. `verify_fail`

并纳入固定回归：`timeout`（`page_timeout`）

---

## 5.1 page_failure_code -> failure_layer 映射（稳定）

| page_failure_code | failure_layer | operation_result | verify_reason |
|---|---|---|---|
| `element_missing` | `bridge_page_failed` | `write_adjust_inventory_bridge_page_failed` | `page_element_missing:sku_locator` |
| `page_timeout` | `bridge_timeout` | `write_adjust_inventory_bridge_timeout` | `bridge_request_timeout` |

---

## 6. 运行说明（最小）

```bash
export ODOO_ADJUST_INVENTORY_CONFIRM_EXECUTION_BACKEND=yingdao_bridge
export YINGDAO_BRIDGE_EXECUTION_MODE=controlled_page
export YINGDAO_CONTROLLED_PAGE_BASE_URL=http://127.0.0.1:8000
python -m app.bridge.yingdao_local_bridge
```

回放样本：

```bash
python script/p70_yingdao_bridge_rehearsal.py --sample success
python script/p70_yingdao_bridge_rehearsal.py --sample page_failure
python script/p70_yingdao_bridge_rehearsal.py --sample verify_fail
```

---

## 7. 边界确认

- 不扩第二个动作
- 仅 `warehouse.adjust_inventory`
- 仅受控页面
- 非正式生产接入
- 不修改 P6.1 / P6.2 / P70 已收口主线语义
