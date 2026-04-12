"""
Playwright-based RPA runner for product.update_price against internal pages only (not production).

Requires: pip install playwright && playwright install chromium

Targets:
- sandbox: /internal/rpa-sandbox/update-price (minimal)
- admin_like: hub /internal/rpa-sandbox/admin-like → workbench /admin-like/update-price
"""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlencode

from app.core.config import settings
from app.core.logging import logger
from app.rpa.schema import RpaExecutionInput, RpaExecutionOutput, RpaRunner

_ADMIN_FAILURE_MODES = frozenset({"none", "sku_missing", "save_error", "save_disabled"})


def _screenshot(page, path: Path) -> str | None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(path), full_page=True)
        return str(path.resolve())
    except OSError as exc:
        logger.warning("RPA screenshot failed: %s", exc)
        return None


def _norm_admin_failure_mode(raw: str) -> str:
    v = (raw or "none").lower().strip()
    return v if v in _ADMIN_FAILURE_MODES else "none"


def _base_sandbox() -> str:
    return (settings.RPA_SANDBOX_BASE_URL or "http://127.0.0.1:8000").rstrip("/")


def _base_admin_like() -> str:
    alt = (settings.RPA_ADMIN_LIKE_BASE_URL or "").strip()
    return alt.rstrip("/") if alt else _base_sandbox()


