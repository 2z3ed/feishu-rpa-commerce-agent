# P12-E Agent 开发提示词

你现在接手的是 feishu-rpa-commerce-agent 项目。

当前唯一主线是：

P12-E：飞书卡片交互层收口与演示稳定版

## 一、当前现实

P12-A 已完成：

- 搜索商品返回候选卡片
- 卡片失败 fallback 文本

P12-B 已完成：

- 候选卡片“加入监控”按钮
- 点击按钮成功纳管
- 群聊结果优先回复群聊

P12-C 已完成：

- “看看当前监控对象”返回管理卡片
- 支持暂停 / 恢复

P12-D 已完成：

- 超过 5 个监控对象时支持“查看更多”
- 下一页仍保留暂停 / 恢复按钮

本轮不是做新功能。

本轮只做：

P12 卡片交互层收口、演示稳定、文档统一、回归命令固化。

## 二、开始前必须先读

1. docs/p12/p12-project-plan.md
2. docs/p12/P12-agent-prompt.md
3. docs/p12/p12-boss-demo-sop.md
4. docs/p12/p12-acceptance-checklist.md
5. README.md
6. AGENTS.md

如果文件不存在或不是 P12-E 口径，先停止并回报。

## 三、本轮允许做

允许：

1. 更新 README P12 阶段说明
2. 更新 docs/p12 四份约束文件为 P12-E 收口口径
3. 新增 P12 收口摘要文档
4. 新增 P12 回归检查脚本
5. 统一老板可读错误提示
6. 补少量测试
7. 清理不必要的临时日志

## 四、本轮禁止做

禁止：

- 不做删除按钮
- 不做批量管理
- 不做搜索过滤
- 不做排序
- 不做 PostgreSQL
- 不新增业务动作
- 不重写 P12-A / B / C / D
- 不破坏已有卡片交互链路
- 不继续做 P12-F / G / H

## 五、建议产物

建议新增：

```text
docs/p12/p12-closure-summary.md
scripts/p12_regression_check.sh
```

收口文档至少写清：

- P12-A 做了什么
- P12-B 做了什么
- P12-C 做了什么
- P12-D 做了什么
- 当前老板演示路径
- 当前测试命令
- 当前已知后移项
- 下一阶段建议

回归脚本至少包含：

```bash
pytest -q tests/test_p10_b_query_integration.py
pytest -q tests/test_p12_b_card_action.py
pytest -q tests/test_p12_c_monitor_card.py
pytest -q tests/test_p12_d_monitor_pagination.py
```

完成后建议按以下顺序执行：

```bash
pytest -q tests/test_p10_b_query_integration.py
pytest -q tests/test_p12_b_card_action.py
pytest -q tests/test_p12_c_monitor_card.py
pytest -q tests/test_p12_d_monitor_pagination.py
bash scripts/p12_regression_check.sh
git status --short
git diff --stat
```

## 六、完成后回报格式

A. 先读了哪些文件  
B. P12-E 收口范围确认  
C. 本轮实际执行了哪些命令  
D. 改了哪些文件  
E. 新增了哪些收口文档或脚本  
F. P12-A/B/C/D 回归测试结果  
G. 是否混入删除 / 批量 / 搜索过滤 / 排序  
H. 是否可以进入最终收口提交  

只允许使用简体中文。

不要只给计划。
不要继续做 P12-F。