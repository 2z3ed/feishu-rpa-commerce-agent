"""P4.1 RPA target profile + readiness + Playwright context injection."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.core.config import settings
from app.graph.nodes import execute_action
from app.rpa.browser_playwright_runner import (
    PlaywrightUpdatePriceRunner,
    _playwright_context_options,
    _real_admin_abs_url,
    _real_admin_catalog_with_sku_query,
)
from app.rpa.schema import RpaExecutionInput, RpaExecutionOutput
from app.rpa.target_readiness import evaluate_rpa_target_readiness, norm_rpa_target_profile


def test_norm_profile_unknown_defaults():
    assert norm_rpa_target_profile("bogus") == "internal_controlled"


def test_internal_controlled_readiness_always_ready(monkeypatch):
    monkeypatch.setattr(settings, "RPA_TARGET_PROFILE", "internal_controlled")
    rr = evaluate_rpa_target_readiness(settings)
    assert rr.ready is True
    assert rr.profile == "internal_controlled"
    assert rr.browser_real_allowed is True


def test_real_admin_missing_config(monkeypatch):
    monkeypatch.setattr(settings, "RPA_TARGET_PROFILE", "real_admin_prepared")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_BASE_URL", "")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_HOME_PATH", "")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_CATALOG_PATH", "")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_DETAIL_PATH_TEMPLATE", "")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_SKU_SEARCH_PARAM", "")
    rr = evaluate_rpa_target_readiness(settings)
    assert rr.ready is False
    assert rr.not_ready_reason == "missing_real_admin_config"
    assert "RPA_REAL_ADMIN_BASE_URL" in rr.missing_config_fields


def test_real_admin_config_ok_missing_session(monkeypatch):
    monkeypatch.setattr(settings, "RPA_TARGET_PROFILE", "real_admin_prepared")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_BASE_URL", "https://shop.example.test")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_HOME_PATH", "/wp-admin/")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_CATALOG_PATH", "/products")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_DETAIL_PATH_TEMPLATE", "/p/{sku}")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_SKU_SEARCH_PARAM", "sku")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_DETAIL_PRICE_SELECTOR", "[data-testid='p']")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_CATALOG_EMPTY_SELECTOR", "[data-testid='e']")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_SESSION_COOKIE", "")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_SESSION_HEADERS_JSON", "")
    rr = evaluate_rpa_target_readiness(settings)
    assert rr.ready is False
    assert rr.missing_session is True
    assert rr.not_ready_reason == "missing_session"


def test_playwright_context_options_merge_cookie_and_json(monkeypatch):
    monkeypatch.setattr(settings, "RPA_BROWSER_EXTRA_HTTP_HEADERS_JSON", '{"X-A":"1"}')
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_SESSION_HEADERS_JSON", '{"X-B":"2"}')
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_SESSION_COOKIE", "sid=z")
    opts = _playwright_context_options()
    h = opts["extra_http_headers"]
    assert h["X-A"] == "1"
    assert h["X-B"] == "2"
    assert h["Cookie"] == "sid=z"


def test_playwright_real_admin_ready_delegates_to_readonly_flow(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "RPA_TARGET_PROFILE", "real_admin_prepared")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_BASE_URL", "https://example.com")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_HOME_PATH", "/admin")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_CATALOG_PATH", "/products")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_DETAIL_PATH_TEMPLATE", "/edit/{sku}")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_SKU_SEARCH_PARAM", "sku")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_DETAIL_PRICE_SELECTOR", "[data-testid='p']")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_CATALOG_EMPTY_SELECTOR", "[data-testid='e']")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_SESSION_COOKIE", "session=x")
    monkeypatch.setattr(settings, "RPA_TARGET_ENV", "sandbox")
    monkeypatch.setattr(settings, "RPA_BROWSER_HEADLESS", True)
    monkeypatch.setattr(settings, "RPA_BROWSER_TIMEOUT_S", 30)

    ev = tmp_path / "e"
    ev.mkdir()
    mock_page = MagicMock()
    mock_page.goto = MagicMock()
    mock_page.set_default_timeout = MagicMock()
    mock_page.screenshot = MagicMock(return_value=None)

    mock_context = MagicMock()
    mock_context.new_page.return_value = mock_page
    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_context

    mock_playwright_instance = MagicMock()
    mock_playwright_instance.chromium.launch.return_value = mock_browser
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_playwright_instance
    mock_cm.__exit__.return_value = None

    captured: dict = {}

    def fake_flow(self, page, evidence_dir, paths, inp, sku, tp, cp, snap, *, timeout_ms):
        captured["sku"] = sku
        return RpaExecutionOutput(
            success=True,
            result_summary="stub",
            parsed_result={"sku": sku, "rpa_target_profile": "real_admin_prepared"},
            evidence_paths=list(paths),
            error_code=None,
            error_message=None,
        )

    monkeypatch.setattr(PlaywrightUpdatePriceRunner, "_flow_real_admin_prepared_readonly", fake_flow)

    with patch("playwright.sync_api.sync_playwright", return_value=mock_cm):
        runner = PlaywrightUpdatePriceRunner(runner_name="browser_real", force_failure=False)
        out = runner.run(
            RpaExecutionInput(
                task_id="T1",
                trace_id="t",
                intent="product.update_price",
                platform="woo",
                params={"sku": "A001", "target_price": 9.9, "current_price": 1.0},
                timeout_s=30,
                evidence_dir=str(ev),
                verify_mode="basic",
                dry_run=False,
            )
        )

    assert out.success is True
    assert captured.get("sku") == "A001"
    mock_browser.new_context.assert_called_once()
    kwargs = mock_browser.new_context.call_args.kwargs
    assert "extra_http_headers" in kwargs
    assert kwargs["extra_http_headers"].get("Cookie") == "session=x"


def test_execute_action_confirm_readiness_fail_sets_backend_reason(monkeypatch):
    def fake_confirm(_executor, state, slots):
        return {
            "error": "缺会话",
            "error_code": "rpa_target_readiness_failed",
            "_rpa_meta": {
                "execution_mode": "rpa",
                "execution_backend": "rpa_browser_real",
                "selected_backend": "rpa_browser_real",
                "final_backend": "rpa_browser_real",
                "rpa_runner": "browser_real",
                "evidence_count": 0,
                "verify_mode": "basic",
                "platform": "woo",
                "rpa_readiness_failed": True,
                "readiness_details": {"not_ready_reason": "missing_session"},
            },
        }

    monkeypatch.setattr(
        "app.graph.nodes.execute_action.execute_task_confirmation",
        fake_confirm,
    )
    state = {
        "intent_code": "system.confirm_task",
        "slots": {"task_id": "TASK-ORIG"},
        "task_id": "TASK-CONFIRM",
        "status": "processing",
    }
    out = execute_action.execute_action(state)
    assert out["status"] == "failed"
    assert out["backend_selection_reason"] == "rpa_readiness_failed"


def test_real_admin_missing_detail_selectors_in_readiness(monkeypatch):
    monkeypatch.setattr(settings, "RPA_TARGET_PROFILE", "real_admin_prepared")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_BASE_URL", "https://shop.example.test")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_HOME_PATH", "/wp-admin/")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_CATALOG_PATH", "/products")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_DETAIL_PATH_TEMPLATE", "/p/{sku}")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_SKU_SEARCH_PARAM", "sku")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_DETAIL_PRICE_SELECTOR", "")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_CATALOG_EMPTY_SELECTOR", "[e]")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_SESSION_COOKIE", "x=1")
    rr = evaluate_rpa_target_readiness(settings)
    assert rr.ready is False
    assert "RPA_REAL_ADMIN_DETAIL_PRICE_SELECTOR" in rr.missing_config_fields


def test_real_admin_url_join_and_catalog_query():
    base = "https://ex.com"
    assert _real_admin_abs_url(base, "/a/b") == "https://ex.com/a/b"
    assert _real_admin_abs_url(base, "/c?x=1") == "https://ex.com/c?x=1"
    cat = _real_admin_catalog_with_sku_query("/catalog", "sku", "AB 1")
    assert "sku=" in cat and "catalog" in cat


def test_verify_only_allows_real_admin_without_list_detail(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "RPA_TARGET_PROFILE", "real_admin_prepared")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_BASE_URL", "https://example.com")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_HOME_PATH", "/admin")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_CATALOG_PATH", "/products")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_DETAIL_PATH_TEMPLATE", "/edit/{sku}")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_SKU_SEARCH_PARAM", "sku")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_DETAIL_PRICE_SELECTOR", "[p]")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_CATALOG_EMPTY_SELECTOR", "[e]")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_SESSION_COOKIE", "s=1")
    monkeypatch.setattr(settings, "RPA_TARGET_ENV", "sandbox")

    ev = tmp_path / "e"
    ev.mkdir()

    def fake_flow(self, *a, **k):
        return RpaExecutionOutput(
            success=True,
            result_summary="v",
            parsed_result={"operation_result": "readonly_verify"},
            evidence_paths=[],
            error_code=None,
            error_message=None,
        )

    monkeypatch.setattr(PlaywrightUpdatePriceRunner, "_flow_real_admin_prepared_readonly", fake_flow)

    mock_page = MagicMock()
    mock_context = MagicMock()
    mock_context.new_page.return_value = mock_page
    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_context
    mock_playwright_instance = MagicMock()
    mock_playwright_instance.chromium.launch.return_value = mock_browser
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_playwright_instance
    mock_cm.__exit__.return_value = None

    with patch("playwright.sync_api.sync_playwright", return_value=mock_cm):
        runner = PlaywrightUpdatePriceRunner(runner_name="browser_real", force_failure=False)
        out = runner.run(
            RpaExecutionInput(
                task_id="T1",
                trace_id="t",
                intent="product.update_price",
                platform="woo",
                params={
                    "sku": "A001",
                    "target_price": 9.9,
                    "current_price": 1.0,
                    "_list_detail_verify_only": True,
                },
                timeout_s=30,
                evidence_dir=str(ev),
                verify_mode="basic",
                dry_run=False,
            )
        )
    assert out.success is True


def test_real_admin_mirror_pages(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_INTERNAL_SANDBOX_API", True)
    from fastapi.testclient import TestClient

    from app.main import app

    c = TestClient(app)
    assert c.get("/api/v1/internal/rpa-real-admin-mirror/home").status_code == 200
    r_cat = c.get(
        "/api/v1/internal/rpa-real-admin-mirror/catalog",
        params={"sku": "__MIRROR_EMPTY__"},
    )
    assert r_cat.status_code == 200
    assert 'data-visible="1"' in r_cat.text
    r_ok = c.get("/api/v1/internal/rpa-real-admin-mirror/catalog", params={"sku": "A001"})
    assert "real-admin-catalog-results" in r_ok.text
    r_d = c.get("/api/v1/internal/rpa-real-admin-mirror/detail/A001")
    assert "real-admin-current-price" in r_d.text
    r_miss = c.get(
        "/api/v1/internal/rpa-real-admin-mirror/detail/A001",
        params={"mirror_fail": "missing_price"},
    )
    assert r_miss.status_code == 200
    assert "real-admin-current-price" not in r_miss.text


def test_real_admin_detail_selector_missing_error(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "RPA_TARGET_PROFILE", "real_admin_prepared")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_BASE_URL", "https://example.com")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_HOME_PATH", "/h")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_CATALOG_PATH", "/c")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_DETAIL_PATH_TEMPLATE", "/d/{sku}")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_SKU_SEARCH_PARAM", "sku")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_DETAIL_PRICE_SELECTOR", "#missing-node")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_CATALOG_EMPTY_SELECTOR", "#never")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_SESSION_COOKIE", "s=1")
    monkeypatch.setattr(settings, "RPA_TARGET_ENV", "sandbox")
    monkeypatch.setattr(settings, "RPA_BROWSER_TIMEOUT_S", 5)

    ev = tmp_path / "e"
    ev.mkdir()

    class Resp:
        status = 200

    mock_page = MagicMock()
    mock_page.goto = MagicMock(return_value=Resp())
    mock_page.wait_for_timeout = MagicMock()
    mock_page.url = "https://example.com/d/A001"
    mock_loc = MagicMock()
    mock_loc.first = mock_loc
    mock_loc.is_visible = MagicMock(return_value=False)
    mock_loc.wait_for = MagicMock(side_effect=RuntimeError("timeout"))
    mock_loc.inner_text = MagicMock(return_value="")
    mock_loc.input_value = MagicMock(return_value="")
    mock_page.locator = MagicMock(return_value=mock_loc)
    mock_page.screenshot = MagicMock(return_value=None)

    mock_context = MagicMock()
    mock_context.new_page.return_value = mock_page
    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_context
    mock_playwright_instance = MagicMock()
    mock_playwright_instance.chromium.launch.return_value = mock_browser
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_playwright_instance
    mock_cm.__exit__.return_value = None

    with patch("playwright.sync_api.sync_playwright", return_value=mock_cm):
        runner = PlaywrightUpdatePriceRunner(runner_name="browser_real", force_failure=False)
        out = runner.run(
            RpaExecutionInput(
                task_id="T1",
                trace_id="t",
                intent="product.update_price",
                platform="woo",
                params={"sku": "A001", "target_price": 9.9, "current_price": 1.0},
                timeout_s=30,
                evidence_dir=str(ev),
                verify_mode="basic",
                dry_run=False,
            )
        )
    assert out.success is False
    assert out.error_code == "rpa_real_admin_detail_selector_missing"


def test_internal_readiness_rpa_target_route(monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app

    monkeypatch.setattr(settings, "RPA_TARGET_PROFILE", "internal_controlled")
    c = TestClient(app)
    r = c.get("/api/v1/internal/readiness/rpa-target")
    assert r.status_code == 200
    body = r.json()
    assert body["rpa_target_profile"] == "internal_controlled"
    assert body["ready"] is True