class PlaywrightUpdatePriceRunner(RpaRunner):
    """Opens internal pages in Chromium; real screenshots; obeys RpaExecutionOutput contract."""

    rpa_backend_obs_id = "rpa_browser_real"

    def __init__(self, *, runner_name: str = "browser_real", force_failure: bool = False):
        self.runner_name = runner_name
        self.force_failure = force_failure

    def run(self, inp: RpaExecutionInput) -> RpaExecutionOutput:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return RpaExecutionOutput(
                success=False,
                result_summary="playwright package not installed",
                parsed_result={},
                evidence_paths=[],
                error_code="playwright_import_error",
                error_message="Install playwright and run: playwright install chromium",
            )

        evidence_dir = Path(inp.evidence_dir)
        paths: list[str] = []
        sku = (inp.params.get("sku") or "").strip().upper()
        target_price = inp.params.get("target_price")
        current_price = inp.params.get("current_price")

        meta_path = evidence_dir / "run_input.json"
        try:
            evidence_dir.mkdir(parents=True, exist_ok=True)
            meta_path.write_text(
                json.dumps(inp.model_dump(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            paths.append(str(meta_path.resolve()))
        except OSError as exc:
            logger.warning("RPA metadata write skipped: %s", exc)

        if not sku:
            _tiny_failure_png(evidence_dir, paths)
            return RpaExecutionOutput(
                success=False,
                result_summary="missing sku",
                parsed_result={},
                evidence_paths=paths,
                error_code="rpa_invalid_params",
                error_message="params.sku is required",
            )

        try:
            cp = float(current_price) if current_price is not None else 0.0
        except (TypeError, ValueError):
            cp = 0.0
        try:
            tp = float(target_price) if target_price is not None else 0.0
        except (TypeError, ValueError):
            tp = 0.0

        timeout_ms = max(1000, int((settings.RPA_BROWSER_TIMEOUT_S or 30) * 1000))
        target_env = (settings.RPA_TARGET_ENV or "sandbox").lower().strip()

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=bool(settings.RPA_BROWSER_HEADLESS))
                try:
                    context = browser.new_context()
                    page = context.new_page()
                    page.set_default_timeout(timeout_ms)
                    if target_env == "admin_like":
                        return self._flow_admin_like(page, evidence_dir, paths, inp, sku, tp, cp)
                    return self._flow_sandbox(
                        page, evidence_dir, paths, inp, sku, tp, cp
                    )
                finally:
                    browser.close()
        except Exception as exc:
            logger.exception("Playwright RPA runner failed")
            return RpaExecutionOutput(
                success=False,
                result_summary=str(exc),
                parsed_result={"sku": sku, "target_price": target_price},
                evidence_paths=paths,
                error_code="rpa_browser_exception",
                error_message=str(exc),
            )

    def _flow_sandbox(
        self,
        page,
        evidence_dir: Path,
        paths: list[str],
        inp: RpaExecutionInput,
        sku: str,
        tp: float,
        cp: float,
    ) -> RpaExecutionOutput:
        base = _base_sandbox()
        ff = 1 if (self.force_failure or settings.RPA_BROWSER_FORCE_FAILURE) else 0
        q = urlencode(
            {
                "sku": sku,
                "current_price": f"{cp:.4f}",
                "target_price": f"{tp:.4f}",
                "force_fail": str(ff),
            }
        )
        url = f"{base}/api/v1/internal/rpa-sandbox/update-price?{q}"
        page.goto(url, wait_until="domcontentloaded")

        p1 = _screenshot(page, evidence_dir / "01_enter_target.png")
        if p1:
            paths.append(p1)

        page.fill("#target-price", str(tp))
        p2 = _screenshot(page, evidence_dir / "02_before_action.png")
        if p2:
            paths.append(p2)

        page.click("#submit-btn")
        page.wait_for_selector("#result[data-status='success'], #result[data-status='error']")

        loc = page.locator("#result")
        status = loc.get_attribute("data-status") or ""
        text = (loc.inner_text() or "").strip()

        if status == "error":
            p3 = _screenshot(page, evidence_dir / "99_failure.png")
            if p3:
                paths.append(p3)
            return RpaExecutionOutput(
                success=False,
                result_summary=text or "sandbox reported error",
                parsed_result={
                    "sku": sku,
                    "target_price": tp,
                    "platform": inp.platform,
                    "dry_run": inp.dry_run,
                },
                evidence_paths=paths,
                error_code="rpa_browser_sandbox_error",
                error_message=text or "Browser sandbox returned error",
            )

        p3 = _screenshot(page, evidence_dir / "03_after_action.png")
        if p3:
            paths.append(p3)

        new_p = loc.get_attribute("data-new-price")
        old_p = loc.get_attribute("data-old-price")
        try:
            new_f = float(new_p) if new_p is not None else tp
        except (TypeError, ValueError):
            new_f = tp
        try:
            old_f = float(old_p) if old_p is not None else cp
        except (TypeError, ValueError):
            old_f = cp

        return RpaExecutionOutput(
            success=True,
            result_summary=f"Playwright sandbox OK: {sku} {old_f} -> {new_f}",
            parsed_result={
                "sku": sku,
                "target_price": new_f,
                "old_price": old_f,
                "platform": inp.platform,
                "dry_run": inp.dry_run,
                "verify_mode": inp.verify_mode,
            },
            evidence_paths=paths,
            error_code=None,
            error_message=None,
        )

    def _flow_admin_like(
        self,
        page,
        evidence_dir: Path,
        paths: list[str],
        inp: RpaExecutionInput,
        sku: str,
        tp: float,
        cp: float,
    ) -> RpaExecutionOutput:
        base = _base_admin_like()
        fm = _norm_admin_failure_mode(settings.RPA_ADMIN_LIKE_FORCE_FAILURE_MODE)
        q = urlencode(
            {
                "sku": sku,
                "current_price": f"{cp:.4f}",
                "target_price": f"{tp:.4f}",
                "failure_mode": fm,
            }
        )
        hub = f"{base}/api/v1/internal/rpa-sandbox/admin-like?{q}"
        page.goto(hub, wait_until="domcontentloaded")
        p1 = _screenshot(page, evidence_dir / "01_enter_backend.png")
        if p1:
            paths.append(p1)

        page.click('[data-testid="nav-to-update-price"]')
        page.wait_for_selector('[data-testid="admin-update-root"]')
        p2 = _screenshot(page, evidence_dir / "02_after_navigation.png")
        if p2:
            paths.append(p2)

        page.locator("#sku-search").fill(sku)
        page.click('[data-testid="locate-sku"]')

        if fm == "sku_missing":
            page.wait_for_selector('#global-error[data-status="error"]')
            gtxt = (page.locator("#global-error").inner_text() or "").strip()
            p99 = _screenshot(page, evidence_dir / "99_failure.png")
            if p99:
                paths.append(p99)
            return RpaExecutionOutput(
                success=False,
                result_summary=gtxt or "sku_missing",
                parsed_result={"sku": sku, "target_price": tp, "platform": inp.platform, "dry_run": inp.dry_run},
                evidence_paths=paths,
                error_code="rpa_admin_sku_missing",
                error_message=gtxt or "商品未找到（受控 sku_missing）",
            )

        page.wait_for_selector('#product-card[data-visible="1"]')
        p3 = _screenshot(page, evidence_dir / "03_product_located.png")
        if p3:
            paths.append(p3)

        page.locator("#new-price").fill(str(tp))
        p4 = _screenshot(page, evidence_dir / "04_before_save.png")
        if p4:
            paths.append(p4)

        save_btn = page.locator("#save-price")
        if fm == "save_disabled":
            p99 = _screenshot(page, evidence_dir / "99_failure.png")
            if p99:
                paths.append(p99)
            return RpaExecutionOutput(
                success=False,
                result_summary="保存按钮不可用（save_disabled）",
                parsed_result={"sku": sku, "target_price": tp, "platform": inp.platform, "dry_run": inp.dry_run},
                evidence_paths=paths,
                error_code="rpa_admin_save_disabled",
                error_message="保存按钮不可用（受控 save_disabled）",
            )

        save_btn.click()
        page.wait_for_selector("#result[data-status='success'], #result[data-status='error']")
        loc = page.locator("#result")
        status = loc.get_attribute("data-status") or ""
        text = (loc.inner_text() or "").strip()

        if status == "error":
            p99 = _screenshot(page, evidence_dir / "99_failure.png")
            if p99:
                paths.append(p99)
            return RpaExecutionOutput(
                success=False,
                result_summary=text or "save failed",
                parsed_result={"sku": sku, "target_price": tp, "platform": inp.platform, "dry_run": inp.dry_run},
                evidence_paths=paths,
                error_code="rpa_admin_save_error",
                error_message=text or "保存失败（受控 save_error）",
            )

        p5 = _screenshot(page, evidence_dir / "05_after_save.png")
        if p5:
            paths.append(p5)

        new_p = loc.get_attribute("data-new-price")
        old_p = loc.get_attribute("data-old-price")
        try:
            new_f = float(new_p) if new_p is not None else tp
        except (TypeError, ValueError):
            new_f = tp
        try:
            old_f = float(old_p) if old_p is not None else cp
        except (TypeError, ValueError):
            old_f = cp

        return RpaExecutionOutput(
            success=True,
            result_summary=f"Playwright admin_like OK: {sku} {old_f} -> {new_f}",
            parsed_result={
                "sku": sku,
                "target_price": new_f,
                "old_price": old_f,
                "platform": inp.platform,
                "dry_run": inp.dry_run,
                "verify_mode": inp.verify_mode,
            },
            evidence_paths=paths,
            error_code=None,
            error_message=None,
        )


def _tiny_failure_png(evidence_dir: Path, paths: list[str]) -> None:
    p = evidence_dir / "99_failure.png"
    try:
        p.write_bytes(
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb"
            b"\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        paths.append(str(p.resolve()))
    except OSError:
        pass
