# P80 真实非生产页面接入锚定

> 阶段定位：P8 主线第一阶段 / P80。  
> 当前目标：先锚定真实非生产页面接入对象与最小执行边界，不进入 P81 实现。  
> 动作边界：仅 `warehouse.adjust_inventory`。  
> 绝对边界：不接真实生产，不扩第二动作，不接影刀控制台 / API / Flow，不让飞书直接触发影刀，不重做 `/tasks` / `/steps`，不推翻已收口主线。

---

## 1. 本轮阶段结论

P80 只做一件事：把“真实非生产页面接入”锚定清楚，确认目标对象、页面路径、最小执行链、最小 happy path、最小 failure path、证据策略，以及 P81 的最小切入点。

这轮不做点击实现，不做正式接入，不做生产化改造。

---

## 2. 仓库当前真实状态（本轮确认）

### 2.1 已存在的核心能力

仓库里当前已确认存在的能力/资产如下：

- `app/bridge/yingdao_local_bridge.py`
  - 本地 bridge 已有 HTTP 契约
  - 支持 `controlled_page` 模式
  - 支持 `page_url` / `page_profile` / `page_steps` / `page_failure_code`
  - 支持 `element_missing` / `page_timeout` / `verify_fail`

- `app/rpa/yingdao_runner.py`
  - 主系统侧 Yingdao 调用封装已存在
  - 负责 bridge 调用、异常翻译、结果校验

- `app/graph/nodes/execute_action.py`
  - `warehouse.adjust_inventory` 已有门禁前置
  - 已有 confirm 唯一放行语义
  - 已有 `gate_allow / gate_status / gate_reason`
  - 已有 `page_*` / `failure_layer` / `verify_reason` 等留痕字段

- `app/tasks/ingress_tasks.py`
  - `action_executed` 详情已稳定输出
  - 门禁字段、页面字段、执行字段均能进入现有证据链

- `script/p70_yingdao_bridge_rehearsal.py`
  - 固定样本回放脚本已存在
  - 可做 task_id replay 报告

- `tests/test_yingdao_local_bridge.py`
  - 已覆盖 controlled page 的 success / element_missing / page_timeout / verify_fail

- `tests/test_yingdao_runner.py`
  - Runner 调 bridge 的正常 / 失败路径已具备测试基础

- `tests/test_p61_odoo_adjust_inventory_flow.py`
  - confirm 主链与 adjust_inventory 的治理语义已被稳定验证

- `tests/test_ingress_action_executed_detail_multi_platform.py`
  - `action_executed` 留痕形状已稳定

- docs 目录已有 P70 / P71 / P72 / P73 全套收口与交接文档

### 2.2 本轮 newly confirmed 的缺口事实

以下事实是本轮重新锚定后明确确认的缺口：

- 仓库里**没有**真实非生产页面的正式锚定文档
- 仓库里**没有**明确指向真实非生产后台 URL、登录方式、导航路径的稳定事实文档
- 仓库里**没有**把 P81 的真实页面点击链写成可落地方案的文档
- 仓库里**没有**把真实非生产页面的截图点位与证据策略单独锚定成 P8 文档

---

## 3. 真实非生产页面的最小接入对象

### 3.1 当前最小接入对象的结论

P80 需要锚定的对象不是生产页面，而是：

**“真实但非生产的受控后台页面”**

当前仓库没有给出一个已被正式记录的具体 URL 名称，因此本轮只能先把对象边界锚定为：

- 真实页面
- 非生产
- 受控后台
- 可被影刀访问
- 可支持 SKU 搜索、编辑、提交、回显

### 3.2 当前缺失的页面事实

仓库当前缺失以下关键信息，需要在后续 P81 前补齐或在外部环境确认：

- 页面入口 URL
- 登录 / 会话维持方式
- 导航入口
- SKU 搜索区位置
- 编辑区位置
- 提交区位置
- 回显区位置

### 3.3 这些缺口会阻塞什么

这些缺口会直接阻塞 P81 的第一步：

- 无法确定影刀进入哪一个真实非生产页面
- 无法确定页面元素定位策略
- 无法定义稳定的点击链与截图点位

---

## 4. P81 未来最小执行链草图

以下是未来最小执行链，只是草图，不是本轮实现：

1. Feishu 触发 `warehouse.adjust_inventory`
2. 任务系统创建任务，进入 `awaiting_confirmation`
3. `system.confirm_task` 放行
4. `YingdaoRunner` 调本地 bridge
5. bridge 进入 `real_nonprod_page` 或等价模式
6. 影刀打开真实非生产后台页面
7. 搜索 SKU
8. 打开编辑区
9. 输入 `delta` 或 `target_inventory`
10. 点击提交
11. 读取页面回显
12. 输出结果到 bridge DTO
13. 回写 `/tasks` 与 `/steps`
14. 留存证据与审计字段

