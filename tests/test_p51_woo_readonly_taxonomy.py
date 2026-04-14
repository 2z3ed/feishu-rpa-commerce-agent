from pathlib import Path

from app.rpa.real_admin_readonly import (
    ERROR_DETAIL_SELECTOR_MISSING,
    ERROR_READBACK_UNSTABLE,
    ERROR_READINESS_NOT_READY,
    run_real_admin_readonly_flow,
)


def _base_kwargs(tmp_path: Path) -> dict:
    return {
        "evidence_dir": tmp_path,
        "evidence_paths": [],
        "sku": "A-001",
        "timeout_ms": 500,
        "requested_target_price": 10.0,
        "requested_current_price": 9.0,
        "verify_mode": "basic",
        "dry_run": False,
        "platform": "woo",
        "read_source": "detail_page",
        "verify_only": True,
    }


def test_p51_readonly_readiness_failure_layer(tmp_path):
    class _Page:
        url = "https://example.test/detail/A001"

        def goto(self, *_args, **_kwargs):
            return None

        def screenshot(self, path: str, full_page: bool):  # noqa: ARG002
            Path(path).write_bytes(b"x")

    out = run_real_admin_readonly_flow(
        page=_Page(),
        readiness_snapshot={"status": "missing_session"},
        **_base_kwargs(tmp_path),
    )
    assert out.success is False
    assert out.error_code == ERROR_READINESS_NOT_READY
    assert out.parsed_result["failure_layer"] == "session_unavailable"
    assert out.result_summary.startswith("[session_unavailable]")
    assert out.error_message.startswith("[session_unavailable]")


def test_p51_readonly_selector_failure_marks_detail_not_loaded(monkeypatch, tmp_path):
    class _Resp:
        status = 200

    class _Locator:
        first = None

        def __init__(self):
            self.first = self

        def is_visible(self):
            return False

        def wait_for(self, **_kwargs):
            raise RuntimeError("selector timeout")

        def inner_text(self, **_kwargs):
            return ""

        def input_value(self, **_kwargs):
            return ""

    class _Page:
        url = "https://example.test/detail/A001"

        def goto(self, *_args, **_kwargs):
            return _Resp()

        def wait_for_load_state(self, *_args, **_kwargs):
            return None

        def wait_for_timeout(self, *_args, **_kwargs):
            return None

        def locator(self, _selector):
            return _Locator()

        def screenshot(self, path: str, full_page: bool):  # noqa: ARG002
            Path(path).write_bytes(b"x")

    import app.rpa.real_admin_readonly as mod

    monkeypatch.setattr(mod.settings, "RPA_REAL_ADMIN_CATALOG_EMPTY_SELECTOR", "#empty")
    monkeypatch.setattr(mod.settings, "RPA_REAL_ADMIN_DETAIL_PRICE_SELECTOR", "#price")

    out = run_real_admin_readonly_flow(
        page=_Page(),
        readiness_snapshot={"status": "ready"},
        **_base_kwargs(tmp_path),
    )
    assert out.success is False
    assert out.error_code == ERROR_DETAIL_SELECTOR_MISSING
    assert out.parsed_result["detail_loaded"] is False
    assert out.parsed_result["failure_layer"] == "detail_not_loaded"
    assert out.error_message.startswith("[detail_not_loaded]")


