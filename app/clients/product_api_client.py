"""Minimal product API client boundary for sku query."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import httpx
from fastapi.testclient import TestClient

from app.clients.product_credential_contract import (
    ProductCredentialInvalidError,
    ProductCredentialMissingError,
)
from app.clients.product_provider_mapper import ProductApiMapperError, get_mapper
from app.clients.product_provider_profile import (
    ProductProviderConfigInvalidError,
    ProductProviderUnsupportedError,
    resolve_provider_profile,
    validate_provider_runtime,
)
from app.clients.product_request_adapter import (
    ProductApiRequestAdapterError,
    build_query_sku_request,
    build_woo_query_sku_dry_run_request,
)
from app.clients.woo_readonly_prep import evaluate_woo_readonly_prep
from app.core.config import settings


class ProductApiClientError(Exception):
    """Base error for product api client."""


class ProductApiClientNotFound(ProductApiClientError):
    """Raised when SKU is not found by upstream."""


class ProductApiClientTimeout(ProductApiClientError):
    """Raised when upstream call times out."""


class ProductApiClientDisabled(ProductApiClientError):
    """Raised when sandbox endpoint is disabled by config."""


class ProductApiClientMapperError(ProductApiClientError):
    """Raised when provider payload cannot be mapped to unified DTO."""


class ProductApiClientRequestError(ProductApiClientError):
    """Raised when request adapter cannot build provider request."""


def classify_woo_dry_run_failure(exc: Exception) -> str:
    """Centralized dry-run failure semantic."""
    if isinstance(exc, ProductApiClientTimeout):
        return "dry_run_timeout"
    if isinstance(exc, ProductApiClientRequestError) and "dry_run_config_not_ready" in str(exc):
        return "dry_run_not_ready"
    if isinstance(exc, (ProductApiClientRequestError, ProductApiClientError)):
        return "dry_run_client_error"
    return "dry_run_client_error"


@dataclass
class ProductSkuStatus:
    sku: str
    product_name: str
    status: str
    inventory: int
    price: float
    platform: str

    def to_dict(self) -> dict:
        return {
            "sku": self.sku,
            "product_name": self.product_name,
            "status": self.status,
            "inventory": self.inventory,
            "price": self.price,
            "platform": self.platform,
        }


class ProductApiClient:
    """Client protocol-like base class for future real API integration."""

    def query_sku_status(self, sku: str, platform: str = "woo") -> Optional[ProductSkuStatus]:
        raise NotImplementedError


class SandboxHttpProductApiClient(ProductApiClient):
    """HTTP-based sandbox client for query_sku_status.

    Default base_url is internal://sandbox (in-process FastAPI endpoint).
    """

    def __init__(self, base_url: str | None = None, timeout_seconds: float = 2.0):
        self.base_url = (
            base_url
            or settings.PRODUCT_QUERY_SKU_API_BASE_URL
            or settings.PRODUCT_QUERY_SKU_SANDBOX_BASE_URL
        )
        self.timeout_seconds = timeout_seconds
        self.last_request_adapter = "unknown_request_adapter"
        self.last_auth_profile = "unknown_auth_profile"
        self.last_credential_profile = "unknown_credential_profile"
        self.last_missing_config_keys: list[str] = []
        self.last_mapper = "unknown_mapper"
        self.last_production_config_ready = "n/a"

    @property
    def client_profile(self) -> str:
        timeout_ms = int(self.timeout_seconds * 1000)
        return f"sandbox_http@{self.base_url}|{timeout_ms}ms"

    @property
    def request_profile(self) -> str:
        return f"{self.last_request_adapter}|{self.last_auth_profile}"

    def _map_response_to_data(self, response: httpx.Response) -> Optional[dict]:
        """Centralized status mapping for sandbox HTTP responses."""
        status = response.status_code
        if status == 200:
            return response.json()
        if status == 404:
            return None
        if status == 503:
            raise ProductApiClientDisabled("internal sandbox api disabled")
        if status == 504:
            raise ProductApiClientTimeout("sandbox timeout for query_sku_status")
        if status == 502:
            raise ProductApiClientError("sandbox client error")
        raise ProductApiClientError(f"sandbox unexpected status={status}")

    def query_sku_status(self, sku: str, platform: str = "woo") -> Optional[ProductSkuStatus]:
        platform_key = (platform or "sandbox").lower().strip()
        try:
            profile = resolve_provider_profile(platform_key)
            timeout_ms = int(self.timeout_seconds * 1000)
            validate_provider_runtime(
                profile=profile,
                intent_code="product.query_sku_status",
                base_url=self.base_url,
                timeout_ms=timeout_ms,
                internal_sandbox_enabled=settings.ENABLE_INTERNAL_SANDBOX_API,
            )
        except ProductProviderUnsupportedError as exc:
            raise ProductApiClientRequestError(f"[provider_unsupported] {exc}") from exc
        except ProductProviderConfigInvalidError as exc:
            raise ProductApiClientRequestError(f"[provider_config_invalid] {exc}") from exc

        try:
            request = build_query_sku_request(platform_key, sku, profile)
        except ProductCredentialMissingError as exc:
            raise ProductApiClientRequestError(f"[credential_missing] {exc}") from exc
        except ProductCredentialInvalidError as exc:
            raise ProductApiClientRequestError(f"[credential_invalid] {exc}") from exc
        except ProductApiRequestAdapterError as exc:
            raise ProductApiClientRequestError(str(exc)) from exc

        self.last_request_adapter = request.request_adapter
        self.last_auth_profile = request.auth_profile
        self.last_credential_profile = request.credential_profile
        self.last_missing_config_keys = list(request.missing_config_keys)
        if platform_key == "woo":
            self.last_production_config_ready = (
                "true" if evaluate_woo_readonly_prep().production_config_ready else "false"
            )
        else:
            self.last_production_config_ready = "n/a"

        if self.base_url == "internal://sandbox":
            from app.main import app

            with TestClient(app) as client:
                response = client.get(request.path, params=request.params, headers=request.headers)
        else:
            try:
                with httpx.Client(base_url=self.base_url, timeout=self.timeout_seconds) as client:
                    response = client.get(request.path, params=request.params, headers=request.headers)
            except httpx.TimeoutException as exc:
                raise ProductApiClientTimeout("sandbox http timeout") from exc
            except httpx.HTTPError as exc:
                raise ProductApiClientError(f"sandbox http transport error: {exc}") from exc

        data = self._map_response_to_data(response)
        if data is None:
            return None
        provider = data.get("provider", "sandbox")
        raw_payload = data.get("payload", {})
        mapper_name, mapper = get_mapper(provider)
        self.last_mapper = mapper_name
        if mapper_name != profile.response_mapper_name:
            raise ProductApiClientMapperError(
                f"profile mapper mismatch: expected {profile.response_mapper_name}, got {mapper_name}"
            )
        try:
            mapped = mapper(raw_payload, provider)
        except ProductApiMapperError as exc:
            raise ProductApiClientMapperError(f"{mapper_name} failed: {exc}") from exc

        return ProductSkuStatus(
            sku=mapped.sku,
            product_name=mapped.product_name,
            status=mapped.status,
            inventory=mapped.inventory,
            price=mapped.price,
            platform=mapped.platform,
        )


class WooHttpDryRunProductApiClient(ProductApiClient):
    """Woo readonly dry-run backend (real HTTP shape, config-gated)."""

    def __init__(self):
        self.last_request_adapter = "unknown_request_adapter"
        self.last_auth_profile = "unknown_auth_profile"
        self.last_credential_profile = "unknown_credential_profile"
        self.last_mapper = "unknown_mapper"
        self.last_production_config_ready = "false"

    @property
    def client_profile(self) -> str:
        prep = evaluate_woo_readonly_prep()
        return f"woo_http_dry_run@{prep.base_url}|{prep.timeout_ms}ms"

    def query_sku_status(self, sku: str, platform: str = "woo") -> Optional[ProductSkuStatus]:
        platform_key = (platform or "woo").lower().strip()
        if platform_key != "woo":
            raise ProductApiClientRequestError("[dry_run_invalid_platform] woo dry-run only supports woo")

        prep = evaluate_woo_readonly_prep()
        self.last_production_config_ready = "true" if prep.production_config_ready else "false"
        if not prep.production_config_ready:
            raise ProductApiClientRequestError(f"[dry_run_config_not_ready] {prep.reason}")

        try:
            profile = resolve_provider_profile("woo")
            request = build_woo_query_sku_dry_run_request(sku, profile)
        except ProductCredentialMissingError as exc:
            raise ProductApiClientRequestError(f"[credential_missing] {exc}") from exc
        except ProductCredentialInvalidError as exc:
            raise ProductApiClientRequestError(f"[credential_invalid] {exc}") from exc
        except ProductApiRequestAdapterError as exc:
            raise ProductApiClientRequestError(str(exc)) from exc

        self.last_request_adapter = request.request_adapter
        self.last_auth_profile = request.auth_profile
        self.last_credential_profile = request.credential_profile

        try:
            with httpx.Client(base_url=prep.base_url, timeout=max(prep.timeout_ms, 1) / 1000.0) as client:
                response = client.get(request.path, params=request.params, headers=request.headers)
        except httpx.TimeoutException as exc:
            raise ProductApiClientTimeout("woo dry-run timeout") from exc
        except httpx.HTTPError as exc:
            raise ProductApiClientError(f"woo dry-run transport error: {exc}") from exc

        status = response.status_code
        if status == 404:
            return None
        if status != 200:
            raise ProductApiClientError(f"woo dry-run unexpected status={status}")

        data = response.json()
        provider = data.get("provider", "woo")
        raw_payload = data.get("payload", data)
        mapper_name, mapper = get_mapper(provider)
        self.last_mapper = mapper_name
        if mapper_name != profile.response_mapper_name:
            raise ProductApiClientMapperError(
                f"profile mapper mismatch: expected {profile.response_mapper_name}, got {mapper_name}"
            )
        try:
            mapped = mapper(raw_payload, provider)
        except ProductApiMapperError as exc:
            raise ProductApiClientMapperError(f"{mapper_name} failed: {exc}") from exc
        return ProductSkuStatus(
            sku=mapped.sku,
            product_name=mapped.product_name,
            status=mapped.status,
            inventory=mapped.inventory,
            price=mapped.price,
            platform=mapped.platform,
        )
