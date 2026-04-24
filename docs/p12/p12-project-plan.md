# P12-F 开发主线文档

## 阶段名称

P12-F：监控对象删除二次确认版

## 一、阶段背景

P12-A 到 P12-E 已经完成并收口：

- P12-A：搜索结果卡片展示
- P12-B：候选卡片“加入监控”按钮
- P12-C：监控对象管理卡片，支持暂停 / 恢复
- P12-D：超过 5 个监控对象时支持“查看更多”
- P12-E：P12 卡片交互层收口与演示稳定

当前监控对象管理卡片已经能查看、分页、暂停、恢复，但还不能安全删除对象。

删除是高风险动作，不允许像暂停 / 恢复一样点击即执行。

因此 P12-F 只做一件事：

给监控对象增加安全删除能力，且必须经过二次确认。

## 二、本轮唯一目标

只做：

监控对象删除二次确认。

目标链路：

1. 用户发送：

```text
看看当前监控对象
```

2. 系统返回管理卡片
3. 用户点击某个对象的：

```text
删除监控
```

4. 系统返回删除确认卡片
5. 用户点击：

```text
确认删除
```

6. 系统调用 B 的删除能力
7. 删除成功后补发老板可读文本
8. 用户点击：

```text
取消
```

则不删除，并补发“已取消删除”

## 三、当前固定边界

A 项目仍是：

- 飞书入口层
- 消息编排层
- 老板交互层

B 项目仍是：

- 业务服务层
- monitor target 数据与动作提供方

固定原则：

- 不合并 A / B
- A 调 B 继续按 Envelope 解包
- B 默认地址继续为 http://127.0.0.1:8005
- 不把 B 业务逻辑搬进 A
- 不重写 P12-A / B / C / D / E

## 四、本轮第一步：必须锚定 B 删除能力

P12-F 开发前，必须先确认 B 服务是否已有删除能力。

需要检查：

- BServiceClient 是否已有 delete_monitor_target / remove_monitor_target / archive_monitor_target
- B 是否已有类似接口：

```text
DELETE /internal/monitor/{id}
POST /internal/monitor/{id}/delete
POST /internal/monitor/{id}/archive
```

- execute_action 是否已有相关 intent
- 现有监控对象状态是否支持 deleted / archived

如果 B 没有删除能力：

不要硬造 A 侧假删除。

必须先回报：

```text
当前 B 未提供 monitor target 删除能力，P12-F 不能完整落地，只能完成删除确认卡片预留与后移说明。
```

如果 B 已有删除能力：

继续实现完整 P12-F。

## 五、本轮允许做

允许：

1. 在监控对象管理卡片增加“删除监控”按钮
2. 点击删除后返回删除确认卡片
3. 确认卡片展示对象名称、ID、URL、状态、风险提示
4. 确认卡片提供“确认删除”和“取消”按钮
5. “确认删除”后调用 B 的删除能力
6. “取消”后不调用删除能力
7. 成功 / 失败 / 取消均返回老板可读文本
8. 保留 P12-C 暂停 / 恢复
9. 保留 P12-D 查看更多
10. 补最小测试

## 六、本轮禁止做

禁止：

- 不做点击即删除
- 不做批量删除
- 不做批量管理
- 不做搜索过滤
- 不做排序
- 不做 PostgreSQL
- 不做权限系统
- 不做复杂回收站
- 不做多级审批
- 不新增其他业务动作
- 不重写 P12-A / B / C / D / E
- 不破坏暂停 / 恢复
- 不破坏查看更多
- 不破坏候选加入监控

## 七、最小 payload 设计

### 删除入口按钮

```json
{
  "action": "delete_monitor_target_request",
  "target_id": 7,
  "source": "monitor_list_card"
}
```

### 确认删除按钮

```json
{
  "action": "delete_monitor_target_confirm",
  "target_id": 7,
  "source": "delete_confirm_card"
}
```

### 取消按钮

```json
{
  "action": "delete_monitor_target_cancel",
  "target_id": 7,
  "source": "delete_confirm_card"
}
```

字段说明：

- action：动作名，必须严格校验
- target_id：监控对象ID
- source：来源，用于排查

## 八、删除确认卡片要求

确认卡片至少展示：

- 标题：确认删除监控对象
- 对象名称
- 对象ID
- URL
- 当前状态
- 风险提示：

```text
删除后，该对象将不再进入监控列表。
```

按钮：

- 确认删除
- 取消

## 九、建议实现顺序

### P12-F.0：删除能力锚定

先确认 B 是否提供删除能力。

如果没有，停止实现业务删除，只更新文档说明后移。

### P12-F.1：删除入口按钮

在 monitor target 管理卡片中增加“删除监控”。

注意：

- 不允许点击后直接删除
- 只允许弹出 / 发送删除确认卡片

### P12-F.2：删除确认卡片

新增独立 builder，建议位置：

```text
app/services/feishu/cards/monitor_target_delete_confirm.py
```

或放在现有 monitor_targets.py 中，但必须保持结构清楚。

### P12-F.3：确认 / 取消回调

在 card action 中增加：

- delete_monitor_target_confirm
- delete_monitor_target_cancel

确认：

- 调用 B 删除能力
- 返回成功 / 失败文本

取消：

- 不调用 B
- 返回已取消

### P12-F.4：回归

必须回归：

- P12-B 加入监控按钮
- P12-C 暂停 / 恢复
- P12-D 查看更多
- 文本加入监控

## 十、通过标准

P12-F 通过条件：

- 管理卡片出现“删除监控”
- 点击“删除监控”不会直接删除
- 出现删除确认卡片
- 点击“取消”不会删除
- 点击“确认删除”后才删除
- 删除成功后监控对象列表不再出现该对象
- 失败返回老板可读错误
- P12-B 不退化
- P12-C 不退化
- P12-D 不退化
- 不混入批量、搜索过滤、排序、PostgreSQL

## 十一、提交边界

允许提交：

- AGENTS.md
- README.md 增量
- docs/p12 四份约束文件
- 删除确认卡片 builder
- card action 删除确认回调
- BServiceClient 删除方法调用适配
- P12-F 最小测试

禁止提交：

- P12-G 批量管理
- P12-H 搜索过滤 / 排序
- PostgreSQL
- 无关重构
- 临时日志