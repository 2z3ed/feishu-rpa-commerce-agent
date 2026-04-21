# P93 Yingdao Success Closure

## 1) 阶段目标与结论

本阶段仅收口 success 主链（`warehouse.adjust_inventory`），不继续深挖 failure 分支。

当前阶段已完成：

- success 真点击链可复跑
- 数据库可稳定从 `A001: 100 -> 105`
- runtime 稳定产出 `done.json`
- 左侧稳定产出 `outbox/{run_id}.output.json`
- `verify_passed=true`
- evidence 至少有 `runtime-result.json` 兜底产物

## 2) 标准总演练命令

```bash
python3 script/p91_yingdao_real_rehearsal.py --mode real-runtime --clean-all --reset-db-inventory 100 --sku A001 --old-inventory 100 --delta 5 --target-inventory 105 --bridge-wait-timeout-s 60
```

## 3) 预期结果文件

以本次 run 为例：

- run_id: `P92-1776772443763-76c9a91d`
- runtime done: `/mnt/z/yingdao_bridge/done/P92-1776772443763-76c9a91d.done.json`
- outbox result: `tmp/yingdao_bridge/outbox/P92-1776772443763-76c9a91d.output.json`
- evidence file: `/mnt/z/yingdao_bridge/evidence/P92-1776772443763-76c9a91d-runtime-result.json`

## 4) success 判定口径

一次通过必须同时满足：

- `old_inventory=100`
- `new_inventory=105`
- `verify_passed=true`
- `done.json` 存在
- `output.json` 存在
- `page_evidence_count > 0`
- `screenshot_paths` 非空且路径可访问

## 5) 证据链当前状态

当前以兜底证据策略为主：

- 当 runtime 未返回真实截图时，归一化层落盘：
  - `/mnt/z/yingdao_bridge/evidence/{run_id}-runtime-result.json`
- 并回填到 `screenshot_paths`
- `page_evidence_count` 与 `screenshot_paths` 文件数保持一致

## 6) 后移项（不纳入本阶段通过标准）

- failure 分支完整收口（路由语义、失败矩阵）
- evidence 从兜底 JSON 升级为真实截图链
- 触发侧“读取 incoming 最新文件”临时方案回收为“读取触发器实际触发路径变量”

## 7) 本阶段回归矩阵

- success 基线（100->105）：通过
- runtime done.json：通过
- outbox output.json：通过
- verify_passed=true：通过
- evidence 兜底：通过
- failure 分支：后移（不纳入本轮通过标准）
