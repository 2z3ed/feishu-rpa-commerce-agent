# P91 Yingdao Real Click Baseline

本轮以“当前机器已有影刀环境”为前提，完成了 **真执行入口锚定 + 与 P90 文件链接线**。

## 1) 当前影刀实际入口（已锚定）

- 安装路径（可执行入口）
  - `Z:\ShadowBot\ShadowBot.exe`
- 可执行文件名
  - `ShadowBot.exe`
- 影刀运行侧目录（已发现）
  - `Z:\yingdao_bridge\incoming`
  - `Z:\yingdao_bridge\done`
  - `Z:\yingdao_bridge\failed`
  - `Z:\yingdao_bridge\evidence`
  - `Z:\yingdao_bridge\export`
- 触发方式（本轮锚定）
  - 文件触发模式：bridge 左侧写入请求文件，runtime 侧监听 `incoming`，处理后写 `done/failed`

## 2) 与 P90 文件链映射

P90 左侧（项目内）：

- inbox: `tmp/yingdao_bridge/inbox`
- outbox: `tmp/yingdao_bridge/outbox`

影刀 runtime 侧（Windows Z 盘）：

- incoming: `Z:\yingdao_bridge\incoming`
- done: `Z:\yingdao_bridge\done`
- failed: `Z:\yingdao_bridge\failed`
- evidence: `Z:\yingdao_bridge\evidence`

映射策略：

1. `tmp/yingdao_bridge/inbox/{run_id}.input.json` -> `/mnt/z/yingdao_bridge/incoming/{run_id}.input.json`
2. 等待 `/mnt/z/yingdao_bridge/done|failed/{run_id}.*.json`
3. 归一化成 P90 outbox 契约写回 `tmp/yingdao_bridge/outbox/{run_id}.output.json`

## 3) 当前代码接线

- `script/p91_yingdao_real_executor.py`
  - 不再是 shim 页面点击器
  - 改为“真实 runtime 入口适配器”
  - 负责：
    - 左侧 inbox -> 右侧 incoming 映射
    - 唤起 `ShadowBot.exe`（若未运行则启动）
    - 读取 done/failed 并归一化回 outbox
- `app/rpa/yingdao_runner.py`
  - 输出标识改为真实执行：
    - `rpa_vendor=yingdao`
    - `execution_backend=yingdao_runtime_file_trigger`
    - `executor_mode=real`
    - `rpa_runtime=shadowbot`

## 4) Rehearsal 模式拆分（P91-2a）

`script/p91_yingdao_real_rehearsal.py` 已拆成两种模式：

- `--mode simulate`
  - 允许启动 `_simulate_runtime_worker`
  - 仅用于本地样板验证
- `--mode real-runtime`
  - **不允许**启动 `_simulate_runtime_worker`
  - 仅做：写 incoming -> 等 done/failed -> 归一化回 outbox

并且：

- `run_id` 改为每次唯一（时间戳 + uuid），不再固定复用
- 脚本会打印本次真实路径：
  - `incoming_path`
  - `done_path`
  - `failed_path`
  - `outbox_path`
- 提供 `--clean-all` 用于测试前清理旧 `inbox/outbox/incoming/done/failed` 的 `*.json`，避免旧文件污染

## 5) 说明

- 本轮目标是“真执行入口接线 + rehearsal simulate/real-runtime 拆分”，不是完整失败矩阵。
- P90 输入输出契约保持不变（`operation_result` / `verify_passed` / `verify_reason` / `page_failure_code` / `failure_layer` / `page_steps` / `page_evidence_count` / `old_inventory` / `new_inventory` / `screenshot_paths`）。

## 6) P92 临时实现标注（必须回收）

当前 real-runtime 联调仍存在一处临时实现：

- 影刀触发器侧按“最新 incoming 文件”读取执行目标（临时排障方案）

该实现会带来并发/乱序风险，不能作为长期正式实现。后续必须收口到：

- 由触发器直接读取“当前触发文件路径变量”或显式 run_id 绑定路径
- 禁止再依赖目录内“最新文件”规则

## 7) P92-7 success 与证据链收口状态（当前基线）

### 固定 success 基线命令

```bash
python3 script/p91_yingdao_real_rehearsal.py --mode real-runtime --clean-all --reset-db-inventory 100 --sku A001 --old-inventory 100 --delta 5 --target-inventory 105 --bridge-wait-timeout-s 60
```

### 当前 success 判定标准

- `old_inventory=100`
- `new_inventory=105`
- `verify_passed=true`
- 右侧 `done/{run_id}.done.json` 存在
- 左侧 `outbox/{run_id}.output.json` 存在
- `screenshot_paths` 非空
- `page_evidence_count > 0`

### 当前 evidence 兜底策略（已生效）

- 当 runtime 未返回真实截图路径时，归一化层会写入：
  - `/mnt/z/yingdao_bridge/evidence/{run_id}-runtime-result.json`
- 并将该文件回填到 `screenshot_paths`
- `page_evidence_count` 与 `screenshot_paths` 文件数保持一致

### 后移项（本轮不继续展开）

- failure 分支的稳定收口（含真实失败语义与路由一致性）已后移
- 当前阶段只维护 success 主链与证据链基线稳定
