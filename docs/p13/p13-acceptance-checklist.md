# P13-H 验收检查表

## 一、范围检查

- [ ] 当前阶段为 P13-H
- [ ] 当前是 A/B 双仓协同开发
- [ ] 未做自动重试队列
- [ ] 未做指数退避
- [ ] 未做定时重试
- [ ] 未做失败告警
- [ ] 未做主动推送
- [ ] 未做阈值提醒
- [ ] 未做代理池
- [ ] 未做 Playwright
- [ ] 未做浏览器渲染
- [ ] 未做站点适配规则库
- [ ] 未做人工修正价格
- [ ] 未混入 P13-I/J/K

## 二、B 项目单对象重试检查

- [ ] POST /internal/monitor/{id}/retry-price-probe 可用
- [ ] 对象不存在时返回可读错误
- [ ] 重试成功写 current_price
- [ ] 重试成功写 price_source=html_extract_preview
- [ ] 重试成功写 price_probe_status=success
- [ ] 重试失败写 price_probe_error
- [ ] 重试失败更新 price_probe_checked_at

## 三、B 项目批量重试检查

- [ ] POST /internal/monitor/retry-price-probes 可用
- [ ] 只选择 failed / fallback_mock / mock_price / unknown 对象
- [ ] 不重试已 success 的真实价格对象
- [ ] 返回 total / retried / success / failed
- [ ] 返回成功对象列表
- [ ] 返回仍失败对象列表
- [ ] 无可重试对象时文案清楚

## 四、A 项目命令检查

- [ ] 支持“重试价格采集”
- [ ] 支持“重试采集失败对象”
- [ ] 支持“重试mock价格对象”
- [ ] 支持“重试对象 7 价格采集”
- [ ] 支持“重试对象ID 7 价格采集”
- [ ] 单对象按对象ID，不按列表序号
- [ ] 不支持“第 N 个”时有明确文案或不误识别

## 五、A 项目展示检查

- [ ] 批量重试显示重试对象数量
- [ ] 批量重试显示成功转真实价格数量
- [ ] 批量重试显示仍失败数量
- [ ] 成功对象展示当前价格和来源
- [ ] 仍失败对象展示状态和原因
- [ ] 单对象成功文案清楚
- [ ] 单对象失败文案清楚
- [ ] 无可重试对象文案清楚

## 六、回归检查

- [ ] P13-G 查看价格采集失败不退化
- [ ] P13-G 查看mock价格对象不退化
- [ ] P13-G 查看真实价格对象不退化
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
- [ ] P13-H 新增 B 测试通过

A 项目：

- [ ] pytest -q tests/test_p10_b_query_integration.py 通过
- [ ] pytest -q tests/test_p13_a_monitor_price_card.py 通过
- [ ] P13-H 新增 A 测试通过
- [ ] bash scripts/p12_regression_check.sh 通过

## 八、实机验收

- [ ] 查看失败 / mock 对象通过
- [ ] 批量重试通过
- [ ] 单对象重试成功场景通过
- [ ] 单对象重试失败场景通过
- [ ] 重试后管理卡片状态更新
- [ ] 重试后分类查询更新
- [ ] P12/P13 回归通过

## 九、提交检查

- [ ] B 项目先提交
- [ ] A 项目后提交
- [ ] B 提交不混入 A 文件
- [ ] A 提交不混入 B 文件
- [ ] 两仓 git status 已复核
- [ ] 两仓 git diff --stat 已复核

## 十、通过结论

P13-H 通过条件：

- [ ] B 单对象重试通过
- [ ] B 批量重试通过
- [ ] A 重试命令通过
- [ ] A 重试结果展示通过
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