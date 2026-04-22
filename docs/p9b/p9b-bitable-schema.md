
---

# 文件 2：`RPA执行证据台账-字段冻结版.md`

```md
# RPA执行证据台账 字段冻结版

## 一、设计目标

这张表不是数据库真相源，而是飞书多维表里的业务台账。
它的用途是：

- 给业务/运营/管理侧查看 RPA 执行结果
- 做筛选、追踪、复盘
- 辅助任务协同
- 不承担最终审计真相源职责

真相源仍然是主系统数据库中的：

- task_records
- task_steps
- action_executed.detail

---

## 八、当前非阻塞事实（P9-B 边界冻结）

### 1) bitable_write_failed 根因（非阻塞）

当前仓库在写入飞书多维表时出现过：

- `bitable_write_failed`
- 报错：`No module named 'lark_oapi.api'`

结论：

- **根因是缺少 `lark_oapi` 依赖**
- 这是**非阻塞问题**，不影响 P9-B “主系统留痕闭环（SQLite + /api/v1/tasks* 可查）”成立

边界冻结：

- 当前仍以 **数据库（SQLite）+ `/api/v1/tasks*`** 为真相源
- 飞书多维表写入保持后移或可选增强项（不作为本轮验收依赖）

---

## 二、推荐表名

**RPA执行证据台账**

如果你想更偏业务口径，也可以叫：

- RPA执行留痕台账
- RPA执行结果台账
- RPA证据台账

推荐还是统一用：

**RPA执行证据台账**

---

## 三、写入策略

当前固定策略：

- 只由主系统写入
- ShadowBot 不直接写表
- 每次 RPA 执行完成后 append 一行
- success/failure 都可各写一行
- 当前阶段先优先支持 success 追加

---

## 四、字段冻结清单

### A. 主键/关联字段

#### 1. 台账类型
- 类型：单选
- 示例值：
  - `rpa_runtime_success`
  - `rpa_runtime_failed`

#### 2. task_id
- 类型：单行文本
- 说明：当前任务 ID

#### 3. target_task_id
- 类型：单行文本
- 说明：如果是 confirm 子任务，关联原始任务 ID；没有就留空

#### 4. run_id
- 类型：单行文本
- 说明：本轮影刀 runtime 的唯一执行 ID

---

### B. 执行上下文字段

#### 5. provider_id
- 类型：单选
- 示例值：
  - `yingdao_local`

#### 6. capability
- 类型：单选
- 示例值：
  - `warehouse.adjust_inventory`

#### 7. execution_mode
- 类型：单选
- 示例值：
  - `rpa`

#### 8. runtime_state
- 类型：单选
- 示例值：
  - `done`
  - `failed`

#### 9. operation_result
- 类型：单行文本
- 示例值：
  - `write_adjust_inventory`
  - `write_adjust_inventory_verify_failed`

---

### C. 结果判断字段

#### 10. verify_passed
- 类型：复选框
- 说明：写后核验是否通过

#### 11. verify_reason
- 类型：单行文本
- 示例值：
  - `post_inventory_matches_target`
  - `post_inventory_mismatch`

#### 12. page_failure_code
- 类型：单行文本
- 示例值：
  - `VERIFY_FAIL`
  - `SKU_MISSING`
  - `ENTRY_NOT_READY`

#### 13. failure_layer
- 类型：单选
- 示例值：
  - `page`
  - `verify_failed`
  - `bridge_result_timeout`

---

### D. 页面执行字段

#### 14. page_steps
- 类型：多行文本
- 说明：页面执行步骤，建议逗号拼接保存
- 示例值：
  - `open_entry,ensure_session,search_sku,open_editor,input_inventory,submit_change,read_feedback,verify_result`

#### 15. page_evidence_count
- 类型：数字
- 说明：证据文件数量

#### 16. screenshot_paths
- 类型：多行文本
- 说明：证据文件路径列表；当前阶段可以先保存为一行 JSON 字符串或换行分隔文本

---

### E. 业务值字段

#### 17. sku
- 类型：单行文本
- 说明：执行对象 SKU

#### 18. old_inventory
- 类型：数字
- 说明：写前库存

#### 19. new_inventory
- 类型：数字
- 说明：写后库存

#### 20. target_inventory
- 类型：数字
- 说明：目标库存

---

### F. 结果展示字段

#### 21. result_summary
- 类型：多行文本
- 说明：给业务侧看的摘要
- 示例：
  - `A001 库存已从 100 调整到 105，RPA 执行成功，核验通过`
  - `A001 库存调整失败，页面核验未通过`

#### 22. latest_evidence_path
- 类型：单行文本
- 说明：最新证据文件路径

---

### G. 时间字段

#### 23. created_at
- 类型：日期时间
- 说明：本条台账创建时间

#### 24. finished_at
- 类型：日期时间
- 说明：本轮执行完成时间

---

## 五、建议的最小字段集

如果你想先做最小可用版，最少先上这 12 个：

1. 台账类型
2. task_id
3. run_id
4. provider_id
5. capability
6. runtime_state
7. verify_passed
8. verify_reason
9. old_inventory
10. new_inventory
11. page_evidence_count
12. created_at

---

## 六、推荐最终字段顺序

建议你在多维表里按这个顺序排：

1. 台账类型  
2. task_id  
3. target_task_id  
4. run_id  
5. provider_id  
6. capability  
7. execution_mode  
8. runtime_state  
9. operation_result  
10. sku  
11. old_inventory  
12. target_inventory  
13. new_inventory  
14. verify_passed  
15. verify_reason  
16. page_failure_code  
17. failure_layer  
18. page_steps  
19. page_evidence_count  
20. screenshot_paths  
21. latest_evidence_path  
22. result_summary  
23. created_at  
24. finished_at  

---

## 七、当前阶段注意事项

1. 当前这张表只做业务台账，不做真相源
2. 当前 success 主链优先，failure 可以后移
3. 当前 screenshot_paths 允许先保存 runtime-result.json 兜底路径
4. 当前不要让 ShadowBot 直接写这张表
5. 一定要由主系统在接住 `done/outbox` 之后再写入