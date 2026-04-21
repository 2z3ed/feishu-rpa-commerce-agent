# P91 Yingdao Runtime Anchor

## 1. 本轮实际检查了什么

### 检查目录

- 仓库根目录
- `app/bridge`
- `app/rpa`
- `script`
- `docs`
- `tests`
- 常见本机安装目录与环境路径

### 检查文件

- `app/bridge/yingdao_local_bridge.py`
- 仓库内所有 `*yingdao*` 相关文件
- 仓库内所有 `*.sh` 启动脚本
- `AGENTS.md`
- 与 `yingdao / inbox / outbox / executor / real_nonprod / bridge` 相关的文档与代码线索

### 检查命令 / 入口

- `command -v yingdao`
- `command -v 影刀`
- 常见安装目录存在性检查
- 仓库内 `yingdao` 相关文件检索
- 仓库内脚本入口检索

## 2. 当前结论

**当前本机不具备影刀真执行入口。**

目前仓库中只具备：

- bridge 文件触发链
- mock executor 占位执行链
- runner -> bridge -> inbox/outbox -> runner 的最小闭环

但缺少可调用的影刀真实执行运行时，因此无法继续推进到真点击层。

## 3. 缺少什么

缺少以下至少一项或多项真实能力：

- 可执行的影刀程序或命令行入口
- 可被本机脚本直接触发的影刀运行时
- 可确认的影刀真点击流程工程 / 导出文件 / 启动方式
- 可监听 inbox / 产出 outbox 的真实影刀执行宿主

## 4. 为什么阻断真点击

没有真实执行入口，就无法：

1. 把输入文件交给影刀进程
2. 让影刀真打开 `real_nonprod_page`
3. 让影刀真登录、搜索、提交、核验
4. 让影刀把真执行结果写回 outbox

因此，P91 的“影刀真点击 self-hosted real_nonprod_page”无法在当前本机条件下成立。

## 5. 当前最多只能做到哪一步

当前最多只能做到：

- P90 已完成的文件触发链闭环
- runner / bridge / mock executor 级验证
- 失败样本与 success 样本的契约验证

不能继续到：

- 影刀真点击执行层
- 真页面自动化闭环

## 6. 恢复 P91 的前提条件

恢复 P91 需要先补齐影刀 runtime，可接受的前提至少包括以下一种：

- 本机安装了可执行的影刀程序，并能通过命令行或固定入口启动
- 已存在可被本机脚本调用的影刀执行入口
- 已明确影刀项目 / 流程导出文件以及启动命令
- 已确认可通过文件触发方式驱动影刀读取 inbox 并写回 outbox

## 7. P91 暂停状态

**P91 暂停，等待影刀 runtime / 真执行入口补齐后再恢复。**
