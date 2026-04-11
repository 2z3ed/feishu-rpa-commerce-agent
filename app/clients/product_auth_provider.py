"""Minimal auth/header provider for query_sku_status sandbox client."""
from __future__ import annotations

from app.clients.product_credential_contract import (
    ProductCredentialError,
    validate_credentials,
)
from app.clients.woo_readonly_prep import evaluate_woo_readonly_prep


class ProductAuthBuildError(ProductCredentialError):
    """Raised when auth headers cannot be built from credential contract."""


def get_auth_headers(
    platform: str, expected_profile: str | None = None
) -> tuple[str, str, list[str], dict[str, str]]:
    credential_profile, credentials, missing = validate_credentials(platform)
    platform_key = (platform or "sandbox").lower().strip()
    if platform_key == "woo":
        woo_prep = evaluate_woo_readonly_prep()
        headers = {
            "X-Provider": "woo",
            "X-Woo-Token": credentials.get("WOO_API_TOKEN", ""),
            "X-Woo-Key": credentials.get("WOO_API_KEY", ""),
            "X-Woo-Auth-Mode": woo_prep.auth_mode,
        }
        if woo_prep.auth_mode == "token_header" and credentials.get("WOO_API_TOKEN"):
            headers["Authorization"] = f"Bearer {credentials.get('WOO_API_TOKEN', '')}"
        return "woo_auth_profile", credential_profile, missing, {
            **headers,
        }
    if platform_key == "odoo":
        return "odoo_auth_profile", credential_profile, missing, {
            "X-Provider": "odoo",
            "X-Odoo-Session": credentials.get("ODOO_SESSION_ID", ""),
            "X-Odoo-DB": credentials.get("ODOO_DB", ""),
        }
    profile = "sandbox_auth_profile"
    return profile, credential_profile, missing, {
        "X-Provider": "sandbox",
        "X-Sandbox-Key": "dev-sandbox-key",
    }
