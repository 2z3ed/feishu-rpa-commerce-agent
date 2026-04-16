# P72 第三轮：更真实后台形态的受控库存页面（最小实现）

> 范围：仅 `warehouse.adjust_inventory`。  
> 目标：在不接真实 Odoo 生产页面、不接影刀控制台/API/Flow 的前提下，让受控页面更接近真实后台形态（入口页/导航/列表/抽屉/回显）。  
> 注意：这仍然不是正式生产接入。

---

## 1. 新受控页面长什么样

页面基于 internal sandbox 的 admin-like 风格新增两条入口：

- 库存概览（Dashboard）：`/api/v1/internal/rpa-sandbox/admin-like/inventory`
- 库存调整（Workbench）：`/api/v1/internal/rpa-sandbox/admin-like/inventory/adjust`

库存调整页包含：

- 侧边导航（库存中心）
- SKU 搜索区（输入 + 查询）
- 列表区（table）
- 编辑抽屉（delta / target_inventory）
- 提交回显（toast + result 面板）

---

## 2. happy path 怎么跑（最小）

1. 打开库存概览页
2. 进入库存调整页
3. 查询 SKU
4. 打开抽屉
5. 输入 delta / target_inventory
6. 提交并读取回显

---

## 3. failure path 怎么跑（最小）

本轮不新增失败码类别，仍使用既有：

- `element_missing`
- `page_timeout`

在库存调整页通过 query 参数注入：

- `failure_mode=element_missing`
- `failure_mode=page_timeout`

---

## 4. 4 类样本如何验证

- success：不带 failure_mode
- element_missing：`failure_mode=element_missing`（抽屉不出现）
- page_timeout：`failure_mode=page_timeout`（回显不出现）
- verify_fail：沿用 `force_verify_fail`（核验失败口径不变）

---

## 5. controlled_page 如何对齐新页面

`controlled_page`（bridge 侧）对齐：

- `page_url` 指向库存概览入口
- `page_profile` 建议使用：`internal_inventory_admin_like_v1`
- `page_steps` 覆盖：入口/导航/列表/抽屉/提交/回显

旧字段口径保持不变：

- `operation_result`
- `verify_passed`
- `verify_reason`
- `failure_layer`
- `raw_result_path`
- `rpa_vendor`

