#!/usr/bin/env bash

set -euo pipefail

echo "[P12] 开始执行 P12-E 固定回归用例..."

pytest -q tests/test_p10_b_query_integration.py
pytest -q tests/test_p12_b_card_action.py
pytest -q tests/test_p12_c_monitor_card.py
pytest -q tests/test_p12_d_monitor_pagination.py

echo "[P12] 回归用例全部通过。"
