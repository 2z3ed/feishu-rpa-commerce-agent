"""Woo read-only production prep config (no real network probe/call)."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from app.core.config import settings

SUPPORTED_WOO_AUTH_MODES = {"token_header", "query_key_secret"}


@dataclass(frozen=True)
class WooReadonlyPrep:
    base_url: str
    api_version_prefix: str
    auth_mode: str
    timeout_ms: int
    allow_internal_sandbox_fallback: bool
    required_config_keys: tuple[str, ...]
    missing_config_keys: list[str]
    production_config_ready: bool
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


def _required_keys_by_auth_mode(auth_mode: str) -> tuple[str, ...]:
    if auth_mode == "query_key_secret":
        return ("WOO_API_KEY", "WOO_API_SECRET")
    return ("WOO_API_TOKEN",)


def _get_setting_value(key: str) -> str:
    return str(getattr(settings, key, "") or "").strip()


def evaluate_woo_readonly_prep() -> WooReadonlyPrep:
    auth_mode = (settings.WOO_AUTH_MODE or "token_header").lower().strip()
    base_url = (settings.WOO_BASE_URL or "").strip()
    api_version_prefix = (settings.WOO_API_VERSION_PREFIX or "wp-json/wc/v3").strip().strip("/")
    timeout_ms = int(settings.WOO_READONLY_TIMEOUT_MS)
    allow_internal_sandbox_fallback = bool(settings.WOO_ALLOW_INTERNAL_SANDBOX_FALLBACK)

    if auth_mode not in SUPPORTED_WOO_AUTH_MODES:
        return WooReadonlyPrep(
            base_url=base_url,
            api_version_prefix=api_version_prefix,
            auth_mode=auth_mode,
            timeout_ms=timeout_ms,
            allow_internal_sandbox_fallback=allow_internal_sandbox_fallback,
            required_config_keys=tuple(),
            missing_config_keys=[],
            production_config_ready=False,
            reason="invalid_auth_mode",
        )

    required_keys = _required_keys_by_auth_mode(auth_mode)
    missing = [key for key in required_keys if not _get_setting_value(key)]

    if not base_url:
        return WooReadonlyPrep(
            base_url=base_url,
            api_version_prefix=api_version_prefix,
            auth_mode=auth_mode,
            timeout_ms=timeout_ms,
            allow_internal_sandbox_fallback=allow_internal_sandbox_fallback,
            required_config_keys=required_keys,
            missing_config_keys=["WOO_BASE_URL", *missing],
            production_config_ready=False,
            reason="missing_base_url",
        )
    if not (base_url.startswith("http://") or base_url.startswith("https://")):
        return WooReadonlyPrep(
            base_url=base_url,
            api_version_prefix=api_version_prefix,
            auth_mode=auth_mode,
            timeout_ms=timeout_ms,
            allow_internal_sandbox_fallback=allow_internal_sandbox_fallback,
            required_config_keys=required_keys,
            missing_config_keys=missing,
            production_config_ready=False,
            reason="invalid_base_url_shape",
        )
    if timeout_ms <= 0:
        return WooReadonlyPrep(
            base_url=base_url,
            api_version_prefix=api_version_prefix,
            auth_mode=auth_mode,
            timeout_ms=timeout_ms,
            allow_internal_sandbox_fallback=allow_internal_sandbox_fallback,
            required_config_keys=required_keys,
            missing_config_keys=missing,
            production_config_ready=False,
            reason="invalid_timeout",
        )
    if not api_version_prefix:
        return WooReadonlyPrep(
            base_url=base_url,
            api_version_prefix=api_version_prefix,
            auth_mode=auth_mode,
            timeout_ms=timeout_ms,
            allow_internal_sandbox_fallback=allow_internal_sandbox_fallback,
            required_config_keys=required_keys,
            missing_config_keys=missing,
            production_config_ready=False,
            reason="missing_api_version_prefix",
        )
    if missing:
        return WooReadonlyPrep(
            base_url=base_url,
            api_version_prefix=api_version_prefix,
            auth_mode=auth_mode,
            timeout_ms=timeout_ms,
            allow_internal_sandbox_fallback=allow_internal_sandbox_fallback,
            required_config_keys=required_keys,
            missing_config_keys=missing,
            production_config_ready=False,
            reason="missing_auth_config",
        )
    return WooReadonlyPrep(
        base_url=base_url,
        api_version_prefix=api_version_prefix,
        auth_mode=auth_mode,
        timeout_ms=timeout_ms,
        allow_internal_sandbox_fallback=allow_internal_sandbox_fallback,
        required_config_keys=required_keys,
        missing_config_keys=[],
        production_config_ready=True,
        reason="ready",
    )


def select_woo_query_backend(
    execution_mode: str,
    platform: str,
) -> tuple[str, bool, str]:
    """Select query backend for Woo api path.

    Returns: (selected_backend, dry_run_enabled, reason)
    """
    dry_run_enabled = bool(settings.WOO_ENABLE_READONLY_DRY_RUN)
    mode = (execution_mode or "").lower().strip()
    platform_key = (platform or "").lower().strip()
    if mode != "api":
        return "sandbox_http_client", dry_run_enabled, "execution_mode_not_api"
    if platform_key != "woo":
        return "sandbox_http_client", dry_run_enabled, "platform_not_woo"
    if not dry_run_enabled:
        return "sandbox_http_client", dry_run_enabled, "dry_run_disabled"

    prep = evaluate_woo_readonly_prep()
    if not prep.production_config_ready:
        return "sandbox_http_client", dry_run_enabled, f"dry_run_config_not_ready:{prep.reason}"
    return "woo_http_dry_run_client", dry_run_enabled, "dry_run_selected"


def get_woo_dry_run_strategy(execution_mode: str, platform: str) -> dict[str, str | bool]:
    selected_backend, dry_run_enabled, reason = select_woo_query_backend(execution_mode, platform)
    fallback_enabled = bool(settings.WOO_ENABLE_READONLY_DRY_RUN_FALLBACK)
    fallback_target = "sandbox_http_client"
    if selected_backend == "woo_http_dry_run_client":
        effective_strategy = "dry_run_with_fallback" if fallback_enabled else "strict_dry_run"
    else:
        effective_strategy = "sandbox_only"
    return {
        "dry_run_enabled": dry_run_enabled,
        "selected_backend": selected_backend,
        "backend_selection_reason": reason,
        "fallback_enabled": fallback_enabled,
        "fallback_target": fallback_target,
        "effective_backend_strategy": effective_strategy,
    }


def get_woo_rollout_policy(execution_mode: str, platform: str) -> dict[str, str | bool]:
    """Centralized Woo readonly rollout policy expression."""
    strategy = get_woo_dry_run_strategy(execution_mode, platform)
    recommended_strategy = "dry_run_with_fallback"
    effective_strategy = str(strategy["effective_backend_strategy"])
    deviation = effective_strategy != recommended_strategy
    if deviation:
        if effective_strategy == "strict_dry_run":
            reason = "fallback_disabled_in_strict_dry_run"
        elif effective_strategy == "sandbox_only":
            reason = "dry_run_not_effective"
        else:
            reason = "strategy_not_recommended"
    else:
        reason = "recommended_strategy_applied"
    return {
        **strategy,
        "recommended_strategy": recommended_strategy,
        "strategy_deviation": deviation,
        "recommended_strategy_reason": reason,
    }
