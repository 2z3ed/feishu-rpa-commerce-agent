# P13-F 验收检查表

## 一、范围检查

- [ ] 当前阶段为 P13-F
- [ ] 当前是 A/B 双仓协同开发
- [ ] 未做反爬
- [ ] 未做代理池
- [ ] 未做 Playwright
- [ ] 未做浏览器渲染
- [ ] 未做多站点完美适配
- [ ] 未做 SKU 规格选择
- [ ] 未做币种换算系统
- [ ] 未做主动推送
- [ ] 未做价格告警
- [ ] 未混入 P13-G/H/I

## 二、B 项目 price probe 检查

- [ ] 有最小 HTML price probe
- [ ] 能解析 HK$1,280.00
- [ ] 能解析 $1,280.00
- [ ] 能解析常见价格格式
- [ ] 解析结果为 float
- [ ] 保留 raw_text
- [ ] 成功时 price_source=html_extract_preview
- [ ] 失败时有 error_message

## 三、B 项目 refresh 集成检查

- [ ] refresh_price 优先尝试 HTML 提取
- [ ] 提取成功写入 current_price
- [ ] 提取成功写入 price_source
- [ ] 提取失败不会中断刷新
- [ ] 提取失败 fallback 到 mock_price 或 unknown
- [ ] last_price / current_price 规则不退化
- [ ] price_snapshot 不退化
- [ ] refresh run 不退化
- [ ] scheduled trigger 不退化

## 四、A 项目展示检查

- [ ] 管理卡片展示 current_price
- [ ] 管理卡片展示 price_source=html_extract_preview
- [ ] fallback 时展示 fallback 来源
- [ ] 未采集对象文案不退化
- [ ] 不新增复杂交互

## 五、实机样本检查

- [ ] Hush Home 对象存在
- [ ] Hush Home URL 可刷新
- [ ] 页面价格 HK$1,280.00 可提取
- [ ] current_price 约为 1280.0
- [ ] price_source=html_extract_preview
- [ ] 价格历史中有记录
- [ ] run detail 中可追踪

## 六、回归检查

- [ ] P13-A 刷新价格不退化
- [ ] P13-B 价格历史不退化
- [ ] P13-C 变化摘要不退化
- [ ] P13-D run 查询不退化
- [ ] P13-E 定时刷新不退化
- [ ] P12-B/C/D/F 不退化

## 七、测试检查

B 项目：

- [ ] pytest -q tests/test_monitor_management_api.py 通过
- [ ] price probe 新增测试通过

A 项目：

- [ ] pytest -q tests/test_p10_b_query_integration.py 通过
- [ ] pytest -q tests/test_p13_a_monitor_price_card.py 通过
- [ ] bash scripts/p12_regression_check.sh 通过
- [ ] 如有 P13-F A 测试，必须通过

## 八、提交检查

- [ ] B 项目先提交
- [ ] A 项目后提交
- [ ] B 提交不混入 A 文件
- [ ] A 提交不混入 B 文件
- [ ] 两仓 git status 已复核
- [ ] 两仓 git diff --stat 已复核

## 九、通过结论

P13-F 通过条件：

- [ ] B HTML 提取通过
- [ ] Hush Home 样本通过
- [ ] fallback 稳定
- [ ] A 展示 html_extract_preview 通过
- [ ] P13-A/B/C/D/E 回归通过
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