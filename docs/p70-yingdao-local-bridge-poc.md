# 影刀本地桥接 PoC（第二轮）：最小稳态

> 范围：仅 `warehouse.adjust_inventory`。  
> 前提：无影刀控制台权限；影刀仅作为本机执行器；smoke harness 已通过。  
> 目标：主系统 -> 本地 HTTP bridge -> 影刀本地执行 -> 回写 `/tasks` 与 `/steps` 证据面。

## 1) Bridge 输入/输出契约

### 输入（`POST /run`）

- `task_id`
- `confirm_task_id`
- `provider_id`
- `capability`
- `sku`
- `delta`
- `old_inventory`
- `target_inventory`
- `environment`
- `force_verify_fail`（可选）

### 输出（统一 JSON）

- `task_id`
- `confirm_task_id`
- `provider_id`
- `capability`
- `rpa_vendor`（固定 `yingdao`）
- `operation_result`
- `verify_passed`
- `verify_reason`
- `failure_layer`
- `status`（`done` / `failed`）
- `raw_result_path`
- `evidence_paths`（当前可最小占位）

## 2) 本地 bridge 服务

实现文件：`app/bridge/yingdao_local_bridge.py`

接口：

- `GET /health`
- `POST /run`

运行：

```bash
python -m app.bridge.yingdao_local_bridge
```

默认监听：`127.0.0.1:17891`

Bridge 行为：

1. `/run` 接收主系统请求
2. 写入输入文件到 `YINGDAO_BRIDGE_INPUT_DIR`（默认 `tmp/yingdao_bridge/inbox`）
3. 等待结果文件（默认 `tmp/yingdao_bridge/outbox/{task_id}.done.json|failed.json`）
4. 解析结果并返回统一 JSON

## 3) 主系统接入点

- Runner：`app/rpa/yingdao_runner.py`（主系统只调 bridge，不直接依赖影刀）
- Confirm 写链接入：`app/graph/nodes/execute_action.py`

开关配置：

- `ODOO_ADJUST_INVENTORY_CONFIRM_EXECUTION_BACKEND=internal_sandbox|yingdao_bridge`  
  - 默认 `internal_sandbox`（保持原链路行为）
  - 设为 `yingdao_bridge` 时，confirm 放行后调用本地 bridge

## 4) 回写证据面

桥接结果在 `parsed_result` 中写入并透传到 `action_executed.detail`，至少包含：

- `rpa_vendor=yingdao`
- `operation_result`
- `verify_passed`
- `verify_reason`
- `failure_layer`
- `confirm_task_id / target_task_id`
- `raw_result_path`
- `evidence_paths_count`

## 5) 手动最小联调

1. 启 bridge：

```bash
python -m app.bridge.yingdao_local_bridge
```

2. 配置主系统使用 bridge：

```bash
export ODOO_ADJUST_INVENTORY_CONFIRM_EXECUTION_BACKEND=yingdao_bridge
export YINGDAO_BRIDGE_BASE_URL=http://127.0.0.1:17891
```

3. 触发 `warehouse.adjust_inventory` + confirm 流程
4. 在 `/tasks/{confirm_task_id}/steps` 查看 `action_executed.detail` 是否包含上述桥接字段

## 6) 失败分类与超时口径（第二轮补充）

### 6.1 Runner 侧（主系统调用 bridge）

- `bridge_unreachable`：bridge 服务不可达
- `bridge_timeout`：调用 `/run` 请求超时
- `bridge_http_error`：bridge 返回 HTTP 5xx
- `bridge_result_invalid_json`：bridge 响应 JSON 非法
- `bridge_result_invalid_shape`：bridge 响应不是对象
- `bridge_result_missing_fields`：bridge 响应缺关键字段

对应 operation_result 口径：

- `write_adjust_inventory_bridge_unreachable`
- `write_adjust_inventory_bridge_timeout`
- `write_adjust_inventory_bridge_failed`
- `write_adjust_inventory_bridge_invalid_result`

### 6.2 Bridge 侧（文件交换执行）

- `bridge_input_write_failed`：输入文件写入失败
- `bridge_result_timeout`：结果文件未在超时内出现
- `bridge_result_invalid_json`：结果文件 JSON 非法
- `bridge_result_invalid_shape`：结果文件不是对象
- `bridge_result_missing_fields`：结果文件缺关键字段

## 7) 超时排查顺序

1. `GET /health` 先确认 bridge 进程在线
2. 检查 `YINGDAO_BRIDGE_INPUT_DIR` 是否写入了 `{task_id}.input.json`
3. 检查 `YINGDAO_BRIDGE_OUTPUT_DIR` 是否产出了 `{task_id}.done.json|failed.json`
4. 对照 `YINGDAO_BRIDGE_WAIT_TIMEOUT_S` 与 `YINGDAO_BRIDGE_POLL_INTERVAL_MS`
5. 在主系统 `/tasks/{confirm_task_id}/steps` 查看 `failure_layer/verify_reason/raw_result_path`

## 8) 可重复手动演练入口

新增脚本：`script/p70_yingdao_bridge_rehearsal.py`

运行示例：

```bash
python script/p70_yingdao_bridge_rehearsal.py \
  --base-url http://127.0.0.1:17891 \
  --task-id TASK-P70-REHEARSAL-1 \
  --confirm-task-id TASK-P70-REHEARSAL-CFM-1
```

强制核验失败样本：

```bash
python script/p70_yingdao_bridge_rehearsal.py --force-verify-fail
```

脚本输出最小核查字段：

- `task_id / confirm_task_id`
- `operation_result / verify_passed / verify_reason / failure_layer`
- `raw_result_path / evidence_paths`

## 9) 边界声明

- 这是本地桥接 PoC 骨架，不是生产接入方案。
- 不涉及影刀控制台/API Key/Flow 权限。
- 不扩第二个动作，不改 Woo 主线，不改 P6.1/P6.2 治理口径。
