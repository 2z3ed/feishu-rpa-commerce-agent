# P12-E 验收检查表

## 一、范围检查

- [ ] 当前阶段为 P12-E
- [ ] 只做 P12 收口
- [ ] 未做删除按钮
- [ ] 未做批量管理
- [ ] 未做搜索过滤
- [ ] 未做排序
- [ ] 未新增业务动作
- [ ] 未重写 P12-A / B / C / D

## 二、文档检查

- [ ] README 已更新 P12 阶段说明
- [ ] AGENTS.md 当前阶段入口为 P12-E
- [ ] docs/p12/p12-project-plan.md 已切到 P12-E
- [ ] docs/p12/P12-agent-prompt.md 已切到 P12-E
- [ ] docs/p12/p12-boss-demo-sop.md 已切到 P12-E
- [ ] docs/p12/p12-acceptance-checklist.md 已切到 P12-E
- [ ] 已新增或更新 P12 收口摘要文档

## 三、回归脚本检查

- [ ] 已新增或更新 P12 回归脚本
- [ ] 脚本包含 P10 B query 回归测试
- [ ] 脚本包含 P12-B 测试
- [ ] 脚本包含 P12-C 测试
- [ ] 脚本包含 P12-D 测试

## 四、功能回归检查

- [ ] P12-A 搜索候选卡片通过
- [ ] P12-B 候选按钮加入监控通过
- [ ] P12-C 监控对象管理卡片通过
- [ ] P12-D 查看更多通过
- [ ] 暂停 / 恢复通过
- [ ] 文本“加入监控第 N 个”通过
- [ ] 卡片失败 fallback 文本

## 五、后移项检查

- [ ] 删除监控对象已明确后移
- [ ] 批量管理已明确后移
- [ ] 搜索过滤已明确后移
- [ ] 排序已明确后移
- [ ] 没有提前实现后移项

## 六、测试检查

- [ ] pytest -q tests/test_p10_b_query_integration.py 通过
- [ ] pytest -q tests/test_p12_b_card_action.py 通过
- [ ] pytest -q tests/test_p12_c_monitor_card.py 通过
- [ ] pytest -q tests/test_p12_d_monitor_pagination.py 通过
- [ ] scripts/p12_regression_check.sh 可执行并通过
- [ ] git status --short 已检查
- [ ] git diff --stat 已检查

## 七、通过结论

P12-E 通过条件：

- [ ] 文档已收口
- [ ] README 已更新
- [ ] 回归脚本已固化
- [ ] P12-A/B/C/D 测试通过
- [ ] 老板演示 SOP 完整
- [ ] 后移项清楚
- [ ] 未混入 P12-F/G/H

最终结论：

- [ ] 通过
- [ ] 不通过

阻塞点：

```text
如未通过，在这里记录原因。
```