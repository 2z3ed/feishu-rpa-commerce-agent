# AGENTS.md

> 本文件是本仓库对编码智能体（如 Codex）的**强约束执行规范**。  
> 本文件中的范围、边界、流程、数据结构、状态机、RAG 策略、飞书交互、安全要求、测试矩阵一旦定义，即视为冻结。  
> 除非用户明确要求修改，否则不得擅自扩展、删减、替换。

---

# 1. 项目定位

## 1.1 项目名称
飞书自然语言驱动的电商后台智能助手

## 1.2 项目目标
本项目是一个**业务可落地的电商后台智能助手**，不是问答机器人，不是研究型 Agent Demo，不是多智能体实验项目。

系统目标：

- 用户在飞书中发送自然语言命令
- 系统将命令解析为结构化任务
- 系统通过 LangGraph 编排主流程
- 系统通过 RAG 检索规则 / FAQ / 历史案例 / 历史任务
- 系统路由到 WooCommerce、Odoo、Chatwoot
- 系统采用 **RPA 主执行 + API 辅助执行**
- 系统将结果通过：
  - 飞书消息
  - 飞书卡片
  - 飞书多维表格
  进行回传与沉淀

## 1.3 项目本质
这是一个**电商后台自动化平台**，目标是替代重复性后台工作，而不是做聊天体验本身。

---

# 2. 范围边界

## 2.1 In Scope（必须实现）
本项目只覆盖以下 4 个岗位：

1. 产品
2. 仓库
3. 客服
4. 财务

并且必须同时实现以下能力：

- 飞书自然语言消息入口
- 飞书消息回执
- 飞书卡片发送
- 飞书卡片交互回调
- 飞书多维表格任务台账
- LangGraph 主编排
- RAG（真实参与业务）
- WooCommerce 接入
- Odoo 接入
- Chatwoot 接入
- RPA 主执行链路
- API 辅助执行链路
- 任务状态机
- 幂等控制
- 重试机制
- 截图 / 附件归档
- README
- 可演示脚本

## 2.2 Out of Scope（禁止扩展）
以下内容一律不做，禁止编码智能体擅自加入：

- 小红书
- 美工 / 抠图 / 图生图 / LoRA
- UI-TARS
- OmniParser
- deepagents
- 多智能体协作
- 审批流
- 支付网关全链路
- 银行流水
- 税务系统
- 发票系统
- 多租户
- K8s / 生产级集群
- 与本项目无关的研究型能力
- V3 规划
- “以后可能要加”的内容先不实现

---

# 3. 固定技术栈

## 3.1 后端
- Python
- FastAPI

## 3.2 编排
- LangGraph
- 禁止使用 deepagents 作为主框架

## 3.3 数据存储
- PostgreSQL（正式）
- SQLite（仅限本地临时兼容，不得作为正式方案）

## 3.4 ORM
- SQLAlchemy

## 3.5 向量库
- Milvus

## 3.6 异步任务
- Celery
- Redis

## 3.7 配置
- `.env`
- `.env.example`

## 3.8 日志
- 结构化日志（JSON 或等价结构）

## 3.9 时区
- Asia/Shanghai

## 3.10 执行原则
- **RPA 是主执行链路**
- **API 是辅助执行链路**
- 至少一个动作必须支持：
  - API 实现
  - RPA 实现
  - API_then_RPA_verify 实现

---

# 4. 平台接入范围

## 4.1 飞书
必须实现：

- 消息事件接收
- 文本回执
- 图片 / 文件回执
- 飞书卡片发送
- 飞书卡片交互回调
- 飞书多维表格写入与更新

## 4.2 WooCommerce
作为主业务平台，必须至少实现：

- 商品查询
- 订单查询
- 改价
- 上架 / 下架
- 商品 / 订单导出

## 4.3 Odoo
作为 ERP / 第二平台，必须至少实现：

- 库存查询
- 产品基础信息查询
- 与 Woo 商品 / 库存对照

## 4.4 Chatwoot
作为客服平台 / 第三平台，必须至少实现：

- 最近会话查询
- 会话摘要查询
- 最近消息查询
- 会话 / 订单联动查询

---

# 5. 四岗位业务动作冻结

---

## 5.1 产品岗

### 5.1.1 固定 intent 列表
- `product.query_sku_status`
- `product.update_price`
- `product.publish_product`
- `product.unpublish_product`
- `product.query_product_profile`
- `product.export_product_list`
- `product.compare_woo_odoo_product`
- `product.batch_update_prices`

### 5.1.2 每个 intent 的 Schema

#### `product.query_sku_status`
必填：
- `sku`

可选：
- `platform`

默认：
- `platform=auto`

#### `product.update_price`
必填：
- `sku`
- `target_price`

可选：
- `currency`
- `platform`
- `reason`

默认：
- `currency=CNY`
- `platform=woo`

#### `product.publish_product`
必填：
- `sku`

可选：
- `platform`

默认：
- `platform=woo`

#### `product.unpublish_product`
必填：
- `sku`

可选：
- `platform`

默认：
- `platform=woo`

