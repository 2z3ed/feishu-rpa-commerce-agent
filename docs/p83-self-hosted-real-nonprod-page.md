# P83 自建 real_nonprod_page 最小后台

> 目标：在本地自建一个独立的 non-production admin stub，作为后续 P8 / real_nonprod_page 的真实目标页。

## 为什么要自建

当前 controlled_page 已证明最小结构链路成立，但它仍然只是受控验证页，不是独立的 real_nonprod_page 目标页。

因此需要一个独立的本地 nonprod 后台，具备：
- 独立端口
- 独立入口
- 独立会话
- 独立导航
- 真实持久化写入

## 服务位置

- 目录：`tools/nonprod_admin_stub/`
- 主文件：`tools/nonprod_admin_stub/app.py`
- 启动脚本：`script/run_nonprod_admin_stub.sh`

## 默认端口

- `127.0.0.1:18081`

## 默认账号

- 用户名：`admin`
- 密码：`admin123`

## 默认样本数据

SQLite 表：`inventory_items`

预置记录：
- `sku=A001`
- `warehouse=MAIN`
- `inventory=100`

## 页面路径

- `GET /login`
- `POST /login`
- `GET /admin`
- `GET /admin/inventory`
- `GET /admin/inventory/adjust?sku=A001`
- `POST /admin/inventory/adjust`

## 已支持的 happy path

1. 打开登录页
2. 登录成功写 session/cookie
3. 进入后台首页
4. 进入库存页并搜索 `A001`
5. 打开调整页
6. 提交库存调整
7. SQLite 中库存真实更新
8. 再次查询能看到新库存

## 已支持的 failure path

- `session_invalid`
  - 未登录访问后台页会显示未登录拦截页
- `entry_not_ready`
  - 通过 `NONPROD_FAIL_MODE=entry_not_ready` 可使库存页显示入口未就绪

## 如何手动验证

1. 启动服务：
   - `bash script/run_nonprod_admin_stub.sh`
2. 打开 `http://127.0.0.1:18081/login`
3. 用 `admin / admin123` 登录
4. 进入 `/admin`
5. 进入 `/admin/inventory?sku=A001`
6. 点击调整并提交
7. 再次查询 `A001`，确认库存已变化

## 结论

这个 stub 是后续 real_nonprod_page 的本地目标页基线，不污染主 API 8000，也不替代 controlled_page。
