# P13-G 验收检查表

## 一、范围检查

- [ ] 当前阶段为 P13-G
- [ ] 当前是 A/B 双仓协同开发
- [ ] 未做主动推送
- [ ] 未做价格告警
- [ ] 未做阈值规则
- [ ] 未做自动重试
- [ ] 未做失败重试队列
- [ ] 未做 Playwright
- [ ] 未做浏览器渲染
- [ ] 未做代理池
- [ ] 未做站点适配规则库
- [ ] 未做人工修正价格
- [ ] 未混入 P13-H/I/J

## 二、B 项目字段检查

- [ ] product 有 price_probe_status
- [ ] product 有 price_probe_error
- [ ] product 有 price_probe_checked_at
- [ ] 可选有 price_probe_raw_text
- [ ] monitor target list 返回 probe 状态
- [ ] run item 返回 probe 状态

## 三、B 项目状态语义检查

- [ ] 成功提取写 success
- [ ] fallback mock 写 fallback_mock
- [ ] 无价格写 no_price_found
- [ ] 超时写 timeout
- [ ] budget exceeded 可识别
- [ ] unknown 可兜底
- [ ] 不影响 refresh-prices 完成

## 四、A 项目管理卡片检查

- [ ] success 显示采集状态
- [ ] fallback_mock 显示采集状态
- [ ] failed 显示采集状态
- [ ] 有 error 时显示采集原因
- [ ] price_source 展示不退化
- [ ] 未采集对象文案不退化

## 五、A 项目查询命令检查

- [ ] 支持“查看价格采集失败”
- [ ] 支持“查看采集失败对象”
- [ ] 支持“查看mock价格对象”
- [ ] 支持“查看真实价格对象”
- [ ] 查询结果最多展示前 10 条
- [ ] 超过 10 条有剩余提示
- [ ] 无结果时文案清楚

## 六、回归检查

- [ ] P13-F Hush Home 真实提取不退化
- [ ] P13-E 定时刷新不退化
- [ ] P13-D run 查询不退化
- [ ] P13-C 变化摘要不退化
- [ ] P13-B 价格历史不退化
- [ ] P13-A 当前价格不退化
- [ ] P12-B/C/D/F 不退化

## 七、测试检查

B 项目：

- [ ] pytest -q tests/test_monitor_management_api.py 通过
- [ ] pytest -q tests/test_price_probe_service.py 通过
- [ ] P13-G 新增 B 测试通过

A 项目：

- [ ] pytest -q tests/test_p10_b_query_integration.py 通过
- [ ] pytest -q tests/test_p13_a_monitor_price_card.py 通过
- [ ] P13-G 新增 A 测试通过
- [ ] bash scripts/p12_regression_check.sh 通过

## 八、实机验收

- [ ] 管理卡片展示采集状态
- [ ] 查看价格采集失败通过
- [ ] 查看mock价格对象通过
- [ ] 查看真实价格对象通过
- [ ] run detail 可追踪 probe 状态
- [ ] P13-F 回归通过
- [ ] P13-E 回归通过
- [ ] P12 回归通过

## 九、提交检查

- [ ] B 项目先提交
- [ ] A 项目后提交
- [ ] B 提交不混入 A 文件
- [ ] A 提交不混入 B 文件
- [ ] 两仓 git status 已复核
- [ ] 两仓 git diff --stat 已复核

## 十、通过结论

P13-G 通过条件：

- [ ] B probe 状态记录通过
- [ ] B list / run detail 返回通过
- [ ] A 卡片展示通过
- [ ] A 查询命令通过
- [ ] P13-A/B/C/D/E/F 回归通过
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