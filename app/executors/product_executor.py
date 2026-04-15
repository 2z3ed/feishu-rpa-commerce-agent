"""Minimal product executor abstraction for current mock stage."""
from __future__ import annotations

from typing import Protocol, Optional, Dict, Any

from app.clients.product_api_client import (
    classify_woo_dry_run_failure,
    ProductApiClientDisabled,
    ProductApiClientError,
    ProductApiClientMapperError,
    ProductApiClientRequestError,
    ProductApiClientTimeout,
    SandboxHttpProductApiClient,
    WooHttpDryRunProductApiClient,
)
from app.clients.product_provider_mapper import get_mapper
from app.clients.product_provider_profile import resolve_provider_profile
from app.core.config import settings
from app.clients.woo_readonly_prep import get_woo_dry_run_strategy
from app.repositories.product_repo import product_repo


EXECUTION_MODE_MOCK = "mock"
EXECUTION_MODE_API = "api"
EXECUTION_MODE_RPA = "rpa"
EXECUTION_MODE_API_THEN_RPA_VERIFY = "api_then_rpa_verify"

SUPPORTED_EXECUTION_MODES = {
    EXECUTION_MODE_MOCK,
    EXECUTION_MODE_API,
    EXECUTION_MODE_RPA,
    EXECUTION_MODE_API_THEN_RPA_VERIFY,
}
SUPPORTED_QUERY_PLATFORMS = {"mock", "woo", "odoo", "sandbox"}


class ProductExecutor(Protocol):
    def query_sku_status(self, sku: str, platform: str = "mock") -> Optional[Dict[str, Any]]:
        ...

    def update_price(self, sku: str, target_price: float, platform: str = "mock") -> Optional[Dict[str, Any]]:
        ...


class MockProductExecutor:
    """Current real executor (mock only)."""

    def query_sku_status(self, sku: str, platform: str = "mock") -> Optional[Dict[str, Any]]:
        return product_repo.query_sku_status(sku, platform)

    def update_price(self, sku: str, target_price: float, platform: str = "mock") -> Optional[Dict[str, Any]]:
        return product_repo.update_price(sku, target_price, platform)


