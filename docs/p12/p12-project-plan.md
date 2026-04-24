# P12-D 开发主线文档

## 阶段名称

P12-D：监控对象分页 / 查看更多版

## 一、阶段背景

P12-C 已完成监控对象管理卡片：

- “看看当前监控对象”优先返回飞书卡片
- 卡片展示对象名称、ID、状态、URL
- active / inactive 支持暂停 / 恢复按钮
- 卡片失败 fallback 文本

但 P12-C 明确只展示前 5 条。

当监控对象超过 5 个时，老板目前无法在卡片中继续查看第 6 条以后的对象。

所以 P12-D 只解决一个问题：

超过 5 个监控对象后，如何继续查看。

## 二、本轮唯一目标

只做：

监控对象管理卡片的“查看更多 / 下一页”。

目标链路：

1. 用户发送：看看当前监控对象
2. 系统返回第 1 页管理卡片
3. 如果总数超过 5 条，卡片底部出现“查看更多”
4. 用户点击“查看更多”
5. 系统返回第 2 页管理卡片
6. 第 2 页继续展示对象名称、ID、状态、URL
7. 暂停 / 恢复按钮仍可用

## 三、当前固定边界

A 项目仍是：

- 飞书入口层
- 消息编排层
- 老板交互层

B 项目仍是：

- 业务服务层
- monitor target 数据提供方

固定原则：

- 不合并 A / B
- A 调 B 继续按 Envelope 解包
- B 默认地址继续为 http://127.0.0.1:8005
- 不把 B 业务逻辑搬进 A
- 不重写 P12-A / P12-B / P12-C

## 四、本轮允许做

允许：

1. 管理卡片支持 page / offset / limit
2. 默认展示第 1 页，每页 5 条
3. 超过 5 条时显示“查看更多”按钮
4. 点击查看更多后返回下一页卡片
5. 下一页继续保留暂停 / 恢复按钮
6. 没有更多数据时给出老板可读提示
7. 卡片失败时 fallback 文本
8. 补最小测试

## 五、本轮禁止做

禁止：

- 不做删除按钮
- 不做批量暂停 / 批量恢复
- 不做搜索过滤
- 不做排序规则
- 不做复杂分页状态系统
- 不做 PostgreSQL 切换
- 不新增业务动作
- 不重写 monitor list 主链
- 不破坏 P12-B 候选按钮
- 不破坏 P12-C 暂停 / 恢复按钮

## 六、最小 payload 设计

查看更多按钮：

```json
{
  "action": "monitor_targets_next_page",
  "page": 2,
  "limit": 5,
  "source": "monitor_list_card"
}
```

字段说明：

- action：固定为 monitor_targets_next_page
- page：下一页页码，从 1 开始
- limit：每页条数，默认 5
- source：来源标识

## 七、建议实现顺序

### P12-D.0：锚定 P12-C 管理卡片

先确认：

- monitor_targets.py 当前 builder 的输入结构
- longconn.py 当前 pause / resume 回调逻辑
- ingress_tasks.py 当前 monitor.targets 成功卡片发送逻辑
- BServiceClient.get_monitor_targets() 当前返回是否包含完整列表

### P12-D.1：卡片 builder 支持分页参数

让 monitor_targets card builder 支持：

- page
- limit
- total
- has_next
- start_index
- end_index

默认：

```text
page = 1
limit = 5
```

### P12-D.2：第一页展示“查看更多”

当 total > page * limit 时，卡片底部出现：

```text
查看更多
```

点击后触发：

```json
{
  "action": "monitor_targets_next_page",
  "page": 2,
  "limit": 5,
  "source": "monitor_list_card"
}
```

### P12-D.3：回调返回下一页

点击“查看更多”后：

- A 重新调用 B 获取 monitor targets
- 按 page / limit 切片
- 返回下一页管理卡片
- 保留每个对象暂停 / 恢复按钮

优先补发新卡片或文本均可，但建议补发新卡片。

### P12-D.4：边界处理

必须处理：

- page 非法
- limit 非法
- 没有更多数据
- B 服务失败
- 卡片发送失败 fallback 文本

## 八、通过标准

P12-D 通过条件：

- 监控对象超过 5 个时出现“查看更多”
- 点击后能看到第 6 条以后的对象
- 下一页仍保留暂停 / 恢复按钮
- 没有更多数据时提示清楚
- P12-A 搜索卡片不退化
- P12-B 加入监控按钮不退化
- P12-C 管理卡片不退化
- 不混入删除、批量、搜索过滤、PostgreSQL

## 九、提交边界

允许提交：

- AGENTS.md
- README.md 增量
- docs/p12 四份约束文件
- monitor card builder 分页增强
- card action next page 回调
- P12-D 最小测试

禁止提交：

- P12-E 内容
- 删除按钮
- 批量操作
- 搜索过滤
- 无关重构
- 临时日志