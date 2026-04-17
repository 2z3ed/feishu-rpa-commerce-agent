# P83 Real Non-Prod Facts

> 来源：`tools/nonprod_admin_stub` 自建本地 non-production admin stub。  
> 目的：作为 P8 后续 `real_nonprod_page` 的真实目标页 facts 基线。  
> 动作边界：仅 `warehouse.adjust_inventory`。  
> 当前结论：facts 已正式入库，但 happy path readiness 仍需代码消费路径与验证脚本联动确认。

---

## 1. 环境事实

- `entry_url`: `http://127.0.0.1:18081/login`
- `admin_entry_url`: `http://127.0.0.1:18081/admin`
- `default_port`: `18081`
- `default_account`: `admin / admin123`
- `session_mode`: `cookie`
- `session_cookie_name`: `nonprod_stub_session`
- `session_cookie_value`: `admin-session`

---

## 2. 页面路径

- `GET /login`
- `POST /login`
- `GET /admin`
- `GET /admin/inventory`
- `GET /admin/inventory/adjust?sku=A001`
- `POST /admin/inventory/adjust`

---

## 3. navigation path

1. `GET /login`
2. `POST /login`
3. `GET /admin`
4. `GET /admin/inventory`
5. `GET /admin/inventory/adjust?sku=A001`

---

## 4. Search area selectors

- `search_input_selector`: `input[name="sku"]`
- `search_button_selector`: `button[type="submit"]`
- `result_row_selector`: `table` 内的结果行

---

## 5. Editor area selectors

- `editor_entry_selector`: `/admin/inventory/adjust?sku=A001`
- `editor_container_selector`: `.card` 内的“库存调整”表单

---

## 6. Submit area selectors

- `inventory_input_selector`: `input[name="delta"]` 或 `input[name="target_inventory"]`
- `submit_button_selector`: `button[type="submit"]`

---

## 7. Feedback area selectors

- `success_toast_selector`: `.msg-ok`
- `error_toast_selector`: `.msg-err`
- `verify_field_selector`: `p` 中的“写后库存”或 `a[href^="/admin/inventory?sku="]`

---

## 8. Success / failure signals

### Success

- 成功提示：`提交成功`
- 写后库存：页面中显示新库存值
- 再查询：库存值已真实变化

### Failure

- `session_invalid`：未登录访问后台或会话失效
- `entry_not_ready`：库存页不可用
- `element_missing`：编辑入口不可用

---

## 9. 已确认的样本数据

- `sku=A001`
- `warehouse=MAIN`
- `inventory=100`

---

## 10. 当前最小 readiness 结论

- facts 已入库
- self-hosted stub 已成为 real_nonprod_page 的真实目标页来源
- 下一步需要把这些 facts 正式接入代码运行路径与验证手段