#### `product.query_product_profile`
必填：
- `sku`

可选：
- `platform`

默认：
- `platform=auto`

#### `product.export_product_list`
必填：
- `date_from`
- `date_to`

可选：
- `status`
- `platform`

默认：
- `status=all`
- `platform=woo`

#### `product.compare_woo_odoo_product`
必填：
- `sku`

可选：无

默认：无

#### `product.batch_update_prices`
必填：
- `source_table`

可选：
- `platform`

默认：
- `platform=woo`

---

## 5.2 仓库岗

### 5.2.1 固定 intent 列表
- `warehouse.query_pending_orders`
- `warehouse.query_order_status`
- `warehouse.mark_order_processed`
- `warehouse.mark_order_shipped`
- `warehouse.fill_tracking_no`
- `warehouse.query_inventory`
- `warehouse.compare_inventory`
- `warehouse.export_picking_list`

### 5.2.2 每个 intent 的 Schema

#### `warehouse.query_pending_orders`
必填：无

可选：
- `platform`

默认：
- `platform=woo`

#### `warehouse.query_order_status`
必填：
- `order_id`

可选：
- `platform`

默认：
- `platform=woo`

#### `warehouse.mark_order_processed`
必填：
- `order_id`

可选：
- `platform`

默认：
- `platform=woo`

#### `warehouse.mark_order_shipped`
必填：
- `order_id`

可选：
- `platform`

默认：
- `platform=woo`

#### `warehouse.fill_tracking_no`
必填：
- `order_id`
- `tracking_no`

可选：
- `carrier`
- `platform`

默认：
- `platform=woo`

#### `warehouse.query_inventory`
必填：
- `sku`

可选：
- `platform`

默认：
- `platform=odoo`

#### `warehouse.compare_inventory`
必填：
- `sku`

可选：无

默认：无

#### `warehouse.export_picking_list`
必填：
- `date_from`
- `date_to`

可选：
- `platform`

默认：
- `platform=woo`

---

## 5.3 客服岗

### 5.3.1 固定 intent 列表
- `customer.query_order_status`
- `customer.list_recent_conversations`
- `customer.get_conversation_summary`
- `customer.get_last_customer_message`
- `customer.query_refund_policy`
- `customer.query_logistics_status`
- `customer.link_conversation_order`
- `customer.flag_abnormal_conversation`

### 5.3.2 每个 intent 的 Schema

#### `customer.query_order_status`
必填：
- `order_id`

可选：
- `platform`

默认：
- `platform=woo`

#### `customer.list_recent_conversations`
必填：
- `limit`

可选：无

默认：
- `limit=5`

#### `customer.get_conversation_summary`
必填：
- `conversation_id`

可选：无

默认：无

#### `customer.get_last_customer_message`
必填：
- `conversation_id`

可选：无

默认：无

#### `customer.query_refund_policy`
必填：
- `topic`

可选：无

默认：
- `topic=refund`

#### `customer.query_logistics_status`
必填：
- `order_id`

可选：无

默认：无

#### `customer.link_conversation_order`
必填：
- `conversation_id`

可选：
- `order_id`
- `customer_email`
- `customer_phone`

默认：无

#### `customer.flag_abnormal_conversation`
必填：
- `conversation_id`
- `reason`

可选：无

默认：无

---

## 5.4 财务岗

### 5.4.1 固定 intent 列表
- `finance.query_daily_order_summary`
- `finance.query_sales_summary`
- `finance.query_refund_cancel_summary`
- `finance.export_daily_report`
- `finance.reconcile_order_erp`
- `finance.write_report_to_bitable`
- `finance.send_daily_report_card`
- `finance.explain_anomaly`

### 5.4.2 每个 intent 的 Schema

#### `finance.query_daily_order_summary`
必填：
- `date`

可选：无

默认：
- `date=today`

#### `finance.query_sales_summary`
必填：
- `date_from`
- `date_to`

可选：无

默认：无

#### `finance.query_refund_cancel_summary`
必填：
- `date_from`
- `date_to`

可选：无

默认：无

#### `finance.export_daily_report`
必填：
- `date`

可选：
- `format`

默认：
- `format=xlsx`

#### `finance.reconcile_order_erp`
必填：
- `date_from`
- `date_to`

可选：无

默认：无

#### `finance.write_report_to_bitable`
必填：
- `date`

可选：无

默认：
- `date=today`

#### `finance.send_daily_report_card`
必填：
- `date`

可选：无

默认：
- `date=today`

#### `finance.explain_anomaly`
必填：
- `anomaly_id`

可选：无

默认：无

---

# 6. 通用命令解析结构冻结

所有自然语言命令必须统一解析为以下结构：

```json
{
  "role": "product | warehouse | customer | finance",
  "intent": "string",
  "platform": "woo | odoo | chatwoot | auto",
  "execution_mode": "auto | api | rpa | api_then_rpa_verify",
  "confirm_required": true,
  "output_mode": "card | text | file | card+bitable",
  "params": {},
  "raw_text": "string",
  "operator": "string",
  "source": "feishu_message"
}