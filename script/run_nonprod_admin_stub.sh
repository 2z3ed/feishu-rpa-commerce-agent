#!/usr/bin/env bash
set -euo pipefail

export NONPROD_ADMIN_STUB_PORT="${NONPROD_ADMIN_STUB_PORT:-18081}"

if [ -x "./venv/bin/python" ]; then
  ./venv/bin/python -m tools.nonprod_admin_stub.app
else
  python3 -m tools.nonprod_admin_stub.app
fi