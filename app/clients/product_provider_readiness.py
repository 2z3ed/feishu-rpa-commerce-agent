"""Provider preflight/readiness for product.query_sku_status."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from app.clients.product_credential_contract import (
    ProductCredentialInvalidError,
    ProductCredentialMissingError,
    validate_credentials,
)
from app.clients.product_provider_profile import (
    ProductProviderConfigInvalidError,
    ProductProviderUnsupportedError,
    resolve_provider_profile,
    validate_provider_runtime,
)
from app.clients.woo_readonly_prep import (
    evaluate_woo_readonly_prep,
    get_woo_dry_run_strategy,
    get_woo_rollout_policy,
)
from app.core.config import settings


@dataclass
class ProviderReadinessResult:
    provider_name: str
    supported_intents: list[str]
    execution_mode: str
    platform: str
    base_url: str
    timeout_ms: int
    internal_sandbox_enabled: bool
    auth_profile: str
    request_adapter: str
    response_mapper: str
    provider_profile: str
    credential_profile: str
    credential_ready: bool
    sandbox_ready: bool
    production_shape_ready: bool
    production_config_ready: bool
    dry_run_enabled: bool
    selected_backend: str
    backend_selection_reason: str
    fallback_enabled: bool
    fallback_target: str
    effective_backend_strategy: str
    recommended_strategy: str
    strategy_deviation: bool
    recommended_strategy_reason: str
    live_probe_enabled: bool
    woo_readonly_prep: dict
    missing_config_keys: list[str]
    ready: bool
    reason: str
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _normalize_reason(err: Exception) -> str:
    msg = str(err).lower()
    if "unsupported provider" in msg:
        return "provider_unsupported"
    if "timeout must be > 0" in msg:
        return "invalid_timeout"
    if "internal sandbox api disabled" in msg:
        return "internal_sandbox_disabled"
    if "credential_missing" in msg:
        return "credential_missing"
    if "credential_invalid" in msg:
        return "credential_invalid"
    return "provider_config_invalid"


def check_query_provider_readiness(provider: str) -> ProviderReadinessResult:
    mode = (settings.PRODUCT_QUERY_SKU_DEFAULT_EXECUTION_MODE or "mock").lower().strip()
    base_url = settings.PRODUCT_QUERY_SKU_API_BASE_URL or "internal://sandbox"
    timeout_ms = int(settings.PRODUCT_QUERY_SKU_API_TIMEOUT_MS)
    sandbox_enabled = bool(settings.ENABLE_INTERNAL_SANDBOX_API)
    provider_key = (provider or "").lower().strip()
    sandbox_ready = False
    production_shape_ready = False
    production_config_ready = False
    dry_run_enabled = bool(settings.WOO_ENABLE_READONLY_DRY_RUN)
    selected_backend = "sandbox_http_client"
    backend_selection_reason = "default_sandbox"
    fallback_enabled = bool(settings.WOO_ENABLE_READONLY_DRY_RUN_FALLBACK)
    fallback_target = "sandbox_http_client"
    effective_backend_strategy = "sandbox_only"
    recommended_strategy = "dry_run_with_fallback"
    strategy_deviation = True
    recommended_strategy_reason = "non_woo_provider"
    live_probe_enabled = bool(settings.WOO_ENABLE_READONLY_LIVE_PROBE)
    woo_readonly_prep: dict = {}

    try:
        profile = resolve_provider_profile(provider_key)
        validate_provider_runtime(
            profile=profile,
            intent_code="product.query_sku_status",
            base_url=base_url,
            timeout_ms=timeout_ms,
            internal_sandbox_enabled=sandbox_enabled,
        )
        credential_profile, _, missing = validate_credentials(profile.provider_name)
        credential_ready = True
        sandbox_ready = bool(sandbox_enabled and base_url == "internal://sandbox")
        production_shape_ready = bool(
            profile.provider_name == "woo"
            and profile.request_adapter_name == "woo_request_adapter"
            and profile.response_mapper_name == "woo_mapper"
            and profile.auth_profile_name == "woo_auth_profile"
            and credential_profile == "woo_credential_profile"
        )
        if profile.provider_name == "woo":
            prep = evaluate_woo_readonly_prep()
            production_config_ready = prep.production_config_ready
            woo_readonly_prep = prep.to_dict()
            strategy = get_woo_dry_run_strategy(mode, profile.provider_name)
            rollout = get_woo_rollout_policy(mode, profile.provider_name)
            dry_run_enabled = bool(strategy["dry_run_enabled"])
            selected_backend = str(strategy["selected_backend"])
            backend_selection_reason = str(strategy["backend_selection_reason"])
            fallback_enabled = bool(strategy["fallback_enabled"])
            fallback_target = str(strategy["fallback_target"])
            effective_backend_strategy = str(strategy["effective_backend_strategy"])
            recommended_strategy = str(rollout["recommended_strategy"])
            strategy_deviation = bool(rollout["strategy_deviation"])
            recommended_strategy_reason = str(rollout["recommended_strategy_reason"])
    except (ProductProviderUnsupportedError, ProductProviderConfigInvalidError) as exc:
        reason = _normalize_reason(exc)
        return ProviderReadinessResult(
            provider_name=provider_key or "unknown",
            supported_intents=[],
            execution_mode=mode,
            platform=provider_key or "unknown",
            base_url=base_url,
            timeout_ms=timeout_ms,
            internal_sandbox_enabled=sandbox_enabled,
            auth_profile="unknown",
            request_adapter="unknown",
            response_mapper="unknown",
            provider_profile=provider_key or "unknown",
            credential_profile="unknown",
            credential_ready=False,
            sandbox_ready=sandbox_ready,
            production_shape_ready=production_shape_ready,
            production_config_ready=production_config_ready,
            dry_run_enabled=dry_run_enabled,
            selected_backend=selected_backend,
            backend_selection_reason=backend_selection_reason,
            fallback_enabled=fallback_enabled,
            fallback_target=fallback_target,
            effective_backend_strategy=effective_backend_strategy,
            recommended_strategy=recommended_strategy,
            strategy_deviation=strategy_deviation,
            recommended_strategy_reason=recommended_strategy_reason,
            live_probe_enabled=live_probe_enabled,
            woo_readonly_prep=woo_readonly_prep,
            missing_config_keys=[],
            ready=False,
            reason=reason,
            errors=[str(exc)],
        )
    except ProductCredentialMissingError as exc:
        return ProviderReadinessResult(
            provider_name=provider_key or "unknown",
            supported_intents=[],
            execution_mode=mode,
            platform=provider_key or "unknown",
            base_url=base_url,
            timeout_ms=timeout_ms,
            internal_sandbox_enabled=sandbox_enabled,
            auth_profile=profile.auth_profile_name if "profile" in locals() else "unknown",
            request_adapter=profile.request_adapter_name if "profile" in locals() else "unknown",
            response_mapper=profile.response_mapper_name if "profile" in locals() else "unknown",
            provider_profile=provider_key or "unknown",
            credential_profile="unknown",
            credential_ready=False,
            sandbox_ready=sandbox_ready,
            production_shape_ready=production_shape_ready,
            production_config_ready=production_config_ready,
            dry_run_enabled=dry_run_enabled,
            selected_backend=selected_backend,
            backend_selection_reason=backend_selection_reason,
            fallback_enabled=fallback_enabled,
            fallback_target=fallback_target,
            effective_backend_strategy=effective_backend_strategy,
            recommended_strategy=recommended_strategy,
            strategy_deviation=strategy_deviation,
            recommended_strategy_reason=recommended_strategy_reason,
            live_probe_enabled=live_probe_enabled,
            woo_readonly_prep=woo_readonly_prep,
            missing_config_keys=[part for part in str(exc).split("missing=")[-1].split(",") if part and "credential_missing" not in part],
            ready=False,
            reason="credential_missing",
            errors=[str(exc)],
        )
    except ProductCredentialInvalidError as exc:
        return ProviderReadinessResult(
            provider_name=provider_key or "unknown",
            supported_intents=[],
            execution_mode=mode,
            platform=provider_key or "unknown",
            base_url=base_url,
            timeout_ms=timeout_ms,
            internal_sandbox_enabled=sandbox_enabled,
            auth_profile=profile.auth_profile_name if "profile" in locals() else "unknown",
            request_adapter=profile.request_adapter_name if "profile" in locals() else "unknown",
            response_mapper=profile.response_mapper_name if "profile" in locals() else "unknown",
            provider_profile=provider_key or "unknown",
            credential_profile="unknown",
            credential_ready=False,
            sandbox_ready=sandbox_ready,
            production_shape_ready=production_shape_ready,
            production_config_ready=production_config_ready,
            dry_run_enabled=dry_run_enabled,
            selected_backend=selected_backend,
            backend_selection_reason=backend_selection_reason,
            fallback_enabled=fallback_enabled,
            fallback_target=fallback_target,
            effective_backend_strategy=effective_backend_strategy,
            recommended_strategy=recommended_strategy,
            strategy_deviation=strategy_deviation,
            recommended_strategy_reason=recommended_strategy_reason,
            live_probe_enabled=live_probe_enabled,
            woo_readonly_prep=woo_readonly_prep,
            missing_config_keys=[],
            ready=False,
            reason="credential_invalid",
            errors=[str(exc)],
        )

    return ProviderReadinessResult(
        provider_name=profile.provider_name,
        supported_intents=list(profile.supported_intents),
        execution_mode=mode,
        platform=profile.provider_name,
        base_url=base_url,
        timeout_ms=timeout_ms,
        internal_sandbox_enabled=sandbox_enabled,
        auth_profile=profile.auth_profile_name,
        request_adapter=profile.request_adapter_name,
        response_mapper=profile.response_mapper_name,
        provider_profile=profile.provider_name,
        credential_profile=credential_profile,
        credential_ready=credential_ready,
        sandbox_ready=sandbox_ready,
        production_shape_ready=production_shape_ready,
        production_config_ready=production_config_ready,
        dry_run_enabled=dry_run_enabled,
        selected_backend=selected_backend,
        backend_selection_reason=backend_selection_reason,
        fallback_enabled=fallback_enabled,
        fallback_target=fallback_target,
        effective_backend_strategy=effective_backend_strategy,
        recommended_strategy=recommended_strategy,
        strategy_deviation=strategy_deviation,
        recommended_strategy_reason=recommended_strategy_reason,
        live_probe_enabled=live_probe_enabled,
        woo_readonly_prep=woo_readonly_prep,
        missing_config_keys=missing,
        ready=True,
        reason="ready",
        errors=[],
    )
