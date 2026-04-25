# P13-C 验收检查表

## 一、范围检查

- [ ] 当前阶段为 P13-C
- [ ] 当前是 A/B 双仓协同开发
- [ ] 未做阈值规则
- [ ] 未做价格低于多少提醒
- [ ] 未做定时任务
- [ ] 未做主动推送
- [ ] 未做订阅系统
- [ ] 未做邮件 / 短信
- [ ] 未做价格曲线图
- [ ] 未做图表卡片
- [ ] 未做库存 / SKU
- [ ] 未混入 P13-D/E/F

## 二、B 项目刷新结构检查

- [ ] refresh-prices 返回 total
- [ ] refresh-prices 返回 refreshed
- [ ] refresh-prices 返回 changed
- [ ] refresh-prices 返回 failed
- [ ] refresh-prices 返回 items 或 changed_items
- [ ] item 包含 product_id
- [ ] item 包含 product_name
- [ ] item 包含 current_price
- [ ] item 包含 last_price
- [ ] item 包含 price_delta
- [ ] item 包含 price_delta_percent
- [ ] item 包含 price_changed
- [ ] item 包含 price_source
- [ ] item 包含 last_checked_at

## 三、B 项目回归检查

- [ ] refresh-price 单对象不退化
- [ ] refresh-prices 批量不退化
- [ ] price snapshot 写入不退化
- [ ] price-history 查询不退化
- [ ] pause / resume / delete 不退化

## 四、A 项目文案检查

- [ ] 有变化时显示“本轮价格变化：X 个”
- [ ] 有变化时展示前 5 条
- [ ] 每条展示名称
- [ ] 每条展示当前价
- [ ] 每条展示上次价
- [ ] 每条展示涨跌金额
- [ ] 每条展示涨跌百分比
- [ ] 超过 5 条时提示剩余数量
- [ ] 无变化时显示“本轮暂无价格变化”
- [ ] 显示失败数
- [ ] B 服务错误时老板可读

## 五、A 项目回归检查

- [ ] “刷新监控价格”仍可用
- [ ] “查看价格历史 7”仍可用
- [ ] “查看第 N 个价格历史”仍可用
- [ ] “看看当前监控对象”仍可用
- [ ] P12 卡片按钮不退化

## 六、测试检查

B 项目：

- [ ] pytest -q tests/test_monitor_management_api.py 通过
- [ ] P13-C 新增 B 测试通过

A 项目：

- [ ] pytest -q tests/test_p10_b_query_integration.py 通过
- [ ] pytest -q tests/test_p13_a_monitor_price_card.py 通过
- [ ] P13-B 测试通过
- [ ] P13-C 新增 A 测试通过
- [ ] bash scripts/p12_regression_check.sh 通过

## 七、实机验收

- [ ] 飞书“刷新监控价格”显示变化摘要
- [ ] 有变化时展示变化对象
- [ ] 无变化时展示暂无变化
- [ ] 超过 5 条时截断展示
- [ ] 价格历史回归通过
- [ ] 管理卡片回归通过
- [ ] P12 回归通过

## 八、提交检查

- [ ] B 项目先提交
- [ ] A 项目后提交
- [ ] B 提交不混入 A 文件
- [ ] A 提交不混入 B 文件
- [ ] 两仓 git status 已复核
- [ ] 两仓 git diff --stat 已复核

## 九、通过结论

P13-C 通过条件：

- [ ] B refresh-prices 结构增强通过
- [ ] A 变化提醒摘要通过
- [ ] P13-A 不退化
- [ ] P13-B 不退化
- [ ] P12 回归通过
- [ ] A/B 分仓测试通过
- [ ] A/B 分仓提交

最终结论：

- [ ] 通过
- [ ] 不通过

阻塞点：

```text
如未通过，在这里记录原因。
```