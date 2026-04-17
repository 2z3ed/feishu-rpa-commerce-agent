#!/usr/bin/env bash
set -euo pipefail
export NONPROD_ADMIN_STUB_PORT="${NONPROD_ADMIN_STUB_PORT:-18081}"
python -m tools.nonprod_admin_stub.app
