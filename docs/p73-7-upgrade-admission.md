# P73 开发第四轮：升级准入检查项固化

> 状态：升级准入定义文档。  
> 范围：仅 `warehouse.adjust_inventory`。  
> 本轮只固化升级准入检查项，不扩张，不改执行链。

## 升级准入检查项

### 1. 门禁点是否稳定

**检查什么**
- 门禁入口是否仍在 `warehouse.adjust_inventory` 的前置位置
- 门禁是否仍只表达最小前置检查结论

**怎么检查**
- 看 `app/graph/nodes/execute_action.py` 的分支位置
- 看 `gate_allow`、`gate_status`、`gate_reason` 是否仍为最小表达

**通过**
- 门禁入口位置清楚且未漂移
- 门禁只负责前置检查，不吞并执行层失败

**不通过**
- 门禁位置变得模糊
- 门禁结果被执行期失败反向覆盖
- 出现额外同义门禁字段

**待确认**
- 文档与测试未同步更新
- 新实现未补齐回归

### 2. 留痕口径是否稳定

**检查什么**
- `action_executed` 详情是否仍承载最小留痕字段
- 是否仍保持任务级 / 步骤级职责分离

**怎么检查**
- 看 `app/tasks/ingress_tasks.py`
- 看 `gate_allow`、`gate_status`、`gate_reason` 是否仍进入现有详情链

**通过**
- 留痕字段仍是最小集合
- 不重做 `/tasks` / `/steps`

**不通过**
- 大范围字段体系重构
- 新增一组同义治理字段
- 留痕职责混写

**待确认**
- 只在部分回归中出现，缺乏统一验证

### 3. 固定样本矩阵是否稳定

**检查什么**
- `success / element_missing / page_timeout / verify_fail` 四个样本是否保持一致结构
- 样本断言是否稳定且可复用

**怎么检查**
- 看 `tests/test_yingdao_local_bridge.py`
- 看 `script/p70_yingdao_bridge_rehearsal.py`
- 看样本级 `operation_result / failure_layer / verify_reason / page_failure_code`

**通过**
- 四个样本都可重复跑
- 每个样本的关键断言一致

**不通过**
- 样本缺失
- 样本之间结构不一致
- 断言依赖临时人工判断

**待确认**
- 只有文档描述，没有对应测试覆盖

### 4. `--task-id` 回放与样本对照是否稳定

**检查什么**
- 是否能通过 `--task-id` 读取并对照固定样本的结果结构
- 是否能用于人工核查 `/steps`

**怎么检查**
- 看 `script/p70_yingdao_bridge_rehearsal.py` 的 `build_task_id_replay_report`
- 用单样本回放对照输出和 `/steps` 的 `action_executed.detail`

**通过**
- 回放报告结构稳定
- 可人工对照 `/steps`

**不通过**
- 回放入口缺失
- 回放结构不稳定
- 与 `/steps` 无法对照

**待确认**
- 回放报告存在，但样本与证据未一致对照

### 5. 失败层 / 主原因映射是否稳定

**检查什么**
- `failure_layer` 是否仍稳定映射到结果语义
- `verify_reason`、`operation_result` 是否与失败层一致

**怎么检查**
- 看 bridge / confirm / result 相关测试
- 重点核对 timeout / page failure / verify fail

**通过**
- 失败层与结果口径一致
- 不需要猜测主原因

**不通过**
- 同一失败场景出现多套口径
- 失败层无法区分主原因

**待确认**
- 个别样本口径仍在调整

### 6. 是否仍保持冻结边界

**检查什么**
- 是否仍只围绕 `warehouse.adjust_inventory`
- 是否仍未扩第二动作
- 是否仍未接正式生产

**怎么检查**
- 看本轮定义和测试改动范围
- 看配置与执行链是否无生产接入变化

**通过**
- 仍只围绕单动作
- 仍非生产接入

**不通过**
- 出现第二动作实现
- 出现生产接入或控制台侧联动

**待确认**
- 文档说冻结，但代码已开始扩张

### 7. 是否无需推翻已有主线语义

**检查什么**
- 是否仍保留 confirm 唯一放行语义
- 是否仍保留 P6.2 / P70 / P71 / P72 / P73 的主线定义

**怎么检查**
- 看 confirm 分支和门禁分支是否仍是前置关系
- 看是否存在需要重写主线语义的新增逻辑

**通过**
- 主线语义未被推翻
- 新增内容只是在原主线内加固

**不通过**
- 需要重写主线抽象才能继续
- confirm 语义被覆盖或旁路

**待确认**
- 文档上说未推翻，但实现和测试尚未完全对齐

## 最小结论

如果以上 7 项都能被明确判定为“通过”，则可认为进入下一阶段的准入条件已经具备。
如果任一项落入“不通过”或“待确认”且不能在当前范围内收敛，则不进入下一阶段。

## 本轮只做了什么

- 把升级准入从抽象定义收敛成 7 条可检查项
- 每条都补了最小的“看什么 / 怎么看 / 通过 / 不通过 / 待确认”结构
- 没有改执行链，不增加新能力

## 没做什么

- 没有扩第二个动作
- 没有接真实 Odoo 生产页面
- 没有接影刀控制台 / API Key / Flow
- 没有让飞书直接触发影刀
- 没有做正式生产接入
- 没有做大重构
- 没有重做 `/tasks` / `/steps`
- 没有新增治理字段体系

## 手动核查

- 先看 `app/graph/nodes/execute_action.py`
- 再看 `app/tasks/ingress_tasks.py`
- 再看 `script/p70_yingdao_bridge_rehearsal.py`
- 再看 `tests/test_yingdao_local_bridge.py`
- 最后把四个固定样本与 `/steps`、`action_executed.detail` 对照检查