---

## 5. 最小 happy path

P80 锚定的最小 happy path 仅保留一条：

- 页面可访问
- 会话有效
- SKU 可搜索到
- 编辑区可打开
- 提交后页面回显与目标一致
- bridge 输出 `operation_result=write_adjust_inventory`
- `verify_passed=true`
- `failure_layer=` 空
- `page_failure_code=` 空
- `page_steps` 完整

### 最少截图点位建议

未来真实非生产页面中，最少应保留这些截图点位：

1. 打开后台首页后的首页截图
2. 搜索到 SKU 之后的列表截图
3. 打开编辑区后的抽屉/表单截图
4. 点击提交后的回显截图
5. 最终结果或成功提示截图

---

## 6. 最小 failure path

P80 先只锚定一条最主要 failure path：

**会话失效 / 未登录**

原因：
- 这是最早发生、最容易阻塞真实页面接入的一类失败
- 也是最能帮助确认登录 / 会话维持方式的失败

### 这条 failure path 的最小表现

- 页面无法进入或跳转登录页
- `verify_passed=false`
- `failure_layer=session_invalid` 或等价表达
- `operation_result=write_adjust_inventory_bridge_failed` 或等价失败结果
- `page_steps` 在最前段中止
- `page_failure_code` 进入会话相关码

### 备选但不优先展开的 failure path

- 元素缺失
- 页面超时
- 提交后回显不一致
- verify_fail

这些可以在后续阶段扩展，但 P80 只先锁最主要的一条。

---

## 7. 样本迁移方式

P80 不是重新造样本，而是要把 P70/P71/P72/P73 已验证过的样本理念迁移到真实非生产页面。

### 迁移原则

- 继续沿用现有 `page_*`、`failure_layer`、`verify_reason` 口径
- 不新增一套新字段体系
- 先用 controlled / nonprod 的页面样本对照真实页面行为
- 固定样本先从“可回放”迁移到“可对照”

### 迁移方法

1. 先用现有 controlled page 样本作为基线
2. 再把相同输入迁移到真实非生产页面
3. 对照页面步骤、回显、失败层、截图点位
4. 保持 `action_executed` 详情可比

---

## 8. 证据策略

P80 的证据策略继续沿用既有最小口径，不新造字段。

### 必须保留的最小字段

- `page_url`
- `page_profile`
- `page_steps`
- `page_evidence_count`
- `operation_result`
- `failure_layer`
- `verify_reason`
- `page_failure_code`

### 证据策略结论

真实非生产页面接入时，证据重点不是“截图越多越好”，而是：

- 每个关键步骤至少有一个可复核点位
- 页面路径和步骤顺序可复现
- 失败时能够定位失败发生在哪一步
- 与 `/steps` 里的结构化字段能够一一对应

---

## 9. P81 的最小实现切入点

P81 未来的最小实现切入点应当是：

1. 在 bridge 增加真实非生产模式分支或等价配置
2. 保持 runner 调用方式不变
3. 让 real_nonprod_page 复用现有 DTO 结构
4. 只接一个页面、一个动作、一个 happy path、一个主要 failure path
5. 先打通可观测性，再扩展稳定性

---

## 10. 这一轮明确不做什么

本轮明确不做：

- 不进入 P81 真实页面点击链实现
- 不接真实生产页面
- 不扩第二个动作
- 不切到 `product.update_price`
- 不接影刀控制台 / API Key / Flow
- 不让飞书直接触发影刀
- 不做正式生产接入
- 不做大重构
- 不重做 `/tasks`、`/steps`
- 不改 confirm 的唯一放行语义
- 不发散到 Odoo 第二动作 / Chatwoot / 其他平台

---

## 11. 本轮结论

### 当前阶段结论

P80 的最小锚定目标是清楚的：

- 目标对象：真实但非生产的受控后台页面
- 最小接入对象：单页面、单动作、单 happy path、单主要 failure path
- 最小执行链：confirm -> runner -> bridge -> real_nonprod_page -> 搜索/编辑/提交/回显 -> `/tasks` 与 `/steps`
- 证据策略：继续沿用现有 page_* / failure_layer / verify_reason 口径

### 本轮 newly confirmed 的结论

- 已有 bridge / runner / 门禁 / 留痕 / 回放 / 样本体系可以直接复用
- 真实非生产页面的具体 URL / 登录 / 导航事实仍缺失
- P81 的实现必须先补齐页面事实，再写点击链

### 当前评估

**P80 目标锚定已基本成立，当前状态：基本通过但有阻塞项。**

阻塞项不在代码，而在真实非生产页面事实尚未完全确认。
