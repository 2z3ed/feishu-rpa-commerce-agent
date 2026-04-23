# P11-B 验收清单

## 一、范围验收

- [x] 只做 discovery/search + discovery/batches/{batch_id}
- [x] 未接 add-from-candidates
- [x] 未做候选编号选择
- [x] 未做 add-by-url 扩展
- [x] 未做 pause / resume / delete
- [x] 未做卡片正式交互
- [x] 未切 PostgreSQL
- [x] 未改 P10 / P11-A 已收口边界

## 一、收口冻结样本

- [x] 成功样本已冻结：`搜索商品：蓝牙耳机` → `TASK-20260423-8089C1`
- [x] 失败样本已冻结：`搜索商品：` → `TASK-20260423-8765A3`
- [x] 空 query 不再走 unknown intent
- [x] 失败路径已去除 “失败解释参考 / RAG失败解释测试” 污染文案

## 二、B 服务验收

- [ ] B 运行在 127.0.0.1:8005
- [ ] POST /internal/discovery/search 可调用
- [ ] GET /internal/discovery/batches/{batch_id} 可调用
- [ ] A 能访问 B
- [ ] 成功 / 失败 Envelope 均可处理

## 三、Envelope 验收

- [ ] A 没有假设裸对象返回
- [ ] A 能处理 ok=true
- [ ] A 能处理 ok=false
- [ ] A 能把失败翻译成老板可读文本

## 四、飞书前台验收

- [ ] 飞书里支持 discovery 搜索命令
- [ ] 成功时飞书能返回候选列表文本
- [ ] 失败时飞书能返回老板可读错误文本
- [ ] 不返回 Python 堆栈
- [ ] 不直接返回原始 JSON

## 五、边界验收

- [ ] A 仍是飞书入口层
- [ ] B 仍是业务服务层
- [ ] 未把 A / B 合并成一个项目
- [ ] 未让 B 长期承担飞书入口角色
- [ ] 未破坏 P10 / P11-A 主线