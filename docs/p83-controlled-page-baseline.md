# P83 受控页面基线

> 说明：本文件仅记录 **controlled_page** 的已确认事实基线，供后续与 `real_nonprod_page` 做对照。  
> 当前结论：controlled_page 事实清楚，但它**不能替代** real_nonprod_page 的真实页面事实。  
> 动作边界：仅 `warehouse.adjust_inventory`。

---

## 1. 已确认的 controlled_page 事实

### 1.1 entry_url

- `http://127.0.0.1:8000/api/v1/internal/rpa-sandbox/admin-like/inventory/adjust`

### 1.2 search_area

- `sku_input`：存在
- `warehouse_input`：存在
- `query_button`：存在

### 1.3 list_area

- `result_row`：`A001` 可查询
- `before_inventory_field`：存在，显示写前库存
- `adjust_button`：存在

### 1.4 editor_area

- `drawer`：右侧抽屉
- `sku_field`：存在
- `before_inventory_field`：存在
- `delta_input`：存在
- `target_inventory_input`：存在
- `submit_button`：存在

### 1.5 feedback_area

- `success_panel`：存在
- `success_text`：`提交成功：库存已更新（受控回显）`
- `result_value`：`new_inventory=96`

---

## 2. 这个基线的用途

- 作为受控页面结构参考
- 帮助识别真实非生产页面需要达到的最小可执行粒度
- 仅用于对照，不用于替代真实页面 facts

---

## 3. 不可替代性说明

`controlled_page` 基线不等于 `real_nonprod_page` facts。

真实非生产页面仍必须单独补齐：

- 正式 URL
- 登录 / 会话维持方式
- 导航入口
- SKU 搜索区稳定定位
- 编辑区稳定定位
- 提交区稳定定位
- 回显区稳定定位

---

## 4. 当前结论

- `controlled_page` 基线已确认
- `real_nonprod_page` facts 仍待确认
- P83 正式总演练仍不能启动
