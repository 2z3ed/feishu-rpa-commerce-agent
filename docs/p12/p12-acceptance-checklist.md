
---

【docs/p12/p12-acceptance-checklist.md】

```md
# P12-C 验收检查表

## 一、范围检查

- [ ] 当前阶段为 P12-C
- [ ] 只做监控对象管理卡片
- [ ] 未重写 P12-A
- [ ] 未重写 P12-B
- [ ] 未做删除按钮
- [ ] 未做分页
- [ ] 未做批量管理
- [ ] 未做 PostgreSQL
- [ ] 未新增业务主线

## 二、monitor list 链路检查

- [ ] 已确认“看看当前监控对象”的 intent_code
- [ ] 已确认当前 B 服务调用方式
- [ ] 已确认当前文本 result_summary 生成位置
- [ ] 已确认卡片失败可 fallback 文本
- [ ] 已确认 B 是否已有 pause / resume 能力

## 三、管理卡片检查

- [ ] 成功时优先返回飞书卡片
- [ ] 卡片展示监控对象总数
- [ ] 卡片展示对象名称
- [ ] 卡片展示对象ID
- [ ] 卡片展示对象状态
- [ ] 卡片展示 URL
- [ ] 最多展示前 5 条
- [ ] 没有删除按钮
- [ ] 没有分页按钮

## 四、按钮检查

- [ ] active 对象显示“暂停监控”
- [ ] inactive 对象显示“恢复监控”
- [ ] 按钮 payload 包含 action
- [ ] 按钮 payload 包含 target_id
- [ ] 按钮 payload 包含 source
- [ ] 非法 action 不会误触发
- [ ] 非法 target_id 返回老板可读错误

## 五、业务复用检查

- [ ] A 没有直接写 B 的业务数据
- [ ] A 调 B 仍按 Envelope 解包
- [ ] B 默认地址仍是 http://127.0.0.1:8005
- [ ] 没有把 B 业务逻辑搬进 A
- [ ] 如果 B 未提供 pause / resume，已明确记录后移

## 六、回归检查

- [ ] P12-A 搜索候选卡片仍可用
- [ ] P12-B 候选按钮加入监控仍可用
- [ ] 文本“加入监控第 N 个”仍可用
- [ ] 搜索失败仍返回文本错误
- [ ] 监控对象卡片失败时 fallback 文本

## 七、测试检查

- [ ] pytest -q tests/test_p10_b_query_integration.py 通过
- [ ] pytest -q tests/test_p12_b_card_action.py 通过
- [ ] pytest -q tests/test_p12_c_monitor_card.py 通过
- [ ] git diff --stat 已复核
- [ ] git status --short 已复核
- [ ] 无 P12-D 内容混入

## 八、实机验收

- [ ] 飞书发送“看看当前监控对象”返回管理卡片
- [ ] 卡片字段完整
- [ ] active / inactive 展示正确
- [ ] 暂停 / 恢复按钮按能力验证
- [ ] P12-A 回归通过
- [ ] P12-B 回归通过
- [ ] 文本加入监控回归通过

## 九、通过结论

P12-C 通过条件：

- [ ] 管理卡片展示通过
- [ ] 文本 fallback 通过
- [ ] P12-A 不退化
- [ ] P12-B 不退化
- [ ] 未混入 P12-D
- [ ] 暂停 / 恢复按钮已通过，或明确后移原因

最终结论：

- [ ] 通过
- [ ] 不通过

阻塞点：

```text
如未通过，在这里记录原因。