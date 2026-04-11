"""Provider capability/profile contract for query_sku_status api path."""
from __future__ import annotations

from dataclasses import dataclass


class ProductProviderProfileError(Exception):
    """Base error for provider profile resolution/validation."""


class ProductProviderUnsupportedError(ProductProviderProfileError):
    """Raised when provider is unsupported."""


class ProductProviderConfigInvalidError(ProductProviderProfileError):
    """Raised when provider config is invalid."""


@dataclass(frozen=True)
class ProductProviderProfile:
    provider_name: str
    supported_intents: tuple[str, ...]
    default_base_url: str
    default_timeout_ms: int
    auth_profile_name: str
    request_adapter_name: str
    response_mapper_name: str
    supports_internal_sandbox_route: bool


_PROFILES: dict[str, ProductProviderProfile] = {
    "sandbox": ProductProviderProfile(
        provider_name="sandbox",
        supported_intents=("product.query_sku_status",),
        default_base_url="internal://sandbox",
        default_timeout_ms=2000,
        auth_profile_name="sandbox_auth_profile",
        request_adapter_name="sandbox_request_adapter",
        response_mapper_name="sandbox_mapper",
        supports_internal_sandbox_route=True,
    ),
    "woo": ProductProviderProfile(
        provider_name="woo",
        supported_intents=("product.query_sku_status",),
        default_base_url="internal://sandbox",
        default_timeout_ms=2000,
        auth_profile_name="woo_auth_profile",
        request_adapter_name="woo_request_adapter",
        response_mapper_name="woo_mapper",
        supports_internal_sandbox_route=True,
    ),
    "odoo": ProductProviderProfile(
        provider_name="odoo",
        supported_intents=("product.query_sku_status",),
        default_base_url="internal://sandbox",
        default_timeout_ms=2000,
        auth_profile_name="odoo_auth_profile",
        request_adapter_name="odoo_request_adapter",
        response_mapper_name="odoo_mapper",
        supports_internal_sandbox_route=True,
    ),
}


def resolve_provider_profile(provider: str) -> ProductProviderProfile:
    key = (provider or "").lower().strip()
    profile = _PROFILES.get(key)
    if not profile:
        raise ProductProviderUnsupportedError(f"unsupported provider: {provider}")
    return profile


def validate_provider_runtime(
    profile: ProductProviderProfile,
    intent_code: str,
    base_url: str,
    timeout_ms: int,
    internal_sandbox_enabled: bool,
) -> None:
    if intent_code not in profile.supported_intents:
        raise ProductProviderConfigInvalidError(
            f"provider {profile.provider_name} does not support intent {intent_code}"
        )
    if timeout_ms <= 0:
        raise ProductProviderConfigInvalidError("timeout must be > 0")
    if not base_url:
        raise ProductProviderConfigInvalidError("base_url is empty")
    if base_url == "internal://sandbox" and not profile.supports_internal_sandbox_route:
        raise ProductProviderConfigInvalidError(
            f"provider {profile.provider_name} does not support internal sandbox route"
        )
    if base_url == "internal://sandbox" and not internal_sandbox_enabled:
        raise ProductProviderConfigInvalidError("internal sandbox api disabled")
