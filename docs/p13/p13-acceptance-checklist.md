# P13-I 验收检查表

## 一、范围检查

- [ ] 当前阶段为 P13-I
- [ ] 当前是 A/B 双仓协同开发
- [ ] 未做完整决策建议系统
- [ ] 未做建议分级
- [ ] 未做处理优先级系统
- [ ] 未做阈值订阅
- [ ] 未做主动推送
- [ ] 未做复杂规则引擎
- [ ] 未做 LLM 自动判断
- [ ] 未做图表看板
- [ ] 未做后台页面
- [ ] 未做 Playwright / 浏览器渲染
- [ ] 未做代理池
- [ ] 未做站点规则库
- [ ] 未混入 P13-J

## 二、B 项目字段检查

- [ ] product 有 price_confidence
- [ ] product 有 price_page_type
- [ ] product 有 price_anomaly_status
- [ ] product 有 price_anomaly_reason
- [ ] product 有 price_action_suggestion
- [ ] list 返回诊断字段
- [ ] run detail 返回诊断字段

## 三、B 项目规则检查

- [ ] product_detail + html success -> high
- [ ] html success + unknown page type -> medium
- [ ] listing/search/article -> low
- [ ] mock/fallback/failed -> low
- [ ] 大幅涨跌 -> suspected
- [ ] current_price > 10000 -> suspected
- [ ] mock_price 变化 -> suspected
- [ ] 正常价格 -> normal
- [ ] 能生成轻量建议

## 四、A 项目管理卡片检查

- [ ] 展示可信度
- [ ] 展示页面类型
- [ ] 展示异常状态
- [ ] 展示异常原因
- [ ] 展示建议
- [ ] 缺字段时使用 unknown / -

## 五、A 项目查询命令检查

- [ ] 支持“查看价格异常对象”
- [ ] 支持“查看低可信价格对象”
- [ ] 支持“查看价格监控状态”
- [ ] 支持“价格监控概览”
- [ ] 最多展示前 10 条
- [ ] 超过 10 条显示剩余提示
- [ ] 无结果时文案清楚

## 六、回归检查

- [ ] P13-H 重试价格采集不退化
- [ ] P13-G 查看采集失败不退化
- [ ] P13-G 查看mock价格对象不退化
- [ ] P13-G 查看真实价格对象不退化
- [ ] P13-F 真实价格提取不退化
- [ ] P13-E 定时刷新不退化
- [ ] P13-D run 查询不退化
- [ ] P13-C 变化摘要不退化
- [ ] P13-B 价格历史不退化
- [ ] P12-B/C/D/F 不退化

## 七、测试检查

B 项目：

- [ ] pytest -q tests/test_monitor_management_api.py 通过
- [ ] pytest -q tests/test_price_probe_service.py 通过
- [ ] P13-I 新增 B 测试通过

A 项目：

- [ ] pytest -q tests/test_p10_b_query_integration.py 通过
- [ ] pytest -q tests/test_p13_a_monitor_price_card.py 通过
- [ ] P13-I 新增 A 测试通过
- [ ] bash scripts/p12_regression_check.sh 通过

## 八、实机验收

- [ ] 管理卡片展示诊断字段
- [ ] 查看价格异常对象通过
- [ ] 查看低可信价格对象通过
- [ ] 查看价格监控状态通过
- [ ] P13-H 重试回归通过
- [ ] P13-G 查询回归通过
- [ ] P12/P13 回归通过

## 九、提交检查

- [ ] B 项目先提交
- [ ] A 项目后提交
- [ ] B 提交不混入 A 文件
- [ ] A 提交不混入 B 文件
- [ ] 两仓 git status 已复核
- [ ] 两仓 git diff --stat 已复核

## 十、通过结论

P13-I 通过条件：

- [ ] B 诊断字段通过
- [ ] B 异常检测通过
- [ ] A 卡片展示通过
- [ ] A 查询命令通过
- [ ] P13-H 回归通过
- [ ] P13-A/B/C/D/E/F/G 回归通过
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