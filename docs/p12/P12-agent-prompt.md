# P12-F Agent 开发提示词

你现在接手的是 feishu-rpa-commerce-agent 项目。

当前唯一主线是：

P12-F：监控对象删除二次确认版

## 一、当前现实

P12-A 已完成：

- 搜索商品返回候选卡片
- 卡片失败 fallback 文本

P12-B 已完成：

- 候选卡片“加入监控”按钮
- 点击按钮成功纳管
- 群聊结果优先回复群聊

P12-C 已完成：

- “看看当前监控对象”返回管理卡片
- 支持暂停 / 恢复

P12-D 已完成：

- 超过 5 个监控对象时支持“查看更多”
- 下一页仍保留暂停 / 恢复按钮

P12-E 已完成：

- P12 卡片交互层收口
- 演示路径统一
- 回归脚本固化
- 删除、批量、搜索过滤、排序明确后移

本轮不是做批量管理，也不是做搜索过滤。

本轮只做：

监控对象删除二次确认。

## 二、开始前必须先读

1. docs/p12/p12-project-plan.md
2. docs/p12/P12-agent-prompt.md
3. docs/p12/p12-boss-demo-sop.md
4. docs/p12/p12-acceptance-checklist.md
5. docs/p12/p12-closure-summary.md
6. README.md
7. AGENTS.md

如果这些文件不存在，或者不是 P12-F 口径，先停止并回报，不要自行编造阶段目标。

## 三、本轮第一步：先锚定 B 是否已有删除能力

你必须先检查：

- app/clients/b_service_client.py
- app/graph/nodes/execute_action.py
- 当前 B 相关接口约定
- tests 中是否已有 delete/remove/archive monitor target 能力

如果 B 没有删除能力：

不要硬造 A 侧假删除。

必须先回报：

```text
当前 B 未提供 monitor target 删除能力，P12-F 不能完整落地。
```

如果 B 已有删除能力，才继续实现完整 P12-F。

## 四、本轮唯一目标

在监控对象管理卡片中增加：

```text
删除监控
```

但点击后不能直接删除。

必须先进入二次确认：

- 确认删除
- 取消

只有点击“确认删除”后，才允许调用 B 删除能力。

## 五、本轮允许做

只允许做：

1. 在管理卡片增加“删除监控”按钮
2. 点击后发送删除确认卡片
3. 确认卡片展示对象名称、ID、URL、状态、风险提示
4. 确认删除后调用 B 删除能力
5. 取消后不调用 B
6. 成功 / 失败 / 取消都返回老板可读文本
7. 保留暂停 / 恢复
8. 保留查看更多
9. 补最小测试

## 六、本轮禁止做

禁止：

- 不做点击即删除
- 不做批量删除
- 不做批量管理
- 不做搜索过滤
- 不做排序
- 不做 PostgreSQL
- 不做权限系统
- 不做复杂回收站
- 不做多级审批
- 不新增其他业务动作
- 不重写 P12-A / B / C / D / E
- 不破坏暂停 / 恢复
- 不破坏查看更多
- 不破坏加入监控

## 七、建议实现位置

优先查看：

- app/services/feishu/cards/monitor_targets.py
- app/services/feishu/longconn.py
- app/services/feishu/client.py
- app/clients/b_service_client.py
- app/graph/nodes/execute_action.py
- tests/test_p12_c_monitor_card.py
- tests/test_p12_d_monitor_pagination.py

建议新增或扩展：

```text
tests/test_p12_f_delete_confirm.py
```

## 八、最小 payload

删除入口：

```json
{
  "action": "delete_monitor_target_request",
  "target_id": 7,
  "source": "monitor_list_card"
}
```

确认删除：

```json
{
  "action": "delete_monitor_target_confirm",
  "target_id": 7,
  "source": "delete_confirm_card"
}
```

取消：

```json
{
  "action": "delete_monitor_target_cancel",
  "target_id": 7,
  "source": "delete_confirm_card"
}
```

## 九、测试要求

至少覆盖：

1. 管理卡片出现删除监控按钮
2. 删除按钮不会直接调用删除能力
3. 点击删除按钮返回确认卡片
4. 确认卡片包含对象名称、ID、URL、状态、风险提示
5. 点击取消不调用删除能力
6. 点击确认才调用删除能力
7. 删除成功后返回老板可读文本
8. P12-C 暂停 / 恢复仍可用
9. P12-D 查看更多仍可用
10. 不包含批量删除

必须跑：

```bash
pytest -q tests/test_p10_b_query_integration.py
pytest -q tests/test_p12_b_card_action.py
pytest -q tests/test_p12_c_monitor_card.py
pytest -q tests/test_p12_d_monitor_pagination.py
pytest -q tests/test_p12_f_delete_confirm.py
bash scripts/p12_regression_check.sh
```

## 十、完成后回报格式

A. 先读了哪些文件  
B. B 是否已有 monitor target 删除能力  
C. 如果没有，是否已停止业务实现并回报  
D. 如果有，本轮实际执行了哪些命令  
E. 改了哪些文件  
F. 删除二次确认链路如何设计  
G. 是否确认“删除按钮不会直接删除”  
H. 是否保留暂停 / 恢复 / 查看更多  
I. 测试结果  
J. 是否可以进入飞书实机验收  

只允许使用简体中文。

不要只给计划。
不要只贴 diff。
不要继续做 P12-G。