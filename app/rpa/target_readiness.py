"""P4.1 — RPA target profile + readiness (config / session) before real admin navigation exists."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from app.core.config import Settings
from app.core.logging import logger

_VALID_PROFILES = frozenset({"internal_controlled", "real_admin_prepared"})


def norm_rpa_target_profile(raw: str | None) -> str:
    v = (raw or "internal_controlled").lower().strip()
    if v not in _VALID_PROFILES:
        logger.warning("Unknown RPA_TARGET_PROFILE=%r, using internal_controlled", raw)
        return "internal_controlled"
    return v


def _parse_headers_json(blob: str) -> dict[str, str]:
    b = (blob or "").strip()
    if not b:
        return {}
    try:
        data = json.loads(b)
    except json.JSONDecodeError:
        logger.warning("Invalid JSON for RPA session/extra headers")
        return {}
    if not isinstance(data, dict):
        return {}
    out: dict[str, str] = {}
    for k, v in data.items():
        out[str(k)] = str(v)
    return out


def _has_real_admin_session(settings: Settings) -> bool:
    if (settings.RPA_REAL_ADMIN_SESSION_COOKIE or "").strip():
        return True
    h = _parse_headers_json(settings.RPA_REAL_ADMIN_SESSION_HEADERS_JSON)
    return len(h) > 0


@dataclass
class RpaTargetReadinessResult:
    ready: bool
    profile: str
    browser_real_allowed: bool
    missing_config_fields: list[str] = field(default_factory=list)
    missing_session: bool = False
    not_ready_reason: str = ""
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rpa_target_profile": self.profile,
            "ready": self.ready,
            "browser_real_allowed": self.browser_real_allowed,
            "missing_config_fields": list(self.missing_config_fields),
            "missing_session": self.missing_session,
            "not_ready_reason": self.not_ready_reason,
            "notes": list(self.notes),
        }

    def human_error_message(self) -> str:
        if self.ready:
            return ""
        parts = [self.not_ready_reason or "rpa_target_not_ready"]
        if self.missing_config_fields:
            parts.append("缺配置: " + ",".join(self.missing_config_fields))
        if self.missing_session:
            parts.append("缺会话: 请配置 RPA_REAL_ADMIN_SESSION_COOKIE 或 RPA_REAL_ADMIN_SESSION_HEADERS_JSON")
        return "；".join(parts)


def evaluate_rpa_target_readiness(settings: Settings) -> RpaTargetReadinessResult:
    profile = norm_rpa_target_profile(getattr(settings, "RPA_TARGET_PROFILE", None))

    if profile == "internal_controlled":
        return RpaTargetReadinessResult(
            ready=True,
            profile=profile,
            browser_real_allowed=True,
            notes=["internal_controlled: 使用内部受控 sandbox / admin-like / list_detail，不要求真实后台配置"],
        )

    missing: list[str] = []
    base = (settings.RPA_REAL_ADMIN_BASE_URL or "").strip()
    if not base:
        missing.append("RPA_REAL_ADMIN_BASE_URL")
    else:
        p = urlparse(base)
        if p.scheme not in ("http", "https") or not p.netloc:
            missing.append("RPA_REAL_ADMIN_BASE_URL(invalid_url)")

    home = (settings.RPA_REAL_ADMIN_HOME_PATH or "").strip()
    if not home or not home.startswith("/"):
        missing.append("RPA_REAL_ADMIN_HOME_PATH")

    catalog = (settings.RPA_REAL_ADMIN_CATALOG_PATH or "").strip()
    if not catalog or not catalog.startswith("/"):
        missing.append("RPA_REAL_ADMIN_CATALOG_PATH")

    detail_t = (settings.RPA_REAL_ADMIN_DETAIL_PATH_TEMPLATE or "").strip()
    if not detail_t or "{sku}" not in detail_t:
        missing.append("RPA_REAL_ADMIN_DETAIL_PATH_TEMPLATE(must_contain_{sku})")

    sku_param = (settings.RPA_REAL_ADMIN_SKU_SEARCH_PARAM or "").strip()
    if not sku_param:
        missing.append("RPA_REAL_ADMIN_SKU_SEARCH_PARAM")

    price_sel = (settings.RPA_REAL_ADMIN_DETAIL_PRICE_SELECTOR or "").strip()
    if not price_sel:
        missing.append("RPA_REAL_ADMIN_DETAIL_PRICE_SELECTOR")
    empty_sel = (settings.RPA_REAL_ADMIN_CATALOG_EMPTY_SELECTOR or "").strip()
    if not empty_sel:
        missing.append("RPA_REAL_ADMIN_CATALOG_EMPTY_SELECTOR")

    miss_session = False
    if not missing and not _has_real_admin_session(settings):
        miss_session = True

    not_ready_reason = ""
    if missing:
        not_ready_reason = "missing_real_admin_config"
    elif miss_session:
        not_ready_reason = "missing_session"

    ready = not missing and not miss_session

    out_notes: list[str] = []
    if ready and getattr(settings, "RPA_REAL_ADMIN_READINESS_HTTP_PROBE", False):
        try:
            home_url = urljoin(base.rstrip("/") + "/", home)
            timeout = float(getattr(settings, "RPA_REAL_ADMIN_READINESS_PROBE_TIMEOUT_S", 5) or 5)
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                r = client.get(home_url)
            if r.status_code >= 500:
                ready = False
                not_ready_reason = "readiness_http_probe_server_error"
                out_notes.append(f"probe_status={r.status_code}")
        except Exception as exc:
            ready = False
            not_ready_reason = "readiness_http_probe_failed"
            out_notes.append(f"probe_error={exc!r}")

    if ready and not out_notes:
        out_notes = [
            "real_admin_prepared: P4.2 将执行 home→catalog→detail 只读导航与读回（浏览器内不做保存）"
        ]

    return RpaTargetReadinessResult(
        ready=ready,
        profile=profile,
        browser_real_allowed=ready,
        missing_config_fields=missing,
        missing_session=miss_session,
        not_ready_reason=not_ready_reason,
        notes=out_notes,
    )