class ApiProductExecutor:
    """Minimal API executor for sku query (stub client now)."""

    def __init__(self):
        self.sandbox_client = SandboxHttpProductApiClient(
            timeout_seconds=max(settings.PRODUCT_QUERY_SKU_API_TIMEOUT_MS, 1) / 1000.0
        )
        self.woo_dry_run_client = WooHttpDryRunProductApiClient()
        self.client = self.sandbox_client
        self.last_selected_backend = "sandbox_http_client"
        self.last_dry_run_enabled = "false"
        self.last_backend_selection_reason = "default_sandbox"
        self.last_fallback_enabled = "true" if settings.WOO_ENABLE_READONLY_DRY_RUN_FALLBACK else "false"
        self.last_fallback_applied = "false"
        self.last_fallback_target = "sandbox_http_client"
        self.last_final_backend = "sandbox_http_client"
        self.last_dry_run_failure = "none"

    def get_backend_profile(self) -> str:
        return self.client.client_profile

    def get_mapper_name(self, platform: str) -> str:
        mapper_name, _ = get_mapper(platform)
        return mapper_name

    def get_provider_profile_name(self, platform: str) -> str:
        return resolve_provider_profile(platform).provider_name

    def get_request_adapter_name(self) -> str:
        return self.client.last_request_adapter

    def get_auth_profile(self) -> str:
        return self.client.last_auth_profile

    def get_credential_profile(self) -> str:
        return self.client.last_credential_profile

    def get_production_config_ready(self) -> str:
        return self.client.last_production_config_ready

    def get_selected_backend(self) -> str:
        return self.last_selected_backend

    def get_dry_run_enabled(self) -> str:
        return self.last_dry_run_enabled

    def get_backend_selection_reason(self) -> str:
        return self.last_backend_selection_reason

    def get_fallback_enabled(self) -> str:
        return self.last_fallback_enabled

    def get_fallback_applied(self) -> str:
        return self.last_fallback_applied

    def get_fallback_target(self) -> str:
        return self.last_fallback_target

    def get_final_backend(self) -> str:
        return self.last_final_backend

    def get_dry_run_failure(self) -> str:
        return self.last_dry_run_failure

    def _select_client(self, platform: str) -> None:
        strategy = get_woo_dry_run_strategy(EXECUTION_MODE_API, platform)
        backend = str(strategy["selected_backend"])
        self.last_selected_backend = backend
        self.last_dry_run_enabled = "true" if bool(strategy["dry_run_enabled"]) else "false"
        self.last_backend_selection_reason = str(strategy["backend_selection_reason"])
        self.last_fallback_enabled = "true" if bool(strategy["fallback_enabled"]) else "false"
        self.last_fallback_target = str(strategy["fallback_target"])
        self.last_fallback_applied = "false"
        self.last_final_backend = backend
        self.last_dry_run_failure = "none"
        self.client = self.woo_dry_run_client if backend == "woo_http_dry_run_client" else self.sandbox_client

    def query_sku_status(self, sku: str, platform: str = "woo") -> Optional[Dict[str, Any]]:
        self._select_client(platform)
        if self.last_selected_backend == "woo_http_dry_run_client":
            try:
                result = self.woo_dry_run_client.query_sku_status(sku, platform)
                self.client = self.woo_dry_run_client
                self.last_final_backend = "woo_http_dry_run_client"
            except (ProductApiClientRequestError, ProductApiClientTimeout, ProductApiClientError) as exc:
                self.last_dry_run_failure = classify_woo_dry_run_failure(exc)
                if self.last_fallback_enabled == "true":
                    self.last_fallback_applied = "true"
                    self.last_backend_selection_reason = f"{self.last_dry_run_failure}|fallback_applied"
                    self.client = self.sandbox_client
                    self.last_final_backend = self.last_fallback_target
                    try:
                        result = self.sandbox_client.query_sku_status(sku, platform)
                    except ProductApiClientRequestError as fallback_exc:
                        raise RuntimeError(
                            f"api query_sku_status failed: [{self.last_dry_run_failure}] {exc}; [fallback_applied] [request_adapter_error] {fallback_exc}"
                        ) from fallback_exc
                    except ProductApiClientDisabled as fallback_exc:
                        raise RuntimeError(
                            f"api query_sku_status failed: [{self.last_dry_run_failure}] {exc}; [fallback_applied] [sandbox_disabled] {fallback_exc}"
                        ) from fallback_exc
                    except ProductApiClientTimeout as fallback_exc:
                        raise RuntimeError(
                            f"api query_sku_status failed: [{self.last_dry_run_failure}] {exc}; [fallback_applied] [client_timeout] {fallback_exc}"
                        ) from fallback_exc
                    except ProductApiClientMapperError as fallback_exc:
                        raise RuntimeError(
                            f"api query_sku_status failed: [{self.last_dry_run_failure}] {exc}; [fallback_applied] [mapper_error] {fallback_exc}"
                        ) from fallback_exc
                    except ProductApiClientError as fallback_exc:
                        raise RuntimeError(
                            f"api query_sku_status failed: [{self.last_dry_run_failure}] {exc}; [fallback_applied] [client_error] {fallback_exc}"
                        ) from fallback_exc
                else:
                    self.last_backend_selection_reason = f"{self.last_dry_run_failure}|fallback_not_allowed"
                    raise RuntimeError(
                        f"api query_sku_status failed: [{self.last_dry_run_failure}] {exc}; [fallback_not_allowed]"
                    ) from exc
            if not result:
                return None
            return result.to_dict()

        try:
            result = self.client.query_sku_status(sku, platform)
            self.last_final_backend = self.last_selected_backend
        except ProductApiClientRequestError as exc:
            raise RuntimeError(f"api query_sku_status failed: [request_adapter_error] {exc}") from exc
        except ProductApiClientDisabled as exc:
            raise RuntimeError(f"api query_sku_status failed: [sandbox_disabled] {exc}") from exc
        except ProductApiClientTimeout as exc:
            raise RuntimeError(f"api query_sku_status failed: [client_timeout] {exc}") from exc
        except ProductApiClientMapperError as exc:
            raise RuntimeError(f"api query_sku_status failed: [mapper_error] {exc}") from exc
        except ProductApiClientError as exc:
            raise RuntimeError(f"api query_sku_status failed: [client_error] {exc}") from exc
        if not result:
            return None
        return result.to_dict()

    def update_price(self, sku: str, target_price: float, platform: str = "woo") -> Optional[Dict[str, Any]]:
        raise NotImplementedError("ApiProductExecutor.update_price is not enabled in current mock stage.")


