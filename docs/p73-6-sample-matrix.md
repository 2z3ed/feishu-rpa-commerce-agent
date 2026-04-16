# P73 开发第三轮：固定样本回归矩阵对齐

> 状态：开发落地说明。  
> 范围：仅 `warehouse.adjust_inventory`。  
> 本轮只做 4 个固定样本的统一检查结构与回归断言对齐，不扩张。

## 4 个固定样本的统一检查结构

### 1. success

- 输入形态：`sku + delta`，`force_verify_fail=false`，`page_failure_mode=none`
- 关键断言：
  - `operation_result=write_adjust_inventory`
  - `verify_passed=true`
  - `failure_layer=` 空
  - `page_failure_code=` 空
  - `gate_status=allow`
  - `gate_reason=allow`
- `/steps` 留痕：应有，且 page steps 完整

### 2. element_missing

- 输入形态：`sku + delta`，`page_failure_mode=element_missing`
- 关键断言：
  - `operation_result=write_adjust_inventory_bridge_page_failed`
  - `verify_passed=false`
  - `failure_layer=bridge_page_failed`
  - `verify_reason=page_element_missing:sku_locator`
  - `page_failure_code=element_missing`
  - `gate_status=allow`
  - `gate_reason=allow`
- `/steps` 留痕：应有，且 page steps 截止到 `open_drawer`

### 3. page_timeout

- 输入形态：`sku + delta`，`page_failure_mode=page_timeout`
- 关键断言：
  - `operation_result=write_adjust_inventory_bridge_timeout`
  - `verify_passed=false`
  - `failure_layer=bridge_timeout`
  - `verify_reason=bridge_request_timeout`
  - `page_failure_code=page_timeout`
  - `gate_status=allow`
  - `gate_reason=allow`
- `/steps` 留痕：应有，且 page steps 只到 `open_dashboard`

### 4. verify_fail

- 输入形态：`sku + delta`，`force_verify_fail=true`
- 关键断言：
  - `operation_result=write_adjust_inventory_verify_failed`
  - `verify_passed=false`
  - `failure_layer=verify_failed`
  - `verify_reason` 包含 `forced_verify_failure`
  - `page_failure_code=` 空
  - `gate_status=allow`
  - `gate_reason=allow`
- `/steps` 留痕：应有，且 page steps 完整

## 本轮新增 / 对齐的断言

- 成功样本断言补齐了 `gate_status=allow` 与 `gate_reason=allow`
- `element_missing` 样本断言补齐了 `verify_reason`、`page_failure_code`，并保持 `gate_* = allow`
- `page_timeout` 样本断言补齐了 `failure_layer`、`verify_reason`，并保持 `gate_* = allow`
- `verify_fail` 样本断言补齐了 `page_failure_code` 空值、`verify_reason` 包含 forced 标记，并保持 `gate_* = allow`

## 字段克制原则

- 继续沿用现有最小字段
- 不新增同义 gate 字段
- 不扩散成新的治理字段体系
- 不重做 `/tasks` / `/steps`

## 没做什么

- 没有扩第二个动作
- 没有接真实 Odoo 生产页面
- 没有接影刀控制台 / API Key / Flow
- 没有让飞书直接触发影刀
- 没有做正式生产接入
- 没有做大重构
- 没有重做 `/tasks` / `/steps`
- 没有引入新的治理字段体系

## 手动验证

- 先跑 `tests/test_p70_yingdao_bridge_rehearsal.py`
- 再跑 `tests/test_yingdao_local_bridge.py`
- 再回看 `tests/test_p61_odoo_adjust_inventory_flow.py`
- 再回看 `tests/test_ingress_action_executed_detail_multi_platform.py`
- 确认 4 个固定样本的 `operation_result / failure_layer / verify_reason / gate_* / page_failure_code` 一致性
