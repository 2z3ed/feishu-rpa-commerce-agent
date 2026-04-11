"""Provider credential/auth config contract for query_sku_status."""
from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings


class ProductCredentialError(Exception):
    """Base error for provider credential contract."""


class ProductCredentialMissingError(ProductCredentialError):
    """Raised when required credential keys are missing."""


class ProductCredentialInvalidError(ProductCredentialError):
    """Raised when credential value is malformed."""


@dataclass(frozen=True)
class ProviderCredentialContract:
    provider_name: str
    required_config_keys: tuple[str, ...]
    optional_config_keys: tuple[str, ...]
    auth_mode: str
    credential_profile_name: str
    allow_empty_credentials: bool = False


_CONTRACTS: dict[str, ProviderCredentialContract] = {
    "sandbox": ProviderCredentialContract(
        provider_name="sandbox",
        required_config_keys=(),
        optional_config_keys=(),
        auth_mode="sandbox_fixed",
        credential_profile_name="sandbox_credential_profile",
        allow_empty_credentials=True,
    ),
    "woo": ProviderCredentialContract(
        provider_name="woo",
        required_config_keys=("WOO_API_TOKEN",),
        optional_config_keys=("WOO_API_KEY",),
        auth_mode="header_token",
        credential_profile_name="woo_credential_profile",
        allow_empty_credentials=False,
    ),
    "odoo": ProviderCredentialContract(
        provider_name="odoo",
        required_config_keys=("ODOO_SESSION_ID",),
        optional_config_keys=("ODOO_DB",),
        auth_mode="session_like",
        credential_profile_name="odoo_credential_profile",
        allow_empty_credentials=False,
    ),
}


def resolve_credential_contract(provider: str) -> ProviderCredentialContract:
    key = (provider or "").lower().strip()
    contract = _CONTRACTS.get(key)
    if not contract:
        raise ProductCredentialInvalidError(f"unsupported provider for credential contract: {provider}")
    return contract


def get_runtime_credentials(provider: str) -> dict[str, str]:
    contract = resolve_credential_contract(provider)
    data: dict[str, str] = {}
    for key in (*contract.required_config_keys, *contract.optional_config_keys):
        data[key] = str(getattr(settings, key, "") or "")
    return data


def validate_credentials(provider: str) -> tuple[str, dict[str, str], list[str]]:
    contract = resolve_credential_contract(provider)
    credentials = get_runtime_credentials(provider)
    missing: list[str] = []

    if not contract.allow_empty_credentials:
        for key in contract.required_config_keys:
            if not credentials.get(key):
                missing.append(key)
        if missing:
            raise ProductCredentialMissingError(
                f"credential_missing: provider={provider}, missing={','.join(missing)}"
            )

    # Minimal invalid format check for session-like credential.
    if contract.auth_mode == "session_like":
        session = credentials.get("ODOO_SESSION_ID", "")
        if session and len(session) < 6:
            raise ProductCredentialInvalidError("credential_invalid: ODOO_SESSION_ID too short")

    return contract.credential_profile_name, credentials, missing