class RpaProductExecutor:
    """Graph confirm-phase RPA uses app.rpa.confirm_update_price (not this class)."""

    def query_sku_status(self, sku: str, platform: str = "woo") -> Optional[Dict[str, Any]]:
        return product_repo.query_sku_status(sku, "mock")

    def update_price(self, sku: str, target_price: float, platform: str = "woo") -> Optional[Dict[str, Any]]:
        raise NotImplementedError(
            "RpaProductExecutor.update_price is not used; confirm flow calls run_confirm_update_price_rpa."
        )


class ApiThenRpaVerifyExecutor:
    """Placeholder for future API then RPA verify strategy."""

    def query_sku_status(self, sku: str, platform: str = "woo") -> Optional[Dict[str, Any]]:
        raise NotImplementedError("ApiThenRpaVerifyExecutor is not implemented in current mock stage.")

    def update_price(self, sku: str, target_price: float, platform: str = "woo") -> Optional[Dict[str, Any]]:
        raise NotImplementedError("ApiThenRpaVerifyExecutor is not implemented in current mock stage.")


def resolve_execution_mode(intent_code: str, requested_mode: str | None = None) -> str:
    """Current strategy:
    - query_sku_status supports mock/api entry
    - update_price and confirm remain mock only
    """
    mode = (requested_mode or "").lower().strip()
    # P6.0: Odoo readonly sample chain (warehouse.query_inventory) should not be labelled "mock".
    # This path uses provider profile + request_adapter + internal sandbox route + mapper, i.e. api-like.
    # Keep the global strategy unchanged; only tighten the semantic for this readonly chain.
    if intent_code == "warehouse.query_inventory":
        return EXECUTION_MODE_API
    if intent_code == "product.query_sku_status":
        allow_rpa = bool(getattr(settings, "PRODUCT_QUERY_SKU_ENABLE_REAL_ADMIN_READONLY", False))
        if mode in {EXECUTION_MODE_MOCK, EXECUTION_MODE_API}:
            return mode
        if mode == EXECUTION_MODE_RPA and allow_rpa:
            return mode
        configured = (settings.PRODUCT_QUERY_SKU_DEFAULT_EXECUTION_MODE or EXECUTION_MODE_MOCK).lower().strip()
        if configured in {EXECUTION_MODE_MOCK, EXECUTION_MODE_API}:
            return configured
        if configured == EXECUTION_MODE_RPA and allow_rpa:
            return configured
        return EXECUTION_MODE_MOCK
    if intent_code in {"product.update_price", "system.confirm_task"}:
        return EXECUTION_MODE_MOCK
    if not mode:
        mode = EXECUTION_MODE_MOCK
    return mode if mode in SUPPORTED_EXECUTION_MODES else EXECUTION_MODE_MOCK


def resolve_query_platform(execution_mode: str, requested_platform: str | None = None) -> str:
    """Resolve query platform for product.query_sku_status only.

    - mock mode defaults to mock
    - api mode defaults to PRODUCT_QUERY_SKU_DEFAULT_PLATFORM (fallback sandbox)
    - invalid requested/configured values fallback safely
    """
    mode = (execution_mode or EXECUTION_MODE_MOCK).lower().strip()
    req = (requested_platform or "").lower().strip()
    if req in SUPPORTED_QUERY_PLATFORMS:
        if mode == EXECUTION_MODE_MOCK:
            return "mock"
        return req

    if mode == EXECUTION_MODE_API:
        configured = (settings.PRODUCT_QUERY_SKU_DEFAULT_PLATFORM or "sandbox").lower().strip()
        if configured in SUPPORTED_QUERY_PLATFORMS - {"mock"}:
            return configured
        return "sandbox"

    return "mock"


def get_product_executor(execution_mode: str) -> ProductExecutor:
    mode = (execution_mode or EXECUTION_MODE_MOCK).lower()
    if mode == EXECUTION_MODE_MOCK:
        return MockProductExecutor()
    if mode == EXECUTION_MODE_API:
        return ApiProductExecutor()
    if mode == EXECUTION_MODE_RPA:
        return RpaProductExecutor()
    if mode == EXECUTION_MODE_API_THEN_RPA_VERIFY:
        return ApiThenRpaVerifyExecutor()
    return MockProductExecutor()
