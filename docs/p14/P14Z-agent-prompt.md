# P14-Z Agent 约束：P14 LLM 智能增强层总收口文档

## 一、当前唯一任务

当前唯一任务是：

P14-Z：P14 LLM 智能增强层总收口文档

本轮只写文档，不写代码。

## 二、必须先读

开始前必须先读：

1. AGENTS.md 当前阶段入口
2. docs/p14/p14z-project-plan.md
3. docs/p14/P14Z-agent-prompt.md
4. 现有 P14-A / P14-B / P14-C / P14-D 文档
5. 当前 git status

## 三、建议新增文件

新增：

docs/p14/p14-closure-summary.md

## 四、必须覆盖内容

文档必须覆盖：

- P14 总定位
- P14-A：LLM intent fallback
- P14-B：LLM monitor summary
- P14-C：LLM anomaly explanation
- P14-D：LLM action plan
- 新增 intent
- 新增环境变量
- 新增 steps
- 飞书实机验收结论
- 安全边界
- 未阻塞问题
- 后续 P15 OCR 建议

## 五、禁止事项

禁止：

- 不改业务代码
- 不改真实 .env
- 不新增 P15
- 不新增 OCR
- 不删除历史文档
- 不移动 P14-A/B/C/D 文档
- 不编造测试结果
- 不编造飞书实机结果
- 不把真实 .env 加入 git

## 六、写作口径

文档要偏交接和收口，不要写成宣传稿。

重点写：

- 做了什么
- 为什么这样做
- 当前边界是什么
- 验收怎么过的
- 后续怎么接

语气要求：

- 清晰
- 可复现
- 可交接
- 不夸大
- 不承诺系统没有做过的事

## 七、完成后回报格式

A. 是否只做文档  
B. 新增了哪个文件  
C. 文档主要章节  
D. 是否覆盖 P14-A/B/C/D  
E. 是否覆盖 intent / env / steps  
F. 是否覆盖飞书验收与安全边界  
G. 是否有未阻塞问题记录  
H. 是否写明 P15 OCR 下一步  
I. git status --short  
J. 是否允许提交  