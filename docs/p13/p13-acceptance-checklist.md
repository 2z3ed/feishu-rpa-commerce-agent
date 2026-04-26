# P13-E 验收检查表

## 一、范围检查

- [ ] 当前阶段为 P13-E
- [ ] 当前是 A/B 双仓协同开发
- [ ] 未做飞书主动推送
- [ ] 未做价格告警
- [ ] 未做阈值规则
- [ ] 未做用户订阅
- [ ] 未做 cron UI
- [ ] 未做复杂调度系统
- [ ] 未做失败重试队列
- [ ] 未做任务优先级
- [ ] 未混入 P13-F/G/H

## 二、B 项目 trigger_source 检查

- [ ] refresh-prices 支持 trigger_source
- [ ] scheduled 可写入 run
- [ ] manual_feishu 或默认手动来源不退化
- [ ] run detail 可看到 trigger_source
- [ ] P13-D run detail 不退化
- [ ] P13-C changed_items 不退化

## 三、A 项目 Celery 任务检查

- [ ] 已新增 schedule_refresh_monitor_prices
- [ ] 任务调用 B refresh-prices
- [ ] 调用时传 trigger_source=scheduled
- [ ] 任务日志包含 START
- [ ] 任务日志包含 CALL B
- [ ] 任务日志包含 RESULT
- [ ] 异常时日志包含 FAILED
- [ ] 不主动发送飞书消息

## 四、Celery Beat 检查

- [ ] beat_schedule 中有 refresh-monitor-prices-every-5-minutes
- [ ] schedule 为每 5 分钟
- [ ] task name 与实际 task 注册一致
- [ ] worker 能执行该 task
- [ ] beat 能触发该 task

## 五、回归检查

- [ ] 手动“刷新监控价格”仍可用
- [ ] 手动刷新仍生成 run_id
- [ ] 查看刷新结果 run_id 仍可用
- [ ] 查看价格历史仍可用
- [ ] 看看当前监控对象仍可用
- [ ] P12 卡片按钮不退化

## 六、测试检查

B 项目：

- [ ] pytest -q tests/test_monitor_management_api.py 通过
- [ ] P13-E 新增 B 测试通过

A 项目：

- [ ] pytest -q tests/test_p10_b_query_integration.py 通过
- [ ] pytest -q tests/test_p13_a_monitor_price_card.py 通过
- [ ] P13-E 新增 A 测试通过
- [ ] bash scripts/p12_regression_check.sh 通过

## 七、实机验收

- [ ] B 服务运行
- [ ] Redis / broker 运行
- [ ] worker 运行
- [ ] beat 运行
- [ ] 定时任务触发
- [ ] 生成 run_id
- [ ] 飞书可查询 run detail
- [ ] 手动刷新回归通过
- [ ] P13-B 回归通过
- [ ] P12 回归通过

## 八、提交检查

- [ ] B 项目先提交
- [ ] A 项目后提交
- [ ] B 提交不混入 A 文件
- [ ] A 提交不混入 B 文件
- [ ] 两仓 git status 已复核
- [ ] 两仓 git diff --stat 已复核

## 九、通过结论

P13-E 通过条件：

- [ ] B trigger_source 通过
- [ ] A Celery task 通过
- [ ] Celery Beat 配置通过
- [ ] 定时执行生成 run_id 通过
- [ ] run detail 查询通过
- [ ] 手动刷新不退化
- [ ] P13-A/B/C/D 回归通过
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