def test_p51_readonly_readback_inconsistent(monkeypatch, tmp_path):
    class _Resp:
        status = 200

    class _Locator:
        first = None

        def __init__(self, selector: str):
            self.first = self
            self.selector = selector

        def is_visible(self):
            return False

        def wait_for(self, **_kwargs):
            return None

        def inner_text(self, **_kwargs):
            if self.selector == "#price":
                return "N/A"
            if self.selector == "#sku":
                return "A001"
            return ""

        def input_value(self, **_kwargs):
            return ""

    class _Page:
        url = "https://example.test/detail/A001"

        def goto(self, *_args, **_kwargs):
            return _Resp()

        def wait_for_load_state(self, *_args, **_kwargs):
            return None

        def wait_for_timeout(self, *_args, **_kwargs):
            return None

        def locator(self, selector):
            return _Locator(selector)

        def screenshot(self, path: str, full_page: bool):  # noqa: ARG002
            Path(path).write_bytes(b"x")

    import app.rpa.real_admin_readonly as mod

    monkeypatch.setattr(mod.settings, "RPA_REAL_ADMIN_CATALOG_EMPTY_SELECTOR", "#empty")
    monkeypatch.setattr(mod.settings, "RPA_REAL_ADMIN_DETAIL_PRICE_SELECTOR", "#price")
    monkeypatch.setattr(mod.settings, "RPA_REAL_ADMIN_DETAIL_SKU_SELECTOR", "#sku")
    monkeypatch.setattr(mod.settings, "RPA_REAL_ADMIN_DETAIL_STATUS_SELECTOR", "#status")
    monkeypatch.setattr(mod.settings, "RPA_REAL_ADMIN_DETAIL_MESSAGE_SELECTOR", "#msg")
    monkeypatch.setattr(mod.settings, "RPA_REAL_ADMIN_DETAIL_NEW_PRICE_SELECTOR", "#new")
    monkeypatch.setattr(mod.settings, "RPA_REAL_ADMIN_DETAIL_PRODUCT_NAME_SELECTOR", "#name")

    out = run_real_admin_readonly_flow(
        page=_Page(),
        readiness_snapshot={"status": "ready"},
        **_base_kwargs(tmp_path),
    )
    assert out.success is False
    assert out.error_code == ERROR_READBACK_UNSTABLE
    assert out.parsed_result["failure_layer"] == "readback_unstable"
    assert out.error_message.startswith("[readback_unstable]")


def test_p51_readonly_success_fields_stable(monkeypatch, tmp_path):
    class _Resp:
        status = 200

    class _Locator:
        first = None

        def __init__(self, selector: str):
            self.first = self
            self.selector = selector

        def is_visible(self):
            return False

        def wait_for(self, **_kwargs):
            return None

        def inner_text(self, **_kwargs):
            if self.selector == "#price":
                return "59.90"
            if self.selector == "#sku":
                return "A001"
            return ""

        def input_value(self, **_kwargs):
            if self.selector == "#new":
                return "59.90"
            return ""

    class _Page:
        url = "https://example.test/detail/A001"

        def goto(self, *_args, **_kwargs):
            return _Resp()

        def wait_for_load_state(self, *_args, **_kwargs):
            return None

        def wait_for_timeout(self, *_args, **_kwargs):
            return None

        def locator(self, selector):
            return _Locator(selector)

        def screenshot(self, path: str, full_page: bool):  # noqa: ARG002
            Path(path).write_bytes(b"x")

    import app.rpa.real_admin_readonly as mod

    monkeypatch.setattr(mod.settings, "RPA_REAL_ADMIN_CATALOG_EMPTY_SELECTOR", "#empty")
    monkeypatch.setattr(mod.settings, "RPA_REAL_ADMIN_DETAIL_PRICE_SELECTOR", "#price")
    monkeypatch.setattr(mod.settings, "RPA_REAL_ADMIN_DETAIL_SKU_SELECTOR", "#sku")
    monkeypatch.setattr(mod.settings, "RPA_REAL_ADMIN_DETAIL_STATUS_SELECTOR", "")
    monkeypatch.setattr(mod.settings, "RPA_REAL_ADMIN_DETAIL_MESSAGE_SELECTOR", "")
    monkeypatch.setattr(mod.settings, "RPA_REAL_ADMIN_DETAIL_NEW_PRICE_SELECTOR", "#new")
    monkeypatch.setattr(mod.settings, "RPA_REAL_ADMIN_DETAIL_PRODUCT_NAME_SELECTOR", "")

    out = run_real_admin_readonly_flow(
        page=_Page(),
        readiness_snapshot={"status": "ready"},
        **_base_kwargs(tmp_path),
    )
    assert out.success is True
    parsed = out.parsed_result
    assert parsed["page_status"] == "loaded"
    assert parsed["page_message"] == "real_admin_readback_ok"
    assert parsed["detail_loaded"] is True
    assert parsed["target_sku_hit"] is True
    assert parsed["read_source"] == "detail_page"
    assert isinstance(parsed["evidence_count"], int)
    assert parsed["evidence_count"] >= 1
