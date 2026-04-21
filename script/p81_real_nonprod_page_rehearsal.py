#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from app.bridge import yingdao_local_bridge as bridge_mod


def main() -> int:
    parser = argparse.ArgumentParser(description="P8.1 real_nonprod_page rehearsal")
    parser.add_argument("--mode", choices=("missing_config", "controlled_page"), default="missing_config")
    args = parser.parse_args()

    old_mode = bridge_mod.settings.YINGDAO_BRIDGE_EXECUTION_MODE
    old_target = bridge_mod.settings.YINGDAO_REAL_NONPROD_PAGE_TARGET_URL
    old_session = bridge_mod.settings.YINGDAO_REAL_NONPROD_PAGE_SESSION_PROFILE
    old_base = bridge_mod.settings.YINGDAO_REAL_NONPROD_PAGE_BASE_URL
    try:
        if args.mode == "missing_config":
            bridge_mod.settings.YINGDAO_BRIDGE_EXECUTION_MODE = "real_nonprod_page"
            bridge_mod.settings.YINGDAO_REAL_NONPROD_PAGE_TARGET_URL = ""
            bridge_mod.settings.YINGDAO_REAL_NONPROD_PAGE_SESSION_PROFILE = ""
            bridge_mod.settings.YINGDAO_REAL_NONPROD_PAGE_BASE_URL = ""
            out = bridge_mod.run_bridge_job(
                {
                    "task_id": "TASK-P81-REHEARSAL-MISS",
                    "confirm_task_id": "TASK-P81-REHEARSAL-MISS-CFM",
                    "provider_id": "odoo",
                    "capability": "warehouse.adjust_inventory",
                    "sku": "A001",
                    "delta": 5,
                    "old_inventory": 100,
                    "target_inventory": 105,
                    "page_profile": "real_nonprod_page",
                }
            )
        else:
            bridge_mod.settings.YINGDAO_BRIDGE_EXECUTION_MODE = "controlled_page"
            out = bridge_mod.run_bridge_job(
                {
                    "task_id": "TASK-P81-REHEARSAL-CTRL",
                    "confirm_task_id": "TASK-P81-REHEARSAL-CTRL-CFM",
                    "provider_id": "odoo",
                    "capability": "warehouse.adjust_inventory",
                    "sku": "A001",
                    "delta": 5,
                    "old_inventory": 100,
                    "target_inventory": 105,
                    "page_profile": "internal_inventory_admin_like_v1",
                }
            )
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    finally:
        bridge_mod.settings.YINGDAO_BRIDGE_EXECUTION_MODE = old_mode
        bridge_mod.settings.YINGDAO_REAL_NONPROD_PAGE_TARGET_URL = old_target
        bridge_mod.settings.YINGDAO_REAL_NONPROD_PAGE_SESSION_PROFILE = old_session
        bridge_mod.settings.YINGDAO_REAL_NONPROD_PAGE_BASE_URL = old_base


if __name__ == "__main__":
    raise SystemExit(main())
