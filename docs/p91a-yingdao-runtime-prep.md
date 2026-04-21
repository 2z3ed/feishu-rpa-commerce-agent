# P91a Yingdao Runtime Prep

## 1. 本轮实际检查项

### 目录

- 仓库根目录
- `app/bridge`
- `app/rpa`
- `script`
- `docs`
- `tests`
- `tmp/yingdao_bridge` 约定路径

### 文件

- `app/bridge/yingdao_local_bridge.py`
- `app/rpa/yingdao_runner.py`
- `app/core/config.py`
- `script/p90_mock_yingdao_executor.py`
- `script/p90_yingdao_bridge_rehearsal.py`
- `tests/test_p90_yingdao_bridge_file_flow.py`
- `docs/p83-real-nonprod-facts.md`
- `docs/p83-real-nonprod-closure.md`
- `docs/p91-yingdao-runtime-anchor.md`
- `README.md`

### 命令 / 入口

- `command -v yingdao`
- `command -v 影刀`
- 常见安装目录存在性检查
- 仓库内 `yingdao` 相关文件检索
- 仓库内 `bridge / inbox / outbox / executor` 相关文档检索

## 2. 当前本机结论

当前本机**不具备影刀真执行入口**。

我实际检查到：

- 没有可通过 `command -v yingdao` 或 `command -v 影刀` 直接发现的可执行入口
- 只有仓库内的 bridge / mock executor / runner 文件触发链
- 没有发现可确认的影刀工程文件、导出流程文件或可启动的真执行入口

## 3. 可执行入口 / 不存在原因

### 现状

- **可执行入口：不存在或无法确认**

### 缺失原因

- 没有可调用的影刀二进制 / 命令行入口
- 没有可确认的影刀真执行宿主
- 没有可证实的流程启动命令

## 4. 流程文件 / 项目文件位置

### 现状

- **未发现可确认的影刀工程文件或导出流程文件**

### 说明

当前仓库中只有：

- bridge 文件触发约定
- mock executor
- runner 文件链

但没有可直接作为“影刀真点击工程”的具体项目文件路径可锚定。

## 5. inbox / outbox / evidence 目录映射

- `tmp/yingdao_bridge/inbox`
  - bridge 写入输入 JSON 的目录
  - 也应是执行器轮询读取输入的目录
- `tmp/yingdao_bridge/outbox`
  - 执行器写出结果 JSON 的目录
  - bridge 轮询读取结果的目录
- `evidence_dir`
  - 由输入 JSON 指定
  - 用于截图、日志、回放留痕等证据落盘

## 6. 运行边界

当前运行边界是：

- 主仓库 / runner / bridge 在当前本机环境执行
- 真影刀若存在，通常应在其可执行环境中运行
- 影刀若只支持 Windows，则需要在 Windows 一侧提供运行时与文件触发宿主
- 当前仓库内的 `tmp/yingdao_bridge` 约定只是文件契约，不代表真点击 runtime 已存在

## 7. 是否满足进入 P91b

**不满足。**

因为没有确认到可执行的影刀真入口，因此不能进入 P91b 的真点击成功链。

## 8. 恢复或继续推进需要的条件

恢复 P91b 前至少需要补齐以下之一：

- 可执行的影刀程序路径
- 明确的启动命令
- 明确的影刀工程 / 流程文件路径
- 可把 `inbox` 输入交给影刀执行、并把结果写回 `outbox` 的真实 runtime

## 9. 建议结论

当前应继续暂停 P91 真点击推进，等待 runtime 条件补齐后再进入 P91b。
