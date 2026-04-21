from app.bridge import yingdao_local_bridge as bridge_mod


def test_real_nonprod_page_fail_fast_missing_config(monkeypatch):
    old_mode = bridge_mod.settings.YINGDAO_BRIDGE_EXECUTION_MODE
    old_target = bridge_mod.settings.YINGDAO_REAL_NONPROD_PAGE_TARGET_URL
    old_session = bridge_mod.settings.YINGDAO_REAL_NONPROD_PAGE_SESSION_PROFILE
    old_base = bridge_mod.settings.YINGDAO_REAL_NONPROD_PAGE_BASE_URL
    old_profile = bridge_mod.settings.YINGDAO_REAL_NONPROD_PAGE_PROFILE
    bridge_mod.settings.YINGDAO_BRIDGE_EXECUTION_MODE = "real_nonprod_page"
    bridge_mod.settings.YINGDAO_REAL_NONPROD_PAGE_TARGET_URL = ""
    bridge_mod.settings.YINGDAO_REAL_NONPROD_PAGE_SESSION_PROFILE = ""
    bridge_mod.settings.YINGDAO_REAL_NONPROD_PAGE_BASE_URL = ""
    bridge_mod.settings.YINGDAO_REAL_NONPROD_PAGE_PROFILE = "real_nonprod_page"
    try:
        out = bridge_mod.run_bridge_job(
            {
                "task_id": "TASK-P81-MISS",
                "confirm_task_id": "TASK-P81-CFM-MISS",
                "provider_id": "odoo",
                "capability": "warehouse.adjust_inventory",
                "sku": "A001",
                "delta": 5,
                "old_inventory": 100,
                "target_inventory": 105,
                "page_profile": "real_nonprod_page",
                "target_url": "",
                "session_profile": "",
            }
        )
        assert out["failure_layer"] == "config"
        assert out["verify_reason"] == "missing_real_nonprod_config"
        assert out["page_failure_code"] == "REAL_NONPROD_CONFIG_MISSING"
        assert out["page_steps"] == ["open_entry"]
        assert out["page_profile"] == "real_nonprod_page"
    finally:
        bridge_mod.settings.YINGDAO_BRIDGE_EXECUTION_MODE = old_mode
        bridge_mod.settings.YINGDAO_REAL_NONPROD_PAGE_TARGET_URL = old_target
        bridge_mod.settings.YINGDAO_REAL_NONPROD_PAGE_SESSION_PROFILE = old_session
        bridge_mod.settings.YINGDAO_REAL_NONPROD_PAGE_BASE_URL = old_base
        bridge_mod.settings.YINGDAO_REAL_NONPROD_PAGE_PROFILE = old_profile


def test_controlled_page_still_works(monkeypatch):
    old_mode = bridge_mod.settings.YINGDAO_BRIDGE_EXECUTION_MODE
    bridge_mod.settings.YINGDAO_BRIDGE_EXECUTION_MODE = "controlled_page"

    class _Resp:
        def __init__(self, body: bytes):
            self._body = body

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return self._body

    def _urlopen(req, timeout=30):  # noqa: ARG001
        url = req.full_url
        if "inventory/adjust?" in url:
            return _Resp(b'{"provider":"odoo","payload":{"qty_after":105}}')
        return _Resp(b"<html>ok</html>")

    monkeypatch.setattr(bridge_mod, "urlopen", _urlopen)
    try:
        out = bridge_mod.run_bridge_job(
            {
                "task_id": "TASK-P81-CTRL",
                "confirm_task_id": "TASK-P81-CFM-CTRL",
                "provider_id": "odoo",
                "capability": "warehouse.adjust_inventory",
                "sku": "A001",
                "delta": 5,
                "old_inventory": 100,
                "target_inventory": 105,
                "page_profile": "internal_inventory_admin_like_v1",
            }
        )
    finally:
        bridge_mod.settings.YINGDAO_BRIDGE_EXECUTION_MODE = old_mode
    assert out["page_profile"] == "internal_inventory_admin_like_v1"
    assert out["operation_result"] in {"write_adjust_inventory", "write_adjust_inventory_verify_failed"}
