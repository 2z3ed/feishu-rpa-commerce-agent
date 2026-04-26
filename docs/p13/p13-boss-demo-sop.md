# P13-F 老板演示 SOP

## 一、演示目标

P13-F 的演示目标是证明：

系统不再只能使用 mock_price，而是可以从真实商品页面中提取价格，并写入监控对象。

本轮不是复杂爬虫，不是反爬，不是代理池。

本轮只演示：

```text
商品 URL
→ HTML 页面
→ 提取价格
→ 写入 current_price
→ price_source=html_extract_preview
```

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
- 已有 Hush Home 监控对象或可重新加入
- P13-A 到 P13-E 能力已回归通过

## 三、演示样本

样本：

```text
Hush Home® 深眠重力被
URL：https://www.hushhome.com/tw/products/weighted-blanket
页面价格示例：HK$1,280.00
```

期望：

```text
当前价格：1280.0
来源：html_extract_preview
```

## 四、演示步骤

### 步骤 1：确认对象在监控列表中

飞书发送：

```text
看看当前监控对象
```

确认 Hush Home 对象存在。

如不存在，先搜索并加入监控。

### 步骤 2：刷新监控价格

飞书发送：

```text
刷新监控价格
```

预期：

- 刷新成功
- 生成 run_id
- 不报错

### 步骤 3：查看管理卡片

飞书发送：

```text
看看当前监控对象
```

找到 Hush Home 对象。

预期：

```text
当前价格：1280.0
来源：html_extract_preview
```

如果提取失败：

- 不能报堆栈
- 允许 fallback 到 mock_price
- 需要在日志或结果中可确认失败原因

### 步骤 4：查看价格历史

飞书发送：

```text
查看价格历史 <对象ID>
```

预期：

- 价格历史中可看到本次刷新记录
- 来源为 html_extract_preview 或 fallback 来源

### 步骤 5：查看刷新 run

飞书发送：

```text
查看刷新结果 <run_id>
```

预期：

- run detail 可查
- item 中价格来源可追踪

## 五、回归验证

必须回归：

```text
刷新监控价格
查看价格历史 7
查看刷新结果 PRR-...
看看当前监控对象
查看更多
```

P12 交互：

- 加入监控
- 暂停 / 恢复
- 删除确认

## 六、失败场景

可选：

1. URL 无法访问
2. HTML 中没有价格
3. 请求超时
4. 返回非 HTML

预期：

- 不影响整轮刷新任务
- fallback 可用
- 不吐堆栈
- 不静默失败

## 七、验收记录模板

```text
P13-F 实机验收记录

时间：
A commit：
B commit：
样本 URL：

1. Hush Home 是否在监控对象中：
结果：通过 / 未通过

2. 刷新监控价格：
结果：通过 / 未通过
run_id：

3. 是否提取真实价格：
结果：通过 / 未通过
current_price：
price_source：

4. 价格历史是否记录：
结果：通过 / 未通过

5. run detail 是否可追踪：
结果：通过 / 未通过

6. fallback 是否稳定：
结果：通过 / 未通过

7. P12/P13 回归：
结果：通过 / 未通过

最终结论：
P13-F 是否通过：
```