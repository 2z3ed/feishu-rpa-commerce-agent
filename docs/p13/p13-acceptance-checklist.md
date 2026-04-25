# P13-A 验收检查表

## 一、范围检查

- [ ] 当前阶段为 P13-A
- [ ] 当前是 A/B 双仓协同开发
- [ ] 未继续深挖 P12 UI
- [ ] 未做定时任务
- [ ] 未做复杂爬虫
- [ ] 未做代理池
- [ ] 未做历史价格表
- [ ] 未做价格告警
- [ ] 未做库存 / SKU
- [ ] 未混入 P13-B/C/D/E

## 二、B 项目字段检查

- [ ] monitor target 返回 current_price
- [ ] monitor target 返回 last_price
- [ ] monitor target 返回 price_delta
- [ ] monitor target 返回 price_delta_percent
- [ ] monitor target 返回 price_changed
- [ ] monitor target 返回 last_checked_at
- [ ] monitor target 返回 price_source
- [ ] 未采集对象字段允许为空

## 三、B 项目刷新检查

- [ ] 单对象刷新价格可用
- [ ] 第一次刷新写入 current_price
- [ ] 第二次刷新写入 last_price
- [ ] price_delta 计算正确
- [ ] price_delta_percent 计算正确
- [ ] price_changed 计算正确
- [ ] last_checked_at 更新
- [ ] price_source 有值
- [ ] pause / resume 不退化
- [ ] delete 不退化

## 四、A 项目命令检查

- [ ] 支持“刷新监控价格”
- [ ] 支持“刷新监控对象价格”
- [ ] 支持“刷新价格”
- [ ] A 调 B 刷新接口
- [ ] 成功返回老板可读汇总
- [ ] 失败返回老板可读错误
- [ ] 不吐堆栈

## 五、A 项目卡片展示检查

- [ ] 未采集对象显示“当前价格：暂未采集”
- [ ] 已采集对象显示 current_price
- [ ] 有 last_price 时显示上次价格
- [ ] 有 delta 时显示上涨 / 下降
- [ ] 显示 delta percent
- [ ] 显示 last_checked_at
- [ ] 显示 price_source
- [ ] 不破坏暂停 / 恢复 / 删除 / 查看更多按钮

## 六、P12 回归检查

- [ ] P12-B 候选加入监控通过
- [ ] P12-C 暂停 / 恢复通过
- [ ] P12-D 查看更多通过
- [ ] P12-F 删除二次确认通过
- [ ] P12 回归脚本通过

## 七、测试检查

B 项目：

- [ ] pytest -q tests/test_monitor_management_api.py 通过
- [ ] 新增价格测试通过

A 项目：

- [ ] pytest -q tests/test_p10_b_query_integration.py 通过
- [ ] pytest -q tests/test_p12_b_card_action.py 通过
- [ ] pytest -q tests/test_p12_c_monitor_card.py 通过
- [ ] pytest -q tests/test_p12_d_monitor_pagination.py 通过
- [ ] pytest -q tests/test_p12_f_delete_confirm.py 通过
- [ ] P13-A 新增测试通过
- [ ] bash scripts/p12_regression_check.sh 通过

## 八、实机验收

- [ ] 飞书“看看当前监控对象”显示暂未采集
- [ ] 飞书“刷新监控价格”成功
- [ ] 再看管理卡片显示 current_price
- [ ] 第二次刷新后显示 last_price / delta
- [ ] P12 交互能力不退化

## 九、提交检查

- [ ] B 项目先提交
- [ ] A 项目后提交
- [ ] B 提交不混入 A 文件
- [ ] A 提交不混入 B 文件
- [ ] 两仓 git status 已复核
- [ ] 两仓 git diff --stat 已复核

## 十、通过结论

P13-A 通过条件：

- [ ] B 价格数据闭环通过
- [ ] A 飞书命令刷新通过
- [ ] A 卡片价格展示通过
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