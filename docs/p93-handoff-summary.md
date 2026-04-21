# P93 Handoff Summary (Yingdao Mainline)

## 1) 当前已完成状态（可直接继承）

在当前收窄范围内，Yingdao 主线已完成并收口到 success 基线：

- success 真点击链通过（`warehouse.adjust_inventory`）
- 基线可复跑：`A001` 库存可稳定 `100 -> 105`
- 右侧 runtime 结果链成立：`done/{run_id}.done.json` 稳定生成
- 左侧归一化结果链成立：`tmp/yingdao_bridge/outbox/{run_id}.output.json` 稳定生成
- success 口径稳定：`verify_passed=true`
- 证据链成立（当前为兜底方案）：evidence 至少有 `runtime-result.json`
- README 已完成最小外化同步（阶段状态与后移项已对外显式）

## 2) 当前后移项（不纳入当前通过标准）

以下内容已明确后移：

1. failure 分支真实收口（路由语义、失败矩阵、稳定失败样本）
2. evidence 从 `runtime-result.json` 兜底升级为真实截图链
3. 触发侧“读取 incoming 最新文件”临时方案回收为“读取触发器实际触发路径变量”

## 3) 最小标准运行命令（当前唯一基线）

```bash
python3 script/p91_yingdao_real_rehearsal.py --mode real-runtime --clean-all --reset-db-inventory 100 --sku A001 --old-inventory 100 --delta 5 --target-inventory 105 --bridge-wait-timeout-s 60
```

## 4) 关键结果文件路径（按 run_id 对齐）

运行后按本次 `run_id` 对齐检查：

- incoming: `/mnt/z/yingdao_bridge/incoming/{run_id}.input.json`
- runtime done: `/mnt/z/yingdao_bridge/done/{run_id}.done.json`
- runtime failed: `/mnt/z/yingdao_bridge/failed/{run_id}.failed.json`
- outbox output: `tmp/yingdao_bridge/outbox/{run_id}.output.json`
- evidence fallback: `/mnt/z/yingdao_bridge/evidence/{run_id}-runtime-result.json`

## 5) 当前最准确阶段判断

- 当前阶段判断：**P93 已完成（success 主链与证据链已收口）**
- 当前不再回头处理：success 主流程 / failure 深挖 / bridge 基础链 / evidence 兜底逻辑

## 6) 下一阶段候选方向（仅列方向，不开工）

1. failure 分支真实落地
2. 真实截图证据增强
3. latest-file 临时方案回收
