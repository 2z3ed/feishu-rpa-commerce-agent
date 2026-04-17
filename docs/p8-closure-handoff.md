# P8 Closure Handoff

## 1. P8 主线范围

P8 聚焦 `warehouse.adjust_inventory` 在 `real_nonprod_page` 上的阶段推进：

- P80：锚定
- P81：最小代码接入
- P82：失败语义与证据稳态
- P83：真实非生产总演练与阶段收口

## 2. 最终完成项

- `controlled_page` 人工验证成立
- 自建 `real_nonprod_page` stub 建立
- `real_nonprod_page` facts 入库
- `config / bridge / runner` 接通 readiness 路径
- 最小自动化闭环成立
- P83 总演练与收口完成

## 3. 已验证项

- 登录 / 导航 / 查询 / 调整 / 持久化更新成立
- `session_invalid` 可复现
- `entry_not_ready` 可复现
- `verify_result` 可回查
- SQLite 库存写后可见
- `controlled_page` 未回归
- 主 API 8000 internal sandbox 未受影响

## 4. 关键脚本 / 测试

- `script/p83_real_nonprod_happy_path_rehearsal.py`
- `tests/test_nonprod_admin_stub.py`
- `tests/test_p83_real_nonprod_happy_path_readiness.py`

## 5. 后移尾巴

- 更真实的 UI 自动化层
- 更丰富的失败矩阵
- 更强的演练可视化留痕

## 6. 下一阶段建议起点

如果后续继续推进，建议从以下方向择一开始：

1. 增加更真实的 UI 自动化执行层
2. 扩展更多非生产失败样本
3. 将当前 stub 闭环对接到更接近真实后台的页面结构
