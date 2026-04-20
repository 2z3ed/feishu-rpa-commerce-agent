# P90.5 Page Executor Baseline (Shim)

## 定位

当前执行器 `script/p91_yingdao_real_executor.py` 已更正为 **page executor shim / baseline**：

- 它会真实操作 self-hosted real_nonprod_page（Playwright）
- 但它 **不是 Yingdao runtime 真执行器**
- 它继续复用 P90 inbox/outbox 契约

## 为什么不能等同 Yingdao runtime

- 未启动/调用 Yingdao runtime 程序
- 未通过 Yingdao runtime 执行工程流
- 仅是页面自动化样板执行器，用于保持链路与留痕可验证

## 当前接通的主系统口径

runner 返回中增加区分字段：

- `rpa_vendor=page_executor_shim`
- `execution_backend=page_executor_baseline`
- `executor_mode=shim`
- `rpa_runtime=none`

并继续输出原有关键字段：

- `operation_result`
- `verify_passed`
- `verify_reason`
- `page_failure_code`
- `failure_layer`
- `page_steps`
- `page_evidence_count`
- `old_inventory`
- `new_inventory`
- `screenshot_paths`

## success / failure 样本

- success：提交库存后再查询验证，`verify_passed=true`
- failure：支持 `session_invalid`（或 `entry_not_ready`）失败样本

## 未来恢复 P91 真点击替换点

保持 bridge 输入输出契约不变，仅替换执行器实现：

- 用 Yingdao runtime 真执行器替换 page executor shim
- 保持 inbox/outbox 与 runner 映射字段不变
- 主系统消费口径（/tasks、/steps、detail）无需重构
