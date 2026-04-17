# P83 前置：controlled_page 基线说明

> 说明：本文件仅记录 **controlled_page** 的已确认事实基线，不代表 real_nonprod_page facts 已到位。  
> 当前结论：controlled_page 事实清楚；真实非生产页面 facts 仍缺失，因此 **P83 仍不能启动正式总演练**。  
> 动作边界：仅 `warehouse.adjust_inventory`。

---

## 1. controlled_page 基线文件

请查看：

- `docs/p83-controlled-page-baseline.md`

该文件只用于受控页面结构对照，**不能**替代 real_nonprod_page 的真实事实。

---

## 2. real_nonprod_page 待确认模板

请查看：

- `docs/real-nonprod-facts-template.md`

该文件用于收集 real_nonprod_page 的真实 facts，不允许用 controlled_page 事实填充。

---

## 3. 当前阻塞

real_nonprod_page 仍缺：

- 正式 URL
- 登录 / 会话维持方式
- 导航入口
- SKU 搜索区稳定定位
- 编辑区稳定定位
- 提交区稳定定位
- 回显区稳定定位

---

## 4. 当前结论

- `controlled_page` 事实已入档到单独的基线文件
- `real_nonprod_page` 仍需补齐真实页面 facts
- P83 正式总演练仍不能启动
