from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from app.rpa.real_admin_readonly import (
    ERROR_DETAIL_POST_SAVE_PRICE_MISMATCH,
    ERROR_DETAIL_POST_SAVE_READBACK_MISSING,
    ERROR_DETAIL_SAVE_RESULT_ERROR,
    ERROR_DETAIL_SAVE_RESULT_TIMEOUT,
    ERROR_DETAIL_SUBMIT_NO_EFFECT,
    run_real_admin_update_price_flow,
)


class _Resp:
    def __init__(self, status: int = 200):
        self.status = status


def _mk_loc(
    *,
    visible: bool = True,
    enabled: bool = True,
    text: str = "",
    attr: dict[str, str] | None = None,
):
    loc = MagicMock()
    loc.first = loc
    loc.wait_for = MagicMock(return_value=None if visible else RuntimeError("hidden"))
    loc.is_visible = MagicMock(return_value=visible)
    loc.is_enabled = MagicMock(return_value=enabled)
    loc.inner_text = MagicMock(return_value=text)
    loc.input_value = MagicMock(return_value=text)
    loc.fill = MagicMock(return_value=None)
    loc.click = MagicMock(return_value=None)
    loc.get_attribute = MagicMock(side_effect=lambda k: (attr or {}).get(k, ""))
    return loc


def _mk_page(*, after_price_text: str, save_status: str, save_text: str = "ok", price_selector: str = "#price"):
    page = MagicMock()
    page.goto = MagicMock(return_value=_Resp(200))
    page.wait_for_timeout = MagicMock()
    page.url = "https://example.test/detail/A001"
    page.screenshot = MagicMock(return_value=None)

    empty_loc = _mk_loc(visible=False)
    before_price_loc = _mk_loc(text="59.90")
    after_price_loc = _mk_loc(text=after_price_text)
    new_price_input_loc = _mk_loc()
    save_btn_loc = _mk_loc()
    save_result_loc = _mk_loc(visible=True, text=save_text, attr={"data-status": save_status})

    def locator(sel: str):
        if sel == "#empty":
            return empty_loc
        if sel == price_selector:
            # first readback uses same selector; return before then after
            if not hasattr(locator, "_called_price"):
                locator._called_price = 0
            locator._called_price += 1
            return before_price_loc if locator._called_price == 1 else after_price_loc
        if sel == "#new":
            return new_price_input_loc
        if sel == "#save":
            return save_btn_loc
        if sel == "#save-result":
            return save_result_loc
        return _mk_loc()

    page.locator = MagicMock(side_effect=locator)
    return page


