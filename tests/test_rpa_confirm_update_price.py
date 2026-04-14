"""RPA contract, fake runner, and confirm-phase wiring (dev)."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.rpa.schema import RpaExecutionOutput
from app.graph.nodes import execute_action
from app.repositories.product_repo import product_repo
from app.db.base import Base
from app.db.models import TaskRecord
from app.core.time import get_shanghai_now
from app.rpa.confirm_update_price import (
    ERROR_API_THEN_RPA_VERIFY_PROFILE_NOT_SUPPORTED,
    run_confirm_update_price_api_then_rpa_verify,
    run_confirm_update_price_rpa,
)
from app.rpa.local_fake_runner import LocalFakeRpaRunner
from app.rpa.schema import RpaExecutionInput
from app.rpa.query_sku_status import run_query_sku_status_real_admin_readonly
from app.rpa.real_admin_readonly import ERROR_DETAIL_SAVE_BUTTON_DISABLED

import pytest

_HAS_PLAYWRIGHT = importlib.util.find_spec("playwright") is not None

def test_rpa_execution_io_models_roundtrip():
    raw = {
        "task_id": "TASK-1",
        "trace_id": "tr-1",
        "intent": "product.update_price",
        "platform": "woo",
        "params": {"sku": "A001", "target_price": 39.9},
        "timeout_s": 60,
        "evidence_dir": "/tmp/ev",
        "verify_mode": "basic",
        "dry_run": False,
    }
    inp = RpaExecutionInput.model_validate(raw)
    d = inp.model_dump()
    assert d["task_id"] == "TASK-1"
    assert d["params"]["sku"] == "A001"


def test_local_fake_runner_writes_evidence_and_succeeds(tmp_path):
    ev = tmp_path / "TASK-X"
    ev.mkdir(parents=True)
    runner = LocalFakeRpaRunner(force_failure=False)
    out = runner.run(
        RpaExecutionInput(
            task_id="TASK-X",
            trace_id="trace",
            intent="product.update_price",
            platform="woo",
            params={"sku": "A001", "target_price": 39.9},
            timeout_s=30,
            evidence_dir=str(ev),
            verify_mode="basic",
            dry_run=False,
        )
    )
    assert out.success is True
    assert out.error_code is None
    assert len(out.evidence_paths) >= 1
    assert (ev / "run_input.json").is_file()
    payload = json.loads((ev / "run_input.json").read_text(encoding="utf-8"))
    assert payload["intent"] == "product.update_price"


def test_local_fake_runner_force_failure(tmp_path):
    ev = tmp_path / "TASK-FAIL"
    ev.mkdir(parents=True)
    runner = LocalFakeRpaRunner(force_failure=True)
    out = runner.run(
        RpaExecutionInput(
            task_id="TASK-FAIL",
            trace_id="t",
            intent="product.update_price",
            platform="woo",
            params={"sku": "A001", "target_price": 1.0},
            timeout_s=30,
            evidence_dir=str(ev),
            verify_mode="none",
            dry_run=False,
        )
    )
    assert out.success is False
    assert out.error_code == "rpa_fake_forced_failure"
    assert any("99_failure" in p for p in out.evidence_paths)


def test_run_confirm_update_price_rpa_success(monkeypatch, tmp_path):
    monkeypatch.setattr("app.rpa.confirm_update_price.log_step", lambda *a, **k: None)
    monkeypatch.setattr(settings, "RPA_RUNNER_TYPE", "local_fake")
    monkeypatch.setattr(settings, "RPA_TARGET_PROFILE", "internal_controlled")
    monkeypatch.setattr(settings, "RPA_TARGET_ENV", "sandbox")
    monkeypatch.setattr(settings, "RPA_EVIDENCE_BASE_DIR", str(tmp_path / "ev"))
    monkeypatch.setattr(settings, "RPA_FAKE_RUNNER_FORCE_FAILURE", False)
    monkeypatch.setattr(settings, "RPA_UPDATE_PRICE_DRY_RUN", False)
    legacy, err = run_confirm_update_price_rpa(
        confirm_task_id="TASK-RPA-OK",
        trace_id="trace-z",
        sku="A001",
        target_price=39.9,
        platform="woo",
    )
    assert err is None
    assert legacy is not None
    assert legacy["sku"] == "A001"
    assert legacy["status"] == "success"
    assert "_rpa_meta" in legacy
    assert legacy["_rpa_meta"]["evidence_count"] >= 1


def test_run_confirm_update_price_rpa_forced_fail(monkeypatch, tmp_path):
    monkeypatch.setattr("app.rpa.confirm_update_price.log_step", lambda *a, **k: None)
    monkeypatch.setattr(settings, "RPA_RUNNER_TYPE", "local_fake")
    monkeypatch.setattr(settings, "RPA_TARGET_PROFILE", "internal_controlled")
    monkeypatch.setattr(settings, "RPA_TARGET_ENV", "sandbox")
    monkeypatch.setattr(settings, "RPA_EVIDENCE_BASE_DIR", str(tmp_path / "ev"))
    monkeypatch.setattr(settings, "RPA_FAKE_RUNNER_FORCE_FAILURE", True)
    legacy, err = run_confirm_update_price_rpa(
        confirm_task_id="TASK-RPA-FAIL",
        trace_id="t",
        sku="A001",
        target_price=39.9,
    )
    assert legacy is None
    assert err is not None
    assert err.get("error_code") == "rpa_fake_forced_failure"


def test_execute_action_confirm_merges_rpa_meta(monkeypatch):
    def fake_confirm(_executor, state, slots):
        return {
            "status": "success",
            "sku": "A001",
            "old_price": 10.0,
            "new_price": 20.0,
            "verify_passed": True,
            "verify_reason": "ok",
            "operation_result": "write_update_price",
            "parsed_result": {
                "failure_layer": "",
                "old_price": 10.0,
                "new_price": 20.0,
                "post_save_price": 20.0,
                "verify_passed": True,
                "verify_reason": "ok",
                "operation_result": "write_update_price",
            },
            "platform": "woo",
            "_rpa_meta": {
                "execution_mode": "rpa",
                "execution_backend": "rpa_local_fake",
                "selected_backend": "rpa_local_fake",
                "final_backend": "rpa_local_fake",
                "rpa_runner": "local_fake",
                "evidence_count": 4,
                "verify_mode": "basic",
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
    assert out["status"] == "succeeded"
    assert out["execution_mode"] == "rpa"
    assert out["evidence_count"] == 4
    assert out["rpa_runner"] == "local_fake"
    assert out["verify_mode"] == "basic"
    assert out["final_backend"] == "rpa_local_fake"
    assert out["verify_passed"] is True
    assert out["verify_reason"] == "ok"
    assert isinstance(out.get("parsed_result"), dict)
    assert out["parsed_result"]["verify_passed"] is True


def test_execute_action_confirm_failure_merges_rpa_meta(monkeypatch):
    def fake_confirm_fail(_executor, state, slots):
        return {
            "error": "[confirm_target_invalid] LocalFakeRpaRunner: force_failure enabled",
            "error_code": "confirm_target_invalid",
            "parsed_result": {"failure_layer": "confirm_target_invalid"},
            "_rpa_meta": {
                "execution_mode": "rpa",
                "execution_backend": "rpa_local_fake",
                "selected_backend": "rpa_local_fake",
                "final_backend": "rpa_local_fake",
                "rpa_runner": "local_fake",
                "evidence_count": 3,
                "verify_mode": "basic",
                "platform": "woo",
            },
        }

    monkeypatch.setattr(
        "app.graph.nodes.execute_action.execute_task_confirmation",
        fake_confirm_fail,
    )
    state = {
        "intent_code": "system.confirm_task",
        "slots": {"task_id": "TASK-ORIG"},
        "task_id": "TASK-CONFIRM",
        "status": "processing",
    }
    out = execute_action.execute_action(state)
    assert out["status"] == "failed"
    assert out["execution_mode"] == "rpa"
    assert out["execution_backend"] == "rpa_local_fake"
    assert out["evidence_count"] == 3
    assert out["rpa_runner"] == "local_fake"
    assert out["verify_mode"] == "basic"
    assert out["platform"] == "woo"
    assert out["final_backend"] == "rpa_local_fake"


def test_execute_action_confirm_failure_result_summary_uses_failure_layer(monkeypatch):
    def fake_confirm_fail(_executor, state, slots):
        return {
            "error": "[old_label] 原始错误文案",
            "error_code": "confirm_target_invalid",
            "parsed_result": {"failure_layer": "confirm_target_invalid"},
        }

    monkeypatch.setattr(
        "app.graph.nodes.execute_action.execute_task_confirmation",
        fake_confirm_fail,
    )
    state = {
        "intent_code": "system.confirm_task",
        "slots": {"task_id": "TASK-ORIG"},
        "task_id": "TASK-CONFIRM",
        "status": "processing",
    }
    out = execute_action.execute_action(state)
    assert out["status"] == "failed"
    assert out["failure_layer"] == "confirm_target_invalid"
    assert out["error_message"] == "[confirm_target_invalid] 原始错误文案"
    assert out["result_summary"] == "确认失败：[confirm_target_invalid] 原始错误文案"


def test_run_confirm_update_price_rpa_failure_includes_meta(monkeypatch, tmp_path):
    monkeypatch.setattr("app.rpa.confirm_update_price.log_step", lambda *a, **k: None)
    monkeypatch.setattr(settings, "RPA_RUNNER_TYPE", "local_fake")
    monkeypatch.setattr(settings, "RPA_TARGET_PROFILE", "internal_controlled")
    monkeypatch.setattr(settings, "RPA_TARGET_ENV", "sandbox")
    monkeypatch.setattr(settings, "RPA_EVIDENCE_BASE_DIR", str(tmp_path / "ev"))
    monkeypatch.setattr(settings, "RPA_FAKE_RUNNER_FORCE_FAILURE", True)
    legacy, err = run_confirm_update_price_rpa(
        confirm_task_id="TASK-META-FAIL",
        trace_id="t",
        sku="A001",
        target_price=39.9,
    )
    assert legacy is None and err is not None
    assert "_rpa_meta" in err
    assert err["_rpa_meta"]["execution_mode"] == "rpa"
    assert err["_rpa_meta"]["evidence_count"] >= 1
    assert err["_rpa_meta"]["platform"] == "woo"
    assert err["_rpa_meta"]["selected_backend"] == "rpa_local_fake"
    pr = err.get("parsed_result") or {}
    for key in (
        "old_price",
        "new_price",
        "post_save_price",
        "verify_passed",
        "verify_reason",
        "operation_result",
        "failure_layer",
    ):
        assert key in pr


def test_get_update_price_runner_browser_real(monkeypatch):
    monkeypatch.setattr(settings, "RPA_RUNNER_TYPE", "browser_real")
    monkeypatch.setattr(settings, "RPA_BROWSER_FORCE_FAILURE", False)
    from app.rpa.browser_playwright_runner import PlaywrightUpdatePriceRunner
    from app.rpa.confirm_update_price import get_update_price_runner

    r = get_update_price_runner()
    assert isinstance(r, PlaywrightUpdatePriceRunner)


def test_internal_rpa_sandbox_page_contains_controls():
    from fastapi.testclient import TestClient
    from fastapi import FastAPI

    from app.api.v1.internal_rpa_sandbox import router as sandbox_router

    app = FastAPI()
    app.include_router(sandbox_router, prefix="/api/v1")
    c = TestClient(app)
    r = c.get("/api/v1/internal/rpa-sandbox/update-price?sku=A001&current_price=59.9&target_price=39.9")
    assert r.status_code == 200
    assert "submit-btn" in r.text
    assert "target-price" in r.text
    assert "data-testid=\"sku\"" in r.text


def test_playwright_runner_success_mocked(monkeypatch, tmp_path):
    if not _HAS_PLAYWRIGHT:
        pytest.skip("playwright not installed in this environment")
    from app.rpa.browser_playwright_runner import PlaywrightUpdatePriceRunner
    from app.rpa.schema import RpaExecutionInput

    ev = tmp_path / "e"
    ev.mkdir()
    monkeypatch.setattr(settings, "RPA_SANDBOX_BASE_URL", "http://127.0.0.1:8000")
    monkeypatch.setattr(settings, "RPA_TARGET_ENV", "sandbox")
    monkeypatch.setattr(settings, "RPA_TARGET_PROFILE", "internal_controlled")
    monkeypatch.setattr(settings, "RPA_BROWSER_HEADLESS", True)
    monkeypatch.setattr(settings, "RPA_BROWSER_TIMEOUT_S", 30)

    mock_page = MagicMock()
    mock_page.goto = MagicMock()
    mock_page.fill = MagicMock()
    mock_page.click = MagicMock()
    mock_page.set_default_timeout = MagicMock()
    mock_loc = MagicMock()
    mock_loc.get_attribute.side_effect = ["success", "39.9", "59.9"]
    mock_loc.inner_text.return_value = "ok"
    mock_page.locator.return_value = mock_loc
    mock_page.wait_for_selector = MagicMock()

    def shot(path=None, **kwargs):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_bytes(b"fakepng")

    mock_page.screenshot = shot

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
                params={"sku": "A001", "target_price": 39.9, "current_price": 59.9},
                timeout_s=30,
                evidence_dir=str(ev),
                verify_mode="basic",
                dry_run=False,
            )
        )
    assert out.success is True
    assert out.parsed_result.get("sku") == "A001"
    assert len(out.evidence_paths) >= 1
    mock_page.goto.assert_called_once()


def test_internal_admin_like_catalog_and_detail():
    from fastapi.testclient import TestClient
    from fastapi import FastAPI

    from app.api.v1.internal_rpa_admin_like import router as admin_like_router

    app = FastAPI()
    app.include_router(admin_like_router, prefix="/api/v1")
    c = TestClient(app)
    cat = c.get(
        "/api/v1/internal/rpa-sandbox/admin-like/catalog?sku=A001&current_price=59.9&target_price=39.9&failure_mode=none"
    )
    assert cat.status_code == 200
    assert "catalog-root" in cat.text
    assert "catalog-search-btn" in cat.text
    det = c.get(
        "/api/v1/internal/rpa-sandbox/admin-like/product-detail?sku=A001&current_price=59.9&target_price=39.9&failure_mode=none&broken=0"
    )
    assert det.status_code == 200
    assert "detail-product-root" in det.text
    broken = c.get(
        "/api/v1/internal/rpa-sandbox/admin-like/product-detail?sku=A001&broken=1&failure_mode=detail_page_not_found"
    )
    assert broken.status_code == 200
    assert "detail-not-found" in broken.text


def test_internal_admin_like_hub_and_workbench():
    from fastapi.testclient import TestClient
    from fastapi import FastAPI

    from app.api.v1.internal_rpa_admin_like import router as admin_like_router

    app = FastAPI()
    app.include_router(admin_like_router, prefix="/api/v1")
    c = TestClient(app)
    h = c.get("/api/v1/internal/rpa-sandbox/admin-like?sku=A001&failure_mode=none")
    assert h.status_code == 200
    assert "nav-to-catalog" in h.text
    assert "nav-to-update-price" in h.text
    assert "admin-hub-root" in h.text
    w = c.get(
        "/api/v1/internal/rpa-sandbox/admin-like/update-price?sku=A001&current_price=59.9&target_price=39.9&failure_mode=none"
    )
    assert w.status_code == 200
    assert "admin-update-root" in w.text
    assert "locate-sku" in w.text
    assert "save-price" in w.text


def test_admin_like_hub_propagates_list_detail_failure_to_catalog_link():
    """list_detail RPA opens hub with detail_page_not_found; catalog href must keep it (P3.3)."""
    from fastapi.testclient import TestClient
    from fastapi import FastAPI

    from app.api.v1.internal_rpa_admin_like import router as admin_like_router

    app = FastAPI()
    app.include_router(admin_like_router, prefix="/api/v1")
    c = TestClient(app)
    h = c.get(
        "/api/v1/internal/rpa-sandbox/admin-like?sku=A001&current_price=59.9&target_price=39.9"
        "&failure_mode=detail_page_not_found"
    )
    assert h.status_code == 200
    assert "nav-to-catalog" in h.text
    assert "failure_mode=detail_page_not_found" in h.text
    assert "/admin-like/catalog?" in h.text
    # Workbench link uses admin-only normalization → unknown list-detail mode becomes none
    assert "admin-like/update-price?" in h.text
    assert "failure_mode=none" in h.text


def test_list_detail_request_chain_hub_catalog_detail_detail_page_not_found():
    """
    E2E parse of the same navigation chain as browser_real list_detail:
    hub (query) → catalog href → detail href must keep failure_mode and broken=1.
    """
    import html as html_stdlib
    import re
    from urllib.parse import parse_qs, unquote, urlparse

    from fastapi.testclient import TestClient
    from fastapi import FastAPI

    from app.api.v1.internal_rpa_admin_like import router as admin_like_router

    app = FastAPI()
    app.include_router(admin_like_router, prefix="/api/v1")
    c = TestClient(app)
    hub_path = (
        "/api/v1/internal/rpa-sandbox/admin-like"
        "?sku=A001&current_price=59.9&target_price=39.9&failure_mode=detail_page_not_found"
    )
    rh = c.get(hub_path)
    assert rh.status_code == 200
    hub_qs = parse_qs(urlparse(hub_path).query)
    assert hub_qs.get("failure_mode") == ["detail_page_not_found"]

    m_cat = re.search(r'<a href="([^"]+)"[^>]*data-testid="nav-to-catalog"', rh.text)
    assert m_cat, "nav-to-catalog href missing"
    # Hub template uses html.escape on href; & becomes &amp; in HTML.
    catalog_path = unquote(html_stdlib.unescape(m_cat.group(1)))
    assert "/admin-like/catalog?" in catalog_path
    cat_qs = parse_qs(urlparse(catalog_path).query)
    assert cat_qs.get("failure_mode") == ["detail_page_not_found"], cat_qs

    rc = c.get(catalog_path)
    assert rc.status_code == 200

    m_det = re.search(r'data-testid="open-product-detail"\s+href="([^"]+)"', rc.text)
    assert m_det, "open-product-detail href missing"
    detail_path = unquote(html_stdlib.unescape(m_det.group(1)))
    det_qs = parse_qs(urlparse(detail_path).query)
    assert det_qs.get("failure_mode") == ["detail_page_not_found"], det_qs
    assert det_qs.get("broken") == ["1"], det_qs

    rd = c.get(detail_path)
    assert rd.status_code == 200
    assert "detail-not-found" in rd.text


def test_playwright_runner_dispatches_admin_like(monkeypatch, tmp_path):
    if not _HAS_PLAYWRIGHT:
        pytest.skip("playwright not installed in this environment")
    from app.rpa.browser_playwright_runner import PlaywrightUpdatePriceRunner
    from app.rpa.schema import RpaExecutionInput

    ev = tmp_path / "e"
    ev.mkdir()
    monkeypatch.setattr(settings, "RPA_TARGET_ENV", "admin_like")
    monkeypatch.setattr(settings, "RPA_TARGET_PROFILE", "internal_controlled")
    monkeypatch.setattr(settings, "RPA_SANDBOX_BASE_URL", "http://127.0.0.1:8000")
    monkeypatch.setattr(settings, "RPA_BROWSER_HEADLESS", True)
    monkeypatch.setattr(settings, "RPA_BROWSER_TIMEOUT_S", 30)

    def fake_admin(self, page, evidence_dir, pths, inp, sku, tp, cp):
        assert sku == "A001"
        Path(evidence_dir, "stub.png").write_bytes(b"x")
        return RpaExecutionOutput(
            success=True,
            result_summary="admin stub",
            parsed_result={
                "sku": sku,
                "target_price": float(tp),
                "old_price": float(cp),
                "platform": "woo",
                "dry_run": False,
                "verify_mode": "basic",
            },
            evidence_paths=pths + [str(Path(evidence_dir) / "stub.png")],
            error_code=None,
            error_message=None,
        )

    monkeypatch.setattr(PlaywrightUpdatePriceRunner, "_flow_admin_like", fake_admin)

    mock_page = MagicMock()
    mock_page.goto = MagicMock()
    mock_page.fill = MagicMock()
    mock_page.click = MagicMock()
    mock_page.set_default_timeout = MagicMock()
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
                params={"sku": "A001", "target_price": 39.9, "current_price": 59.9},
                timeout_s=30,
                evidence_dir=str(ev),
                verify_mode="basic",
                dry_run=False,
            )
        )
    assert out.success is True
    assert "admin stub" in out.result_summary
    assert len(out.evidence_paths) >= 2


def test_playwright_runner_dispatches_list_detail(monkeypatch, tmp_path):
    if not _HAS_PLAYWRIGHT:
        pytest.skip("playwright not installed in this environment")
    from app.rpa.browser_playwright_runner import PlaywrightUpdatePriceRunner
    from app.rpa.schema import RpaExecutionInput

    ev = tmp_path / "e"
    ev.mkdir()
    monkeypatch.setattr(settings, "RPA_TARGET_ENV", "list_detail")
    monkeypatch.setattr(settings, "RPA_TARGET_PROFILE", "internal_controlled")
    monkeypatch.setattr(settings, "RPA_SANDBOX_BASE_URL", "http://127.0.0.1:8000")
    monkeypatch.setattr(settings, "RPA_BROWSER_HEADLESS", True)
    monkeypatch.setattr(settings, "RPA_BROWSER_TIMEOUT_S", 30)

    def fake_ld(self, page, evidence_dir, pths, inp, sku, tp, cp):
        assert sku == "A001"
        Path(evidence_dir, "ld.png").write_bytes(b"x")
        return RpaExecutionOutput(
            success=True,
            result_summary="list_detail stub",
            parsed_result={
                "sku": sku,
                "old_price": float(cp),
                "new_price": float(tp),
                "page_status": "success",
                "page_message": "ok",
                "operation_result": "saved",
                "platform": "woo",
                "dry_run": False,
                "verify_mode": "basic",
                "target_price": float(tp),
            },
            evidence_paths=pths + [str(Path(evidence_dir) / "ld.png")],
            error_code=None,
            error_message=None,
        )

    monkeypatch.setattr(PlaywrightUpdatePriceRunner, "_flow_list_detail", fake_ld)

    mock_page = MagicMock()
    mock_page.goto = MagicMock()
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
                params={"sku": "A001", "target_price": 39.9, "current_price": 59.9},
                timeout_s=30,
                evidence_dir=str(ev),
                verify_mode="basic",
                dry_run=False,
            )
        )
    assert out.success is True
    assert out.parsed_result.get("operation_result") == "saved"
    assert len(out.evidence_paths) >= 2


def test_run_confirm_update_price_api_then_rpa_verify_success_local_fake(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "app.rpa.confirm_update_price.log_step",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(settings, "RPA_RUNNER_TYPE", "local_fake")
    monkeypatch.setattr(settings, "RPA_EVIDENCE_BASE_DIR", str(tmp_path / "ev"))
    monkeypatch.setattr(settings, "RPA_API_THEN_RPA_VERIFY_FORCE_PAGE_MISMATCH", False)
    monkeypatch.setattr(settings, "RPA_TARGET_PROFILE", "internal_controlled")
    orig = float(product_repo.query_sku_status("A001", "mock")["price"])
    try:
        legacy, err = run_confirm_update_price_api_then_rpa_verify(
            confirm_task_id="TASK-AV-OK",
            trace_id="t",
            sku="A001",
            target_price=39.9,
            platform="mock",
        )
        assert err is None and legacy is not None
        assert legacy["verify_passed"] is True
        assert legacy["api_price_after_update"] == 39.9
        meta = legacy["_rpa_meta"]
        assert meta["execution_mode"] == "api_then_rpa_verify"
        assert meta["verify_passed"] is True
        assert meta["expected_target_price"] == 39.9
        assert float(product_repo.query_sku_status("A001", "mock")["price"]) == 39.9
    finally:
        product_repo.update_price("A001", orig, "mock")


def test_run_confirm_update_price_api_then_rpa_verify_force_mismatch(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "app.rpa.confirm_update_price.log_step",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(settings, "RPA_RUNNER_TYPE", "local_fake")
    monkeypatch.setattr(settings, "RPA_TARGET_PROFILE", "internal_controlled")
    monkeypatch.setattr(settings, "RPA_EVIDENCE_BASE_DIR", str(tmp_path / "ev"))
    monkeypatch.setattr(settings, "RPA_API_THEN_RPA_VERIFY_FORCE_PAGE_MISMATCH", True)
    orig = float(product_repo.query_sku_status("A001", "mock")["price"])
    try:
        _, err = run_confirm_update_price_api_then_rpa_verify(
            confirm_task_id="TASK-AV-MIS",
            trace_id="t",
            sku="A001",
            target_price=42.0,
            platform="mock",
        )
        assert err is not None
        assert err["error_code"] == "verify_compare_failed"
        assert err["_rpa_meta"]["verify_passed"] is False
        assert "price_mismatch" in (err["_rpa_meta"].get("verify_reason") or "")
    finally:
        product_repo.update_price("A001", orig, "mock")


def test_run_confirm_update_price_api_then_rpa_verify_api_missing_sku(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "app.rpa.confirm_update_price.log_step",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(settings, "RPA_RUNNER_TYPE", "local_fake")
    monkeypatch.setattr(settings, "RPA_TARGET_PROFILE", "internal_controlled")
    monkeypatch.setattr(settings, "RPA_EVIDENCE_BASE_DIR", str(tmp_path / "ev"))
    legacy, err = run_confirm_update_price_api_then_rpa_verify(
        confirm_task_id="TASK-AV-API",
        trace_id="t",
        sku="ZZZ999",
        target_price=1.0,
        platform="mock",
    )
    assert legacy is None
    assert err["error_code"] == "api_update_sku_not_found"
    assert err["_rpa_meta"]["rpa_verification_skipped"] is True


def test_execute_action_confirm_api_then_rpa_verify_ok_backend_reason(monkeypatch):
    def fake_confirm(_executor, state, slots):
        return {
            "status": "success",
            "sku": "A001",
            "old_price": 59.9,
            "new_price": 39.9,
            "platform": "mock",
            "verify_passed": True,
            "verify_reason": "ok",
            "api_price_after_update": 39.9,
            "_rpa_meta": {
                "execution_mode": "api_then_rpa_verify",
                "execution_backend": "api_then_rpa_verify",
                "selected_backend": "api_then_rpa_verify",
                "final_backend": "api_then_rpa_verify",
                "rpa_runner": "local_fake",
                "evidence_count": 2,
                "verify_mode": "basic",
                "verify_passed": True,
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
    assert out["status"] == "succeeded"
    assert out["backend_selection_reason"] == "api_then_rpa_verify_ok"
    assert out["execution_mode"] == "api_then_rpa_verify"


def test_execute_action_confirm_api_then_rpa_verify_fail_backend_reason(monkeypatch):
    def fake_confirm(_executor, state, slots):
        return {
            "error": "页面核验未通过：price_mismatch",
            "_rpa_meta": {
                "execution_mode": "api_then_rpa_verify",
                "execution_backend": "api_then_rpa_verify",
                "selected_backend": "api_then_rpa_verify",
                "final_backend": "api_then_rpa_verify",
                "rpa_runner": "local_fake",
                "evidence_count": 2,
                "verify_mode": "basic",
                "platform": "mock",
                "verify_passed": False,
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
    assert out["backend_selection_reason"] == "api_then_rpa_verify_failed"


def test_query_readonly_bridge_returns_stable_read_contract(monkeypatch):
    monkeypatch.setattr(settings, "RPA_TARGET_PROFILE", "real_admin_prepared")
    monkeypatch.setattr("app.rpa.query_sku_status.log_step", lambda *a, **k: None)

    class _Runner:
        runner_name = "browser_real"

        def run(self, inp):
            return RpaExecutionOutput(
                success=True,
                result_summary="ok",
                parsed_result={
                    "sku": "A001",
                    "product_name": "Mirror Name",
                    "page_current_price": 59.9,
                    "page_status": "ok",
                    "page_message": "loaded",
                    "target_sku_hit": True,
                    "detail_loaded": True,
                    "read_source": "browser_real",
                    "profile": "real_admin_prepared",
                    "evidence_count": 2,
                },
                evidence_paths=["a.png", "b.png"],
                error_code=None,
                error_message=None,
            )

    monkeypatch.setattr("app.rpa.query_sku_status.get_update_price_runner", lambda force_failure=False: _Runner())
    out, err = run_query_sku_status_real_admin_readonly(task_id="TASK-Q-1", trace_id="t", sku="A001")
    assert err is None
    qr = out["query_result"]
    for key in (
        "sku",
        "product_name",
        "page_status",
        "page_message",
        "target_sku_hit",
        "detail_loaded",
        "read_source",
        "profile",
        "evidence_count",
    ):
        assert key in qr


def test_query_readonly_bridge_keeps_failure_taxonomy(monkeypatch):
    monkeypatch.setattr(settings, "RPA_TARGET_PROFILE", "real_admin_prepared")
    monkeypatch.setattr("app.rpa.query_sku_status.log_step", lambda *a, **k: None)

    class _Runner:
        runner_name = "browser_real"

        def run(self, inp):
            return RpaExecutionOutput(
                success=False,
                result_summary="detail selector missing",
                parsed_result={"detail_loaded": True, "target_sku_hit": False},
                evidence_paths=["f.png"],
                error_code="rpa_real_admin_detail_selector_missing",
                error_message="selector missing",
            )

    monkeypatch.setattr("app.rpa.query_sku_status.get_update_price_runner", lambda force_failure=False: _Runner())
    out, err = run_query_sku_status_real_admin_readonly(task_id="TASK-Q-2", trace_id="t", sku="A001")
    assert out is None
    assert err is not None
    assert err["error_code"] == "rpa_real_admin_detail_selector_missing"


def test_confirm_rpa_real_admin_readonly_contract_uses_shared_taxonomy(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "RPA_RUNNER_TYPE", "browser_real")
    monkeypatch.setattr(settings, "RPA_TARGET_PROFILE", "real_admin_prepared")
    monkeypatch.setattr(settings, "RPA_EVIDENCE_BASE_DIR", str(tmp_path / "ev"))
    monkeypatch.setattr("app.rpa.confirm_update_price.log_step", lambda *a, **k: None)

    class _Runner:
        runner_name = "browser_real"
        rpa_backend_obs_id = "rpa_browser_real"

        def run(self, inp):
            return RpaExecutionOutput(
                success=True,
                result_summary="readonly ok",
                parsed_result={
                    "sku": "A001",
                    "product_name": "Mirror Name",
                    "page_current_price": 59.9,
                    "page_status": "loaded",
                    "page_message": "real_admin_readback_ok",
                    "target_sku_hit": True,
                    "detail_loaded": True,
                    "profile": "real_admin_prepared",
                    "read_source": "browser_real",
                    "evidence_count": 3,
                    "platform": "woo",
                },
                evidence_paths=["00_context_prepared.png", "01_home_loaded.png", "03_detail_readback.png"],
                error_code=None,
                error_message=None,
            )

    monkeypatch.setattr("app.rpa.confirm_update_price.get_update_price_runner", lambda force_failure=None: _Runner())
    legacy, err = run_confirm_update_price_rpa(
        confirm_task_id="TASK-C-RPA-1",
        trace_id="t",
        sku="A001",
        target_price=39.9,
        platform="woo",
    )
    assert err is None
    assert legacy is not None
    for key in (
        "sku",
        "product_name",
        "page_current_price",
        "page_status",
        "page_message",
        "target_sku_hit",
        "detail_loaded",
        "profile",
        "read_source",
        "evidence_count",
        "verify_passed",
        "verify_reason",
        "verify_error_code",
        "expected_target_price",
        "compared_price",
        "api_price_after_update",
    ):
        assert key in legacy
    assert legacy["verify_passed"] is True


def test_confirm_rpa_real_admin_readonly_failure_taxonomy_passthrough(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "RPA_RUNNER_TYPE", "browser_real")
    monkeypatch.setattr(settings, "RPA_TARGET_PROFILE", "real_admin_prepared")
    monkeypatch.setattr(settings, "RPA_EVIDENCE_BASE_DIR", str(tmp_path / "ev"))
    monkeypatch.setattr("app.rpa.confirm_update_price.log_step", lambda *a, **k: None)

    class _Runner:
        runner_name = "browser_real"
        rpa_backend_obs_id = "rpa_browser_real"

        def run(self, inp):
            return RpaExecutionOutput(
                success=False,
                result_summary="detail selector missing",
                parsed_result={"detail_loaded": True},
                evidence_paths=["99_failure.png"],
                error_code="rpa_real_admin_detail_selector_missing",
                error_message="selector missing",
            )

    monkeypatch.setattr("app.rpa.confirm_update_price.get_update_price_runner", lambda force_failure=None: _Runner())
    legacy, err = run_confirm_update_price_rpa(
        confirm_task_id="TASK-C-RPA-2",
        trace_id="t",
        sku="A001",
        target_price=39.9,
        platform="woo",
    )
    assert legacy is None
    assert err is not None
    assert err["error_code"] == "rpa_real_admin_detail_selector_missing"


def test_api_then_rpa_verify_real_admin_prepared_explicitly_restricted(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "RPA_TARGET_PROFILE", "real_admin_prepared")
    monkeypatch.setattr(settings, "RPA_EVIDENCE_BASE_DIR", str(tmp_path / "ev"))
    monkeypatch.setattr("app.rpa.confirm_update_price.log_step", lambda *a, **k: None)

    legacy, err = run_confirm_update_price_api_then_rpa_verify(
        confirm_task_id="TASK-AV-RESTRICT",
        trace_id="t",
        sku="A001",
        target_price=39.9,
        platform="woo",
    )
    assert legacy is None
    assert err is not None
    assert err["error_code"] == ERROR_API_THEN_RPA_VERIFY_PROFILE_NOT_SUPPORTED
    assert err["_rpa_meta"]["rpa_verification_skipped"] is True


def test_real_admin_write_failure_save_button_disabled(monkeypatch, tmp_path):
    """
    P4.5 representative failure:
    - real_admin_prepared write flow hits disabled save button
    - returns stable taxonomy error_code
    """
    if not _HAS_PLAYWRIGHT:
        pytest.skip("playwright not installed in this environment")
    from app.rpa.browser_playwright_runner import PlaywrightUpdatePriceRunner

    monkeypatch.setattr(settings, "RPA_TARGET_PROFILE", "real_admin_prepared")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_BASE_URL", "https://example.com")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_HOME_PATH", "/h")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_CATALOG_PATH", "/c")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_DETAIL_PATH_TEMPLATE", "/d/{sku}")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_SKU_SEARCH_PARAM", "sku")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_DETAIL_PRICE_SELECTOR", "[data-testid='real-admin-current-price']")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_CATALOG_EMPTY_SELECTOR", "[data-testid='real-admin-catalog-empty']")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_DETAIL_NEW_PRICE_SELECTOR", "[data-testid='real-admin-new-price']")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_DETAIL_SAVE_BUTTON_SELECTOR", "[data-testid='real-admin-save-btn']")
    monkeypatch.setattr(settings, "RPA_REAL_ADMIN_DETAIL_SAVE_RESULT_SELECTOR", "[data-testid='real-admin-save-result']")
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
    mock_page.screenshot = MagicMock(return_value=None)

    def make_loc(*, enabled=True, visible=True, text=""):
        loc = MagicMock()
        loc.first = loc
        loc.wait_for = MagicMock(return_value=None if visible else RuntimeError("hidden"))
        loc.is_visible = MagicMock(return_value=visible)
        loc.is_enabled = MagicMock(return_value=enabled)
        loc.inner_text = MagicMock(return_value=text)
        loc.input_value = MagicMock(return_value=text)
        loc.fill = MagicMock(return_value=None)
        loc.click = MagicMock(return_value=None)
        loc.get_attribute = MagicMock(return_value="")
        return loc

    # Map selectors to locators.
    price_loc = make_loc(text="59.90")
    empty_loc = make_loc(visible=False)
    input_loc = make_loc()
    save_btn_loc = make_loc(enabled=False)  # disabled
    save_res_loc = make_loc(visible=False)

    def locator(sel):
        if "current-price" in sel or "PRICE" in sel or "real-admin-current-price" in sel:
            return price_loc
        if "catalog-empty" in sel:
            return empty_loc
        if "new-price" in sel:
            return input_loc
        if "save-btn" in sel:
            return save_btn_loc
        if "save-result" in sel:
            return save_res_loc
        return make_loc()

    mock_page.locator = MagicMock(side_effect=locator)

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
                params={"sku": "A001", "target_price": 39.9, "current_price": 59.9},
                timeout_s=30,
                evidence_dir=str(ev),
                verify_mode="basic",
                dry_run=False,
            )
        )
    assert out.success is False
    assert out.error_code == ERROR_DETAIL_SAVE_BUTTON_DISABLED


def test_execute_task_confirmation_confirm_target_invalid_has_stable_parsed_result():
    state = {"task_id": "TASK-CFM-INVALID"}
    slots = {}
    out = execute_action.execute_task_confirmation(executor=None, state=state, slots=slots)
    assert out["error_code"] == "confirm_target_invalid"
    pr = out.get("parsed_result") or {}
    for key in (
        "old_price",
        "new_price",
        "post_save_price",
        "verify_passed",
        "verify_reason",
        "operation_result",
        "failure_layer",
    ):
        assert key in pr
    assert pr["failure_layer"] == "confirm_target_invalid"
    assert "target_task_id" in pr
    assert "original_update_task_id" in pr
    assert "operation_result" in pr
    assert "verify_passed" in pr
    assert "verify_reason" in pr


def test_execute_task_confirmation_repeated_confirm_blocked_by_single_status_source(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    db = Session()
    try:
        update_task_id = "TASK-UP-ONE"
        confirm_task_1 = "TASK-CFM-ONE"
        confirm_task_2 = "TASK-CFM-TWO"
        summary = (
            "[product.update_price] ⚠️ 检测到高风险操作：修改价格\n"
            "SKU: A001\n当前价格：59.9\n目标价格：39.9\n任务号：TASK-UP-ONE"
        )
        db.add(
            TaskRecord(
                task_id=update_task_id,
                source_platform="feishu",
                status="awaiting_confirmation",
                intent_text="修改 SKU A001 价格到 39.9",
                result_summary=summary,
                created_at=get_shanghai_now(),
                updated_at=get_shanghai_now(),
            )
        )
        db.add(
            TaskRecord(
                task_id=confirm_task_1,
                source_platform="feishu",
                status="processing",
                intent_text=f"确认执行 {update_task_id}",
                created_at=get_shanghai_now(),
                updated_at=get_shanghai_now(),
            )
        )
        db.add(
            TaskRecord(
                task_id=confirm_task_2,
                source_platform="feishu",
                status="processing",
                intent_text=f"确认执行 {update_task_id}",
                created_at=get_shanghai_now(),
                updated_at=get_shanghai_now(),
            )
        )
        db.commit()

        monkeypatch.setattr(execute_action, "SessionLocal", lambda: db)
        monkeypatch.setattr(settings, "PRODUCT_UPDATE_PRICE_CONFIRM_EXECUTION_BACKEND", "mock")
        calls = {"count": 0}

        class _FakeExecutor:
            def update_price(self, sku, target_price):
                calls["count"] += 1
                return {
                    "status": "success",
                    "sku": sku,
                    "old_price": 59.9,
                    "new_price": float(target_price),
                    "post_save_price": float(target_price),
                    "platform": "woo",
                }

        first = execute_action.execute_task_confirmation(
            executor=_FakeExecutor(),
            state={"task_id": confirm_task_1},
            slots={"task_id": update_task_id},
        )
        assert first.get("status") == "success"
        assert calls["count"] == 1

        second = execute_action.execute_task_confirmation(
            executor=_FakeExecutor(),
            state={"task_id": confirm_task_2},
            slots={"task_id": update_task_id},
        )
        assert second["error_code"] == "confirm_target_already_consumed"
        assert calls["count"] == 1
        pr = second.get("parsed_result") or {}
        assert pr["failure_layer"] == "confirm_target_already_consumed"
        assert pr["target_task_id"] == update_task_id
        assert pr["original_update_task_id"] == update_task_id
        assert pr["operation_result"] == "confirm_blocked_noop"
        assert pr["verify_passed"] is False
        assert "already_consumed_status=" in str(pr["verify_reason"])
    finally:
        db.close()
