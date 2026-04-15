"""Odoo readonly inventory client (sandbox/in-process).

P6.0 goal: make `warehouse.query_inventory` use the same observable provider chain:
- provider profile + runtime validation
- request adapter (build provider request)
- internal sandbox route (in-process TestClient)
- response mapper (odoo_mapper)

This is NOT a real Odoo integration. It is a deterministic readonly sample chain.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.clients.product_provider_mapper import ProductApiMapperError, get_mapper
from app.clients.product_provider_profile import (
    ProductProviderConfigInvalidError,
    ProductProviderUnsupportedError,
    resolve_provider_profile,
    validate_provider_runtime,
)
from app.clients.product_request_adapter import ProductApiRequestAdapterError, build_query_sku_request
from app.core.config import settings


class OdooInventoryClientError(Exception):
    """Base error for odoo inventory client."""


class OdooInventoryClientNotFound(OdooInventoryClientError):
    """SKU not found by sandbox provider."""


class OdooInventoryClientTimeout(OdooInventoryClientError):
    """Sandbox call timed out."""


class OdooInventoryClientDisabled(OdooInventoryClientError):
    """Internal sandbox disabled."""


class OdooInventoryClientRequestError(OdooInventoryClientError):
    """Request adapter / provider profile mismatch."""


class OdooInventoryClientMapperError(OdooInventoryClientError):
    """Mapper could not map payload."""


@dataclass(frozen=True)
class OdooInventoryResult:
    sku: str
    product_name: str
    status: str
    inventory: int
    platform: str = "odoo"


class OdooInventoryClient:
    """Readonly inventory client for capability `warehouse.query_inventory`."""

    def __init__(self, base_url: str | None = None, timeout_seconds: float = 2.0):
        self.base_url = base_url or settings.PRODUCT_QUERY_SKU_API_BASE_URL or "internal://sandbox"
        self.timeout_seconds = timeout_seconds
        self.last_request_adapter = "unknown_request_adapter"
        self.last_auth_profile = "unknown_auth_profile"
        self.last_credential_profile = "unknown_credential_profile"
        self.last_mapper = "unknown_mapper"

    @property
    def client_profile(self) -> str:
        timeout_ms = int(self.timeout_seconds * 1000)
        return f"sandbox_http@{self.base_url}|{timeout_ms}ms"

    def _map_response_to_data(self, response: httpx.Response) -> Optional[dict]:
        status = response.status_code
        if status == 200:
            return response.json()
        if status == 404:
            return None
        if status == 503:
            raise OdooInventoryClientDisabled("internal sandbox api disabled")
        if status == 504:
            raise OdooInventoryClientTimeout("sandbox timeout for query_inventory")
        if status == 502:
            raise OdooInventoryClientError("sandbox client error")
        raise OdooInventoryClientError(f"sandbox unexpected status={status}")

    def _build_minimal_internal_sandbox_app(self) -> FastAPI:
        """Build a minimal app containing only internal sandbox routes.

        Avoid importing the full `app.main:app` which pulls optional deps (lark/redis) in some envs.
        """
        from app.api.v1 import internal_sandbox

        a = FastAPI()
        a.include_router(internal_sandbox.router, prefix="/api/v1")
        return a

    def query_inventory(self, sku: str) -> OdooInventoryResult:
        sku_upper = (sku or "").strip().upper()
        if not sku_upper:
            raise OdooInventoryClientRequestError("SKU is required")

        try:
            profile = resolve_provider_profile("odoo")
            timeout_ms = int(self.timeout_seconds * 1000)
            validate_provider_runtime(
                profile=profile,
                intent_code="warehouse.query_inventory",
                base_url=self.base_url,
                timeout_ms=timeout_ms,
                internal_sandbox_enabled=settings.ENABLE_INTERNAL_SANDBOX_API,
            )
        except ProductProviderUnsupportedError as exc:
            raise OdooInventoryClientRequestError(f"[provider_unsupported] {exc}") from exc
        except ProductProviderConfigInvalidError as exc:
            raise OdooInventoryClientRequestError(f"[provider_config_invalid] {exc}") from exc

        try:
            # Reuse existing request adapter shape (Odoo provider route is stable).
            request = build_query_sku_request("odoo", sku_upper, profile)
        except ProductApiRequestAdapterError as exc:
            raise OdooInventoryClientRequestError(str(exc)) from exc

        self.last_request_adapter = request.request_adapter
        self.last_auth_profile = request.auth_profile
        self.last_credential_profile = request.credential_profile

        if self.base_url == "internal://sandbox":
            with TestClient(self._build_minimal_internal_sandbox_app()) as client:
                response = client.get(request.path, params=request.params, headers=request.headers)
        else:
            try:
                with httpx.Client(base_url=self.base_url, timeout=self.timeout_seconds) as client:
                    response = client.get(request.path, params=request.params, headers=request.headers)
            except httpx.TimeoutException as exc:
                raise OdooInventoryClientTimeout("sandbox http timeout") from exc
            except httpx.HTTPError as exc:
                raise OdooInventoryClientError(f"sandbox http transport error: {exc}") from exc

        data = self._map_response_to_data(response)
        if data is None:
            raise OdooInventoryClientNotFound(f"SKU {sku_upper} not found")

        provider = data.get("provider", "odoo")
        raw_payload = data.get("payload", {})
        mapper_name, mapper = get_mapper(provider)
        self.last_mapper = mapper_name
        if mapper_name != profile.response_mapper_name:
            raise OdooInventoryClientMapperError(
                f"profile mapper mismatch: expected {profile.response_mapper_name}, got {mapper_name}"
            )
        try:
            mapped = mapper(raw_payload, provider)
        except ProductApiMapperError as exc:
            raise OdooInventoryClientMapperError(f"{mapper_name} failed: {exc}") from exc

        return OdooInventoryResult(
            sku=mapped.sku,
            product_name=mapped.product_name,
            status=mapped.status,
            inventory=mapped.inventory,
            platform=mapped.platform,
        )

