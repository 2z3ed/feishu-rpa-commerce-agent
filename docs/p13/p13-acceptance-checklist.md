# P13-D 验收检查表

## 一、范围检查

- [ ] 当前阶段为 P13-D
- [ ] 当前是 A/B 双仓协同开发
- [ ] 未做定时任务
- [ ] 未做主动推送
- [ ] 未做阈值告警
- [ ] 未做失败重试队列
- [ ] 未做复杂调度
- [ ] 未做价格图表
- [ ] 未做后台管理页面
- [ ] 未做 run 列表页面
- [ ] 未混入 P13-E/F/G

## 二、B 项目 run 存储检查

- [ ] 有 price_refresh_runs 结构
- [ ] 有 price_refresh_run_items 结构
- [ ] refresh-prices 每次生成 run_id
- [ ] run 保存 status
- [ ] run 保存 total
- [ ] run 保存 refreshed
- [ ] run 保存 changed
- [ ] run 保存 failed
- [ ] run 保存 started_at
- [ ] run 保存 finished_at
- [ ] run 保存 duration_ms
- [ ] run 保存 trigger_source

## 三、B 项目 item 明细检查

- [ ] item 保存 run_id
- [ ] item 保存 product_id
- [ ] item 保存 product_name
- [ ] item 保存 status
- [ ] item 保存 current_price
- [ ] item 保存 last_price
- [ ] item 保存 price_delta
- [ ] item 保存 price_delta_percent
- [ ] item 保存 price_changed
- [ ] item 保存 price_source
- [ ] item 支持 error_message
- [ ] item 保存 checked_at

## 四、B 项目 API 检查

- [ ] refresh-prices 返回 run_id
- [ ] refresh-prices 返回 status
- [ ] refresh-prices 保留 P13-C changed_items / items
- [ ] GET /internal/monitor/price-refresh-runs/{run_id} 可用
- [ ] run_id 不存在时返回 envelope error
- [ ] run detail 返回 summary
- [ ] run detail 返回 items

## 五、A 项目命令检查

- [ ] 刷新监控价格回复展示 run_id
- [ ] 支持“查看刷新结果 PRR-xxx”
- [ ] 支持“查看价格刷新批次 PRR-xxx”
- [ ] 支持“查看刷新批次 PRR-xxx”
- [ ] A 调 B run detail API
- [ ] run 不存在时返回老板可读错误

## 六、A 项目展示检查

- [ ] run detail 显示 run_id
- [ ] run detail 显示 status
- [ ] run detail 显示 total
- [ ] run detail 显示 refreshed
- [ ] run detail 显示 changed
- [ ] run detail 显示 failed
- [ ] run detail 显示 duration_ms
- [ ] run detail 展示变化对象
- [ ] 无变化对象时提示清楚

## 七、回归检查

- [ ] P13-A 刷新价格不退化
- [ ] P13-B 价格历史不退化
- [ ] P13-C 变化摘要不退化
- [ ] P12-B 候选加入监控通过
- [ ] P12-C 暂停 / 恢复通过
- [ ] P12-D 查看更多通过
- [ ] P12-F 删除二次确认通过

## 八、测试检查

B 项目：

- [ ] pytest -q tests/test_monitor_management_api.py 通过
- [ ] P13-D 新增 B 测试通过

A 项目：

- [ ] pytest -q tests/test_p10_b_query_integration.py 通过
- [ ] pytest -q tests/test_p13_a_monitor_price_card.py 通过
- [ ] P13-D 新增 A 测试通过
- [ ] bash scripts/p12_regression_check.sh 通过

## 九、实机验收

- [ ] 飞书“刷新监控价格”返回 run_id
- [ ] 飞书“查看刷新结果 run_id”成功
- [ ] run detail summary 正确
- [ ] run detail 变化对象正确
- [ ] 不存在 run_id 返回可读错误
- [ ] P13-B 回归通过
- [ ] P12 回归通过

## 十、提交检查

- [ ] B 项目先提交
- [ ] A 项目后提交
- [ ] B 提交不混入 A 文件
- [ ] A 提交不混入 B 文件
- [ ] 两仓 git status 已复核
- [ ] 两仓 git diff --stat 已复核

## 十一、通过结论

P13-D 通过条件：

- [ ] B refresh run 留痕通过
- [ ] B run detail API 通过
- [ ] A 展示 run_id 通过
- [ ] A run 查询通过
- [ ] P13-A/B/C 回归通过
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