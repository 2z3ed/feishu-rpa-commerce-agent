# P14-Z 项目计划：P14 LLM 智能增强层总收口文档

## 一、阶段名称

P14-Z：P14 LLM 智能增强层总收口文档

## 二、本轮目标

本轮只做 P14 总收口文档。

建议新增：

docs/p14/p14-closure-summary.md

该文档用于交接和复盘 P14-A / P14-B / P14-C / P14-D 四个阶段，方便后续 GPT、agent 或人工继续进入 P15 OCR 主线。

## 三、当前已完成阶段

### P14-A：LLM 意图解析 fallback

已完成：

- 规则未命中时触发 LLM fallback
- intent / slots / confidence / clarification_question 结构化输出
- allowlist 校验
- confidence 阈值
- 低置信度澄清
- system.confirm_task 禁止由 LLM fallback 生成
- product.update_price 不绕过确认
- task_steps 留痕
- 飞书实机验收通过

### P14-B：LLM 监控对象运营总结

已完成：

- 新增 ecom_watch.monitor_summary
- 支持价格监控总体总结
- 支持监控健康度总结
- 支持重点处理对象总结
- 支持 summary_focus=overview / health_check / priority_targets
- provider 失败降级为规则摘要
- task_steps 留痕
- 飞书实机验收通过

### P14-C：LLM 异常原因解释

已完成：

- 新增 ecom_watch.anomaly_explanation
- 支持异常原因解释
- 支持低可信对象解释
- 支持 mock_price / fallback_mock 解释
- 支持人工处理原因解释
- 支持 explanation_focus=overview / low_confidence / mock_source / manual_review
- provider 失败降级为规则解释
- task_steps 留痕
- 飞书实机验收通过

### P14-D：LLM 操作计划生成

已完成：

- 新增 ecom_watch.action_plan
- 支持异常商品下一步处理计划
- 支持处理顺序计划
- 支持低可信对象处理计划
- 支持重试 + URL 混合处理计划
- 支持 plan_focus=overview / priority / manual_review_first / retry_url_mix
- provider 失败降级为规则计划
- task_steps 留痕
- 飞书实机验收通过

## 四、本轮允许做

允许做：

- 新增 P14 总收口文档
- 总结 P14-A/B/C/D 能力
- 总结新增 intent
- 总结新增环境变量
- 总结 steps 留痕
- 总结飞书验收结果
- 总结安全边界
- 总结未阻塞问题
- 写明后续 P15 OCR 建议入口

## 五、本轮禁止做

禁止做：

- 不改业务代码
- 不改真实 .env
- 不新增 OCR
- 不新增 P15 代码
- 不改 B 项目
- 不重构 P14-A/B/C/D
- 不删除历史文档
- 不编造测试结果
- 不编造飞书实机结果
- 不把真实 .env 加入 git

## 六、收口文档建议结构

docs/p14/p14-closure-summary.md 建议包含：

1. 阶段总览
2. P14 的核心定位
3. P14-A 完成内容
4. P14-B 完成内容
5. P14-C 完成内容
6. P14-D 完成内容
7. 新增 intent 清单
8. 新增环境变量清单
9. task_steps 留痕清单
10. 飞书实机验收摘要
11. 安全边界
12. 未阻塞问题
13. 后续建议：P15 OCR
14. 给下一个 GPT / agent 的交接提醒

## 七、完成后回报格式

完成后必须回报：

A. 是否只做文档  
B. 新增了哪个收口文档  
C. 文档覆盖了哪些 P14 阶段  
D. 是否记录新增 intent  
E. 是否记录新增环境变量  
F. 是否记录 steps 留痕  
G. 是否记录飞书实机验收结论  
H. 是否记录安全边界  
I. 是否记录未阻塞问题  
J. 是否写明 P15 OCR 后续建议  
K. git status --short  
L. 是否允许提交 P14 总收口文档  