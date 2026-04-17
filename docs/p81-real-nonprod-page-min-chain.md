# P81 最小真实非生产页面点击链落地

> 阶段定位：P8 主线第二阶段 / P81。  
> 本轮状态：**最小代码接入完成，但当前仅支持结构化 fail-fast。**  
> 动作边界：仅 `warehouse.adjust_inventory`。  
> 绝对边界：不接真实生产，不扩第二动作，不接影刀控制台 / API / Flow，不让飞书直接触发影刀，不重做 `/tasks` / `/steps`，不推翻已收口主线。

---

## 1. 本轮实际做了什么

- bridge 已新增 `real_nonprod_page` 运行分支。
- runner 仍保持原有调用方式，不破坏 `controlled_page`。
- `real_nonprod_page` 在缺失页面事实时，按结构化 fail-fast 返回。
- 新增最小 rehearsal 脚本与测试，用来复验缺配置失败与 controlled page 不回归。

---

## 2. 哪些代码已经正式接入

### 2.1 bridge

- `app/bridge/yingdao_local_bridge.py`
  - 新增 `real_nonprod_page` 分支
  - 新增最小 fail-fast 返回结构
  - 新增标准步骤名的最小输出：
    - `open_entry`
    - `ensure_session`

### 2.2 config

- `app/core/config.py`
  - 增加 real_nonprod_page 的最小配置占位：
    - `YINGDAO_REAL_NONPROD_PAGE_BASE_URL`
    - `YINGDAO_REAL_NONPROD_PAGE_PROFILE`
    - `YINGDAO_REAL_NONPROD_PAGE_TARGET_URL`
    - `YINGDAO_REAL_NONPROD_PAGE_SESSION_PROFILE`

### 2.3 runner

- `app/rpa/yingdao_runner.py`
  - 保持调用契约不变
  - 现在可透传 real_nonprod_page 产生的结构化失败结果

### 2.4 verification assets

- `script/p81_real_nonprod_page_rehearsal.py`
- `tests/test_p81_real_nonprod_page.py`

---

## 3. 当前 real_nonprod_page 已达到哪一步

当前只达到：

**已完成最小代码接入，但仅支持结构化 fail-fast。**

具体来说：

- real_nonprod_page 已正式进入代码运行路径
- 缺配置时不会伪造 happy path
- 失败会带出稳定的 `page_profile / page_steps / page_failure_code / verify_reason`
- 但还没有真实页面点击链 happy path

---

## 4. 最小步骤语义

当前最低限度的步骤语义已经进入代码输出：

- `open_entry`
- `ensure_session`

说明：

- 即使页面事实缺失，也会先记录已经走到哪一步
- 当前因为缺配置，通常会在前两步内 fail-fast
- 后续真实页面事实补齐后，再继续扩展到：
  - `search_sku`
  - `open_editor`
  - `input_inventory`
  - `submit_change`
  - `read_feedback`
  - `verify_result`

---

## 5. fail-fast 语义

当页面事实缺失时，当前代码会稳定返回结构化失败：

- `failure_layer=config`
- `verify_reason=missing_real_nonprod_config` / `session_invalid` / `entry_not_ready`
- `page_failure_code=REAL_NONPROD_CONFIG_MISSING` / `SESSION_INVALID` / `ENTRY_NOT_READY`
- `page_steps` 保留已执行步骤
- `page_evidence_count=0`

这不是生产级失败分类，而是 P81 的最小骨架失败语义。

---

## 6. 当前还缺哪些页面事实

仍然缺：

- 真实页面正式 URL
- 登录 / 会话维持方式
- 导航入口
- SKU 搜索区稳定定位
- 编辑区稳定定位
- 提交区稳定定位
- 回显区稳定定位

这些缺口会阻塞真实 happy path 的到来。

---

## 7. 为什么仍不能伪造 happy path

因为目前还没有正式落库的真实页面事实。

如果现在伪造成功，会带来：

- 样本失真
- 证据失真
- 回归失真
- 后续页面真接入时返工

所以本轮原则是：

**骨架先落，成功不伪造。**

---

## 8. 下一轮什么时候才算能进入 P82

只有在以下最小事实确认后，才算可以进入 P82：

1. 页面 URL 已明确
2. 会话 / 登录方式已明确
3. 导航路径已明确
4. SKU 搜索、编辑、提交、回显区定位已明确
5. real_nonprod_page 至少能走到一个稳定最小 happy path 或稳定的主要失败语义

---

## 9. 本轮明确不做什么

- 不进入 P82
- 不扩第二个动作
- 不切到 `product.update_price`
- 不接真实生产页面
- 不做影刀控制台 / API Key / Flow 接入
- 不让飞书直接触发影刀
- 不大改 ingress / confirm / `/tasks` / `/steps` 主链
- 不伪造真实页面成功样本
- 不破坏 `controlled_page`

---

## 10. 当前结论

**P81 当前已完成最小代码接入，但仅支持结构化 fail-fast；尚未完成真实 happy path。**
