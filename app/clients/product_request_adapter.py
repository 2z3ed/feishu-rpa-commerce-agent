"""Provider request adapter for query_sku_status."""
from __future__ import annotations

from dataclasses import dataclass

from app.clients.product_auth_provider import get_auth_headers
from app.clients.product_provider_profile import ProductProviderProfile
from app.clients.woo_readonly_prep import evaluate_woo_readonly_prep


class ProductApiRequestAdapterError(Exception):
    """Raised when provider request cannot be constructed."""


@dataclass
class ProviderHttpRequest:
    path: str
    params: dict[str, str]
    headers: dict[str, str]
    request_adapter: str
    auth_profile: str
    credential_profile: str
    missing_config_keys: list[str]


def build_query_sku_request(platform: str, sku: str, profile: ProductProviderProfile) -> ProviderHttpRequest:
    platform_key = (platform or "sandbox").lower().strip()
    auth_profile, credential_profile, missing_config_keys, headers = get_auth_headers(
        platform_key, profile.auth_profile_name
    )

    if platform_key == "sandbox":
        request = ProviderHttpRequest(
            path=f"/api/v1/internal/sandbox/provider/sandbox/sku/{sku}",
            params={"provider_platform": "sandbox"},
            headers=headers,
            request_adapter="sandbox_request_adapter",
            auth_profile=auth_profile,
            credential_profile=credential_profile,
            missing_config_keys=missing_config_keys,
        )
        if request.request_adapter != profile.request_adapter_name:
            raise ProductApiRequestAdapterError("request adapter/profile mismatch: sandbox")
        return request
    if platform_key == "woo":
        woo_prep = evaluate_woo_readonly_prep()
        request = ProviderHttpRequest(
            path=f"/api/v1/internal/sandbox/provider/woo/{woo_prep.api_version_prefix}/products",
            params={
                "sku": sku,
                "status": "any",
                "per_page": "1",
                "consumer_key": credentials_key_placeholder(headers.get("X-Woo-Key", "")),
            },
            headers={
                **headers,
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-Woo-Auth-Shape": woo_prep.auth_mode,
            },
            request_adapter="woo_request_adapter",
            auth_profile=auth_profile,
            credential_profile=credential_profile,
            missing_config_keys=missing_config_keys,
        )
        if request.request_adapter != profile.request_adapter_name:
            raise ProductApiRequestAdapterError("request adapter/profile mismatch: woo")
        return request
    if platform_key == "odoo":
        request = ProviderHttpRequest(
            path=f"/api/v1/internal/sandbox/provider/odoo/product/{sku}",
            params={"company": "main"},
            headers=headers,
            request_adapter="odoo_request_adapter",
            auth_profile=auth_profile,
            credential_profile=credential_profile,
            missing_config_keys=missing_config_keys,
        )
        if request.request_adapter != profile.request_adapter_name:
            raise ProductApiRequestAdapterError("request adapter/profile mismatch: odoo")
        return request
    raise ProductApiRequestAdapterError(f"unsupported query_sku_status platform: {platform_key}")


def credentials_key_placeholder(value: str) -> str:
    return value or "ck_placeholder"


def build_woo_query_sku_dry_run_request(sku: str, profile: ProductProviderProfile) -> ProviderHttpRequest:
    """Build Woo request shape for readonly dry-run backend."""
    auth_profile, credential_profile, missing_config_keys, headers = get_auth_headers("woo", profile.auth_profile_name)
    woo_prep = evaluate_woo_readonly_prep()
    request = ProviderHttpRequest(
        path=f"/{woo_prep.api_version_prefix}/products",
        params={
            "sku": sku,
            "status": "any",
            "per_page": "1",
            "consumer_key": credentials_key_placeholder(headers.get("X-Woo-Key", "")),
        },
        headers={
            **headers,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Woo-Auth-Shape": woo_prep.auth_mode,
            "X-Woo-Dry-Run": "true",
        },
        request_adapter="woo_request_adapter",
        auth_profile=auth_profile,
        credential_profile=credential_profile,
        missing_config_keys=missing_config_keys,
    )
    if request.request_adapter != profile.request_adapter_name:
        raise ProductApiRequestAdapterError("request adapter/profile mismatch: woo dry run")
    return request
