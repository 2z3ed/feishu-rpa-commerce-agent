# P9-C 阶段收口报告（SQLite 真相源版）

## 一、阶段结论

P9-C 已达到收口条件，结论为：

- 可复验
- 可查询
- 可回写

本阶段目标为“主系统将已成立 success 结果异步追加回写到飞书多维表 RPA执行证据台账”，该目标已完成。

## 二、最终冻结样本

- run_id：`P92-1776872728677-f3aef2aa`
- orig_task_id：`TASK-P9B-ODOO-ADJ-ORIG-P92-1776872728677-f3aef2aa`
- confirm_task_id：`TASK-P9B-ODOO-ADJ-CFM-P92-1776872728677-f3aef2aa`
- baseline：`A001 100 -> 105`

## 三、主系统侧通过依据

1. `/api/v1/tasks/{confirm_task_id}` 返回 `succeeded`
2. `/api/v1/tasks/{confirm_task_id}/steps` 出现：
   - `bitable_write_started`
   - `bitable_write_succeeded`
3. `bitable_write_succeeded.detail` 含 record_id：
   - `recvhxeZuXxPWr`

## 四、多维表侧通过依据

- 目标表：`RPA执行证据台账`
- table_id：`tblJVq5GgBKn8gaA`
- record_id：`recvhxeZuXxPWr`

回读字段与主系统一致：

- `task_id=TASK-P9B-ODOO-ADJ-CFM-P92-1776872728677-f3aef2aa`
- `run_id=TASK-P9B-ODOO-ADJ-CFM-P92-1776872728677-f3aef2aa`
- `old_inventory=100`
- `target_inventory=105`
- `new_inventory=105`
- `verify_passed=true`
- `verify_reason=post_inventory_matches_target`
- `screenshot_paths` 与 `latest_evidence_path` 均有值

## 五、非阻塞边界（P9-C.3 冻结）

已固定：

1. bitable 写入失败不回退主系统 success
2. bitable 异常仅记录为 `task_steps` 告警（`bitable_write_failed`）
3. SQLite 仍是真相源，多维表仅为协同台账

## 六、关键风险与处理

### 1) 本地 lark_oapi stub 风险

- 根因：仓库根目录 `lark_oapi` 本地 stub 会遮蔽真实 SDK 模块路径 `lark_oapi.api`
- 现象：IM/bitable SDK 路径调用报 `No module named 'lark_oapi.api'`

### 2) 本轮处理

- 在 bitable 写入中保留 SDK 优先
- 若命中 `ModuleNotFoundError`，自动切换 HTTP fallback（tenant_access_token + bitable open api）

### 3) 冻结结论

- 本轮不重构全链路 SDK 导入机制
- fallback 已满足 P9-C 的“可回写 + 非阻塞”验收需求
- 风险记录为已知项，后续按优先级处理

## 七、FEISHU_RPA_EVIDENCE_TABLE_ID 决策

- 当前方案：按表名 `RPA执行证据台账` 自动解析 table_id，可用
- 风险：依赖表名稳定，若改名会影响路由
- 建议：下一轮新增显式 env `FEISHU_RPA_EVIDENCE_TABLE_ID`（最小增强，不阻塞本轮）

## 八、后移项（不阻塞）

1. IM 回复链路仍受本地 stub 影响（`send_text_reply` SDK 路径）
2. 增加显式 env：`FEISHU_RPA_EVIDENCE_TABLE_ID`
3. PostgreSQL 回归（下一阶段，不作为当前首验收）

## 九、下一阶段候选方向

1. 最小配置增强：加入 `FEISHU_RPA_EVIDENCE_TABLE_ID`
2. 清理本地 stub 对 SDK 的遮蔽策略（仅限必要路径，不扩功能）
3. 继续保持单动作单样本冻结，不扩 failure 分支
