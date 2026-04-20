#!/usr/bin/env python3
"""Page executor baseline (shim), NOT Yingdao runtime.

This script executes real page automation against self-hosted nonprod page via Playwright,
but it does not start/call Yingdao runtime itself. It keeps P90 inbox/outbox contract.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

INBOX_DIR = Path("tmp/yingdao_bridge/inbox")
OUTBOX_DIR = Path("tmp/yingdao_bridge/outbox")


def _load_input(fp: Path) -> dict[str, Any]:
    return json.loads(fp.read_text(encoding="utf-8") or "{}")


def _write_output(run_id: str, result: dict[str, Any]) -> Path:
    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    out_fp = OUTBOX_DIR / f"{run_id}.output.json"
    out_fp.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out_fp


def _origin(url: str) -> str:
    p = urlparse(url)
    return urlunparse((p.scheme, p.netloc, "", "", "", ""))


def _parse_inventory(html: str) -> int | None:
    m = re.search(r"Current Inventory</th><td>(\d+)</td>", html)
    if m:
        return int(m.group(1))
    m2 = re.search(r"写后库存:\s*(\d+)", html)
    if m2:
        return int(m2.group(1))
    return None


def _base_result(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": str(payload.get("run_id") or ""),
        "operation_result": "write_adjust_inventory_bridge_failed",
        "verify_passed": False,
        "verify_reason": "",
        "page_failure_code": "",
        "failure_layer": "",
        "page_steps": [],
        "page_evidence_count": 0,
        "old_inventory": int(payload.get("old_inventory") or 0),
        "new_inventory": int(payload.get("old_inventory") or 0),
        "screenshot_paths": [],
    }


def process_one(input_fp: Path) -> Path:
    payload = _load_input(input_fp)
    run_id = str(payload.get("run_id") or input_fp.stem.replace(".input", ""))
    entry_url = str(payload.get("entry_url") or "http://127.0.0.1:18081/login")
    login_url = str(payload.get("login_url") or entry_url)
    sku = str(payload.get("sku") or "A001").strip().upper()
    delta = int(payload.get("delta") or 0)
    target_inventory = int(payload.get("target_inventory") or 0)
    fail_mode = str(payload.get("fail_mode") or "").strip().lower()
    evidence_dir = Path(str(payload.get("evidence_dir") or "tmp/evidence"))
    evidence_dir.mkdir(parents=True, exist_ok=True)

    result = _base_result(payload)
    result["run_id"] = run_id
    steps: list[str] = []
    shots: list[str] = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            # open_entry
            steps.append("open_entry")
            page.goto(entry_url, wait_until="domcontentloaded", timeout=15000)

            # ensure_session
            steps.append("ensure_session")
            page.fill('input[name="username"]', "admin")
            page.fill('input[name="password"]', "badpass" if fail_mode == "session_invalid" else "admin123")
            page.click('button[type="submit"]')
            page.wait_for_load_state("domcontentloaded")
            if fail_mode == "session_invalid" or "登录失败" in page.content():
                shot = evidence_dir / f"{run_id}-session-invalid.png"
                page.screenshot(path=str(shot), full_page=True)
                shots.append(str(shot))
                result.update(
                    {
                        "operation_result": "write_adjust_inventory_bridge_failed",
                        "verify_passed": False,
                        "verify_reason": "session_invalid",
                        "page_failure_code": "SESSION_INVALID",
                        "failure_layer": "config",
                        "page_steps": steps,
                        "page_evidence_count": len(shots),
                        "screenshot_paths": shots,
                    }
                )
                browser.close()
                return _write_output(run_id, result)

            base = _origin(login_url)

            # search_sku
            steps.append("search_sku")
            inv_url = f"{base}/admin/inventory?sku={sku}"
            page.goto(inv_url, wait_until="domcontentloaded", timeout=15000)
            html = page.content()
            if fail_mode == "entry_not_ready" or "入口未就绪" in html:
                shot = evidence_dir / f"{run_id}-entry-not-ready.png"
                page.screenshot(path=str(shot), full_page=True)
                shots.append(str(shot))
                result.update(
                    {
                        "operation_result": "write_adjust_inventory_bridge_failed",
                        "verify_passed": False,
                        "verify_reason": "entry_not_ready",
                        "page_failure_code": "ENTRY_NOT_READY",
                        "failure_layer": "page",
                        "page_steps": steps,
                        "page_evidence_count": len(shots),
                        "screenshot_paths": shots,
                    }
                )
                browser.close()
                return _write_output(run_id, result)

            old_inventory = _parse_inventory(html)
            if old_inventory is None:
                old_inventory = int(payload.get("old_inventory") or 100)

            # open_editor
            steps.append("open_editor")
            page.goto(f"{base}/admin/inventory/adjust?sku={sku}", wait_until="domcontentloaded", timeout=15000)

            # input_inventory + submit_change
            new_inventory = target_inventory if target_inventory else old_inventory + delta
            steps.append("input_inventory")
            page.fill('input[name="target_inventory"]', str(new_inventory))
            steps.append("submit_change")
            page.click('button[type="submit"]')
            page.wait_for_load_state("domcontentloaded")

            # read_feedback
            steps.append("read_feedback")
            submit_html = page.content()
            success = "提交成功" in submit_html or "msg-ok" in submit_html

            # verify_result
            steps.append("verify_result")
            page.goto(inv_url, wait_until="domcontentloaded", timeout=15000)
            verify_html = page.content()
            after_inventory = _parse_inventory(verify_html)
            verify_passed = bool(success and after_inventory is not None and after_inventory == new_inventory)

            shot = evidence_dir / f"{run_id}-final.png"
            page.screenshot(path=str(shot), full_page=True)
            shots.append(str(shot))

            result.update(
                {
                    "operation_result": "write_adjust_inventory" if verify_passed else "write_adjust_inventory_verify_failed",
                    "verify_passed": verify_passed,
                    "verify_reason": "" if verify_passed else "verify_fail",
                    "page_failure_code": "" if verify_passed else "VERIFY_FAIL",
                    "failure_layer": "" if verify_passed else "verify_failed",
                    "page_steps": steps,
                    "page_evidence_count": len(shots),
                    "old_inventory": old_inventory,
                    "new_inventory": int(after_inventory if after_inventory is not None else new_inventory),
                    "screenshot_paths": shots,
                }
            )
            browser.close()
    except PlaywrightTimeoutError:
        result.update(
            {
                "operation_result": "write_adjust_inventory_bridge_timeout",
                "verify_passed": False,
                "verify_reason": "bridge_request_timeout",
                "page_failure_code": "PAGE_TIMEOUT",
                "failure_layer": "bridge_timeout",
                "page_steps": steps,
                "page_evidence_count": len(shots),
                "screenshot_paths": shots,
            }
        )
    except Exception as exc:
        result.update(
            {
                "operation_result": "write_adjust_inventory_bridge_failed",
                "verify_passed": False,
                "verify_reason": f"executor_error:{type(exc).__name__}",
                "page_failure_code": "EXECUTOR_ERROR",
                "failure_layer": "bridge_executor_failed",
                "page_steps": steps,
                "page_evidence_count": len(shots),
                "screenshot_paths": shots,
            }
        )

    return _write_output(run_id, result)


def main() -> int:
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    processed = 0
    for fp in sorted(INBOX_DIR.glob("*.input.json")):
        process_one(fp)
        processed += 1
    print(f"processed={processed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