def _base_settings(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_BASE_URL", "https://example.test")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_HOME_PATH", "/h")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_CATALOG_PATH", "/c")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_DETAIL_PATH_TEMPLATE", "/d/{sku}")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_SKU_SEARCH_PARAM", "sku")

    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_CATALOG_EMPTY_SELECTOR", "#empty")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_DETAIL_PRICE_SELECTOR", "#price")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_DETAIL_NEW_PRICE_SELECTOR", "#new")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_DETAIL_SAVE_BUTTON_SELECTOR", "#save")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_DETAIL_SAVE_RESULT_SELECTOR", "#save-result")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_PRICE_COMPARE_TOLERANCE", 0.009)


def test_write_flow_success_requires_readback_and_match(monkeypatch, tmp_path):
    _base_settings(monkeypatch)
    page = _mk_page(after_price_text="39.90", save_status="success", save_text="saved")
    out = run_real_admin_update_price_flow(
        page=page,
        evidence_dir=Path(tmp_path),
        evidence_paths=[],
        task_id="TASK-X",
        sku="A001",
        readiness_snapshot={"ready": True},
        timeout_ms=5000,
        requested_target_price=39.9,
        requested_current_price=59.9,
        verify_mode="basic",
        dry_run=False,
        platform="woo",
        read_source="browser_real",
    )
    assert out.success is True
    pr = out.parsed_result
    assert pr["submit_attempted"] is True
    assert pr["submit_result"] == "success"
    assert pr["page_current_price_after_save"] is not None
    assert pr["verify_passed"] is True
    assert pr["verify_reason"] == "ok"


def test_write_flow_post_save_price_mismatch_is_failure(monkeypatch, tmp_path):
    _base_settings(monkeypatch)
    page = _mk_page(after_price_text="66.60", save_status="success", save_text="saved")
    out = run_real_admin_update_price_flow(
        page=page,
        evidence_dir=Path(tmp_path),
        evidence_paths=[],
        task_id="TASK-X",
        sku="A001",
        readiness_snapshot={"ready": True},
        timeout_ms=5000,
        requested_target_price=39.9,
        requested_current_price=59.9,
        verify_mode="basic",
        dry_run=False,
        platform="woo",
        read_source="browser_real",
    )
    assert out.success is False
    assert out.error_code == ERROR_DETAIL_POST_SAVE_PRICE_MISMATCH
    assert out.parsed_result["verify_passed"] is False


def test_write_flow_post_save_readback_missing_is_failure(monkeypatch, tmp_path):
    _base_settings(monkeypatch)
    page = _mk_page(after_price_text="39.90", save_status="success", save_text="saved")

    # Break post-save readback by raising on second price locator read
    def locator(sel: str):
        if sel == "#empty":
            return _mk_loc(visible=False)
        if sel == "#price":
            if not hasattr(locator, "_n"):
                locator._n = 0
            locator._n += 1
            if locator._n == 1:
                return _mk_loc(text="59.90")
            raise RuntimeError("missing price node")
        if sel == "#new":
            return _mk_loc()
        if sel == "#save":
            return _mk_loc()
        if sel == "#save-result":
            return _mk_loc(visible=True, text="saved", attr={"data-status": "success"})
        return _mk_loc()

    page.locator = MagicMock(side_effect=locator)
    out = run_real_admin_update_price_flow(
        page=page,
        evidence_dir=Path(tmp_path),
        evidence_paths=[],
        task_id="TASK-X",
        sku="A001",
        readiness_snapshot={"ready": True},
        timeout_ms=5000,
        requested_target_price=39.9,
        requested_current_price=59.9,
        verify_mode="basic",
        dry_run=False,
        platform="woo",
        read_source="browser_real",
    )
    assert out.success is False
    assert out.error_code == ERROR_DETAIL_POST_SAVE_READBACK_MISSING
    assert out.parsed_result["verify_reason"] == "post_save_readback_missing"


def test_write_flow_save_result_error_is_failure(monkeypatch, tmp_path):
    _base_settings(monkeypatch)
    page = _mk_page(after_price_text="39.90", save_status="error", save_text="failed")
    out = run_real_admin_update_price_flow(
        page=page,
        evidence_dir=Path(tmp_path),
        evidence_paths=[],
        task_id="TASK-X",
        sku="A001",
        readiness_snapshot={"ready": True},
        timeout_ms=5000,
        requested_target_price=39.9,
        requested_current_price=59.9,
        verify_mode="basic",
        dry_run=False,
        platform="woo",
        read_source="browser_real",
    )
    assert out.success is False
    assert out.error_code == ERROR_DETAIL_SAVE_RESULT_ERROR
    assert out.parsed_result["verify_reason"] == "save_result_error"


def test_write_flow_save_result_timeout_is_failure(monkeypatch, tmp_path):
    _base_settings(monkeypatch)
    base_page = _mk_page(after_price_text="39.90", save_status="success", save_text="saved")
    orig_locator = base_page.locator

    def locator(sel: str):
        if sel == "#save-result":
            loc = orig_locator(sel)
            loc.wait_for = MagicMock(side_effect=RuntimeError("timeout"))
            return loc
        return orig_locator(sel)

    base_page.locator = MagicMock(side_effect=locator)

    out = run_real_admin_update_price_flow(
        page=base_page,
        evidence_dir=Path(tmp_path),
        evidence_paths=[],
        task_id="TASK-X",
        sku="A001",
        readiness_snapshot={"ready": True},
        timeout_ms=100,
        requested_target_price=39.9,
        requested_current_price=59.9,
        verify_mode="basic",
        dry_run=False,
        platform="woo",
        read_source="browser_real",
    )
    assert out.success is False
    assert out.error_code == ERROR_DETAIL_SAVE_RESULT_TIMEOUT


def test_write_flow_submit_no_effect_is_failure(monkeypatch, tmp_path):
    _base_settings(monkeypatch)
    page = _mk_page(after_price_text="39.90", save_status="idle", save_text="")
    out = run_real_admin_update_price_flow(
        page=page,
        evidence_dir=Path(tmp_path),
        evidence_paths=[],
        task_id="TASK-X",
        sku="A001",
        readiness_snapshot={"ready": True},
        timeout_ms=5000,
        requested_target_price=39.9,
        requested_current_price=59.9,
        verify_mode="basic",
        dry_run=False,
        platform="woo",
        read_source="browser_real",
    )
    assert out.success is False
    assert out.error_code == ERROR_DETAIL_SUBMIT_NO_EFFECT

