# P12-D Agent 开发提示词

你现在接手的是 feishu-rpa-commerce-agent 项目。

当前唯一主线是：

P12-D：监控对象分页 / 查看更多版

## 一、当前现实

P12-A 已完成：

- discovery 搜索结果卡片展示
- 卡片失败 fallback 文本

P12-B 已完成：

- 候选卡片“加入监控”按钮
- 点击按钮可加入监控
- 群聊中优先回复群聊

P12-C 已完成：

- “看看当前监控对象”优先返回管理卡片
- 最多展示前 5 条
- active / inactive 支持暂停 / 恢复按钮

本轮 P12-D 只解决：

监控对象超过 5 个后如何继续查看。

## 二、开始前必须先读

1. docs/p12/p12-project-plan.md
2. docs/p12/P12-agent-prompt.md
3. docs/p12/p12-boss-demo-sop.md
4. docs/p12/p12-acceptance-checklist.md

如果文件不存在或不是 P12-D 口径，先停止并回报。

## 三、固定原则

A 项目仍是：

- 飞书入口层
- 消息编排层
- 老板交互层

B 项目仍是：

- 业务服务层

固定原则：

- 不合并 A / B
- A 调 B 继续按 Envelope 解包
- B 默认地址继续是 http://127.0.0.1:8005
- 不把 B 业务逻辑搬进 A
- 不重写 P12-A / P12-B / P12-C

## 四、本轮唯一目标

当“看看当前监控对象”的对象数量超过 5 个时：

- 第 1 页展示前 5 条
- 卡片底部出现“查看更多”
- 点击后展示第 2 页
- 第 2 页继续展示后续对象
- 暂停 / 恢复按钮仍可用

## 五、本轮允许做

只允许做：

1. 管理卡片 builder 支持 page / limit
2. 超过 5 条时显示“查看更多”
3. 增加 monitor_targets_next_page 回调
4. 点击后重新获取 monitor targets 并返回下一页卡片
5. 保留暂停 / 恢复按钮
6. 保留文本 fallback
7. 补最小测试

## 六、本轮禁止做

禁止：

- 不做删除按钮
- 不做批量管理
- 不做搜索过滤
- 不做排序
- 不做复杂分页状态系统
- 不做 PostgreSQL
- 不新增业务动作
- 不重写 P12-A / P12-B / P12-C
- 不破坏已有按钮回调

## 七、建议实现位置

优先查看：

- app/services/feishu/cards/monitor_targets.py
- app/services/feishu/longconn.py
- app/tasks/ingress_tasks.py
- app/clients/b_service_client.py
- tests/test_p12_c_monitor_card.py

建议新增或扩展：

```text
tests/test_p12_d_monitor_pagination.py
```

## 八、最小 payload

查看更多按钮 payload：

```json
{
  "action": "monitor_targets_next_page",
  "page": 2,
  "limit": 5,
  "source": "monitor_list_card"
}
```

要求：

- page 必须是正整数
- limit 默认 5
- limit 不允许被传成很大值
- action 必须校验
- source 仅用于排查

## 九、测试要求

至少覆盖：

1. 超过 5 个对象时出现“查看更多”
2. 第 1 页只展示前 5 条
3. next_page payload 正确
4. 第 2 页展示第 6 条以后对象
5. 没有更多数据时不显示“查看更多”
6. 暂停 / 恢复按钮仍存在
7. 不包含 delete 按钮
8. P12-B / P12-C 测试不退化

必须跑：

```bash
pytest -q tests/test_p10_b_query_integration.py
pytest -q tests/test_p12_b_card_action.py
pytest -q tests/test_p12_c_monitor_card.py
pytest -q tests/test_p12_d_monitor_pagination.py
```

## 十、完成后回报格式

A. 先读了哪些文件  
B. 当前 P12-C 管理卡片分页锚定结果  
C. 本轮实际执行了哪些命令  
D. 改了哪些文件  
E. 分页 payload 如何设计  
F. 是否保留暂停 / 恢复按钮  
G. 是否保留文本 fallback  
H. 测试结果  
I. 是否可以进入飞书实机验收  

只允许使用简体中文。

不要只给计划。
不要只贴 diff。
不要继续做 P12-E。