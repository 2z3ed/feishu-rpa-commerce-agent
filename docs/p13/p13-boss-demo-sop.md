# P13-G 老板演示 SOP

## 一、演示目标

P13-G 的演示目标是证明：

系统不仅能抓真实价格，还能告诉老板哪些对象采集成功、哪些对象 fallback、哪些对象失败，以及失败原因。

本轮不是主动通知，不是价格告警，也不是重试系统。

## 二、演示前提

需要启动：

A 项目：

```text
feishu-rpa-commerce-agent
```

B 项目：

```text
Ecom-Watch-Agent-Agent
```

需要确保：

- B 服务运行在 http://127.0.0.1:8005
- A API / worker / 飞书长连接 listener 已启动
- 已有成功样本，如 Hush Home
- 至少有一个 fallback/mock 对象

## 三、演示步骤

### 步骤 1：刷新监控价格

飞书发送：

```text
刷新监控价格
```

预期：

- 刷新成功
- 生成 run_id
- 不因某个 URL 失败拖垮整批

### 步骤 2：查看管理卡片

飞书发送：

```text
看看当前监控对象
```

预期：

成功对象显示：

```text
采集状态：success
来源：html_extract_preview
```

fallback 对象显示：

```text
采集状态：fallback_mock
采集原因：timeout
来源：mock_price
```

### 步骤 3：查看采集失败对象

飞书发送：

```text
查看价格采集失败
```

预期：

返回 fallback / failed 对象列表。

### 步骤 4：查看 mock 价格对象

飞书发送：

```text
查看mock价格对象
```

预期：

返回 price_source=mock_price 或 fallback_mock 对象列表。

### 步骤 5：查看真实价格对象

飞书发送：

```text
查看真实价格对象
```

预期：

返回 price_source=html_extract_preview 或 success 对象列表。

### 步骤 6：查看 run detail

飞书发送：

```text
查看刷新结果 PRR-...
```

预期：

run detail 中也能看到 probe 状态或至少能追踪本次来源。

## 四、失败场景

可选：

1. URL 超时
2. URL 无价格
3. 站点不可访问
4. budget exceeded

预期：

- 不吐堆栈
- 不静默失败
- fallback 或失败原因可见

## 五、回归验证

必须回归：

```text
刷新监控价格
查看价格历史 7
查看刷新结果 PRR-...
看看当前监控对象
查看更多
```

P12：

- 加入监控
- 暂停 / 恢复
- 删除确认

## 六、验收记录模板

```text
P13-G 实机验收记录

时间：
A commit：
B commit：

1. 刷新监控价格：
结果：通过 / 未通过

2. 管理卡片展示采集状态：
结果：通过 / 未通过

3. 查看价格采集失败：
结果：通过 / 未通过

4. 查看mock价格对象：
结果：通过 / 未通过

5. 查看真实价格对象：
结果：通过 / 未通过

6. run detail 采集状态：
结果：通过 / 未通过

7. P12/P13 回归：
结果：通过 / 未通过

最终结论：
P13-G 是否通过：
```