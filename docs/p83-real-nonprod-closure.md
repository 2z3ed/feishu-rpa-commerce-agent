# P83 Real Non-Prod Closure

## 1. 本轮范围

本轮围绕 `real_nonprod_page` 自建 stub 与 `warehouse.adjust_inventory` 单动作，完成单样本回放、端到端人工演练、回归矩阵与阶段收口。

## 2. 当前基线

- 自建 stub 位于 `tools/nonprod_admin_stub/`
- 登录 / 导航 / 查询 / 调整 / 持久化更新成立
- 最小自动化闭环已成立
- `session_invalid` / `entry_not_ready` 失败路径可复现
- facts 已入库
- config 已有最小配置占位
- bridge 已能读取并消费相关 facts
- `controlled_page` 未回归
- 主 API 8000 internal sandbox 未受影响

## 3. 单样本回放说明

### 成功样本
- 动作：`warehouse.adjust_inventory`
- 样本：`sku=A001, old_inventory=100, delta=5, target_inventory=105`
- 回放方式：`script/p83_real_nonprod_happy_path_rehearsal.py`
- 验证点：登录、查询、进入调整页、提交、回查库存、确认写后值

### 失败样本
- `session_invalid`
- `entry_not_ready`
- 回放方式：runner / rehearsal 同链路切换失败模式
- 验证点：失败码、失败层级、page_steps、可复现性

## 4. 端到端人工演练说明

演练链：
1. 登录
2. 进入后台首页
3. 查询 SKU
4. 打开调整页
5. 提交库存调整
6. 读取 success / verify 信号
7. 再次查询确认库存变化

演练层级：runner / rehearsal 级别的 in-process stub 演练，不接真实生产页。

## 5. 回归矩阵

| covered_check | 验证方式 | 本轮是否通过 |
| --- | --- | --- |
| happy path 成功 | `tests/test_p83_real_nonprod_happy_path_readiness.py` / rehearsal | 是 |
| session_invalid | 同上 | 是 |
| entry_not_ready | 同上 | 是 |
| verify_result 正常 | 同上 | 是 |
| SQLite 持久化变化正常 | 同上 | 是 |
| controlled_page 未回归 | 既有测试/代码路径保持 | 是 |
| 主 API 8000 internal sandbox 未受影响 | 既有路径保持 | 是 |

## 6. 结果留档结构

- `docs/p83-real-nonprod-facts.md`
- `docs/p83-real-nonprod-happy-path-readiness.md`
- `docs/p83-real-nonprod-closure.md`
- `script/p83_real_nonprod_happy_path_rehearsal.py`
- `tests/test_p83_real_nonprod_happy_path_readiness.py`

## 7. 仍有哪些尾巴

- 真实影刀点击链未接入
- 仍属于 stub / runner 级别的 in-process 闭环

## 8. 为什么当前可以阶段收口

- 核心事实已入库
- 最小自动化闭环已成立
- 失败语义稳定
- 回放 / 演练 / 留档结构已固定
- 受控页面和主 API 未回归

## 9. 下一阶段建议

如需继续扩展，可在不破坏当前闭环的前提下，接入更真实的 UI 自动化层或更丰富的失败矩阵，但不应再推翻当前 P83 收口结果。
