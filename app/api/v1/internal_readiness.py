"""Internal readiness endpoint for development/testing."""
from fastapi import APIRouter, Query

from app.clients.environment_readiness import check_environment_readiness
from app.clients.product_provider_readiness import (
    check_platform_provider_readiness,
    check_query_provider_readiness,
)
from app.clients.product_provider_profile import resolve_provider_profile
from app.services.feishu.bitable_write import check_bitable_readiness
from app.rag.retrieval_service import check_rag_readiness
from app.core.logging import logger
from app.core.config import settings

router = APIRouter(prefix="/internal/readiness", tags=["internal-readiness"])


@router.get("/query-sku-provider", include_in_schema=False)
def query_sku_provider_readiness(provider: str = Query(default="sandbox")):
    result = check_query_provider_readiness(provider)
    if result.ready:
        logger.info("Provider readiness success: provider=%s", result.provider_name)
    else:
        logger.warning(
            "Provider readiness failed: provider=%s, reason=%s, errors=%s",
            result.provider_name,
            result.reason,
            result.errors,
        )
    return result.to_dict()


@router.get("/provider", include_in_schema=False)
def provider_readiness(
    provider: str = Query(default="woo"),
    capability: str | None = Query(default=None),
):
    """
    P5.0 unified readiness entry.
    Keep old /query-sku-provider for backward compatibility.
    """
    provider_key = (provider or "").lower().strip() or "unknown"
    resolved_capability = (capability or "").strip()
    if not resolved_capability:
        try:
            resolved_capability = resolve_provider_profile(provider_key).capability
        except Exception:
            resolved_capability = "product.query_sku_status"

    result = check_platform_provider_readiness(provider_key, capability=resolved_capability)
    reason = (result.reason or "").strip() or ("ready" if bool(result.ready) else "not_ready")
    errors = [str(e).strip() for e in (result.errors or []) if str(e).strip()]
    reasons = [reason, *errors]
    body = {
        "provider_id": provider_key,
        "capability": resolved_capability,
        "ready": bool(result.ready),
        "credential_ready": bool(result.credential_ready),
        "sandbox_ready": bool(result.sandbox_ready),
        "production_shape_ready": bool(result.production_shape_ready),
        "production_config_ready": bool(result.production_config_ready),
        "recommended_strategy": (result.recommended_strategy or "").strip() or "n/a",
        "reason": reason,
        "reasons": reasons,
    }
    if result.ready:
        logger.info(
            "Unified provider readiness success: provider=%s capability=%s",
            body["provider_id"],
            resolved_capability,
        )
    else:
        logger.warning(
            "Unified provider readiness failed: provider=%s capability=%s reasons=%s",
            body["provider_id"],
            resolved_capability,
            body["reasons"],
        )
    return body


@router.get("/unified-provider", include_in_schema=False)
def unified_provider_readiness(
    provider: str = Query(..., description="provider id: woo|odoo|chatwoot"),
    capability: str | None = Query(default=None, description="capability/intent code"),
):
    """
    P5.0 unified readiness entry (preferred).
    This is a stable, provider/capability-shaped readiness API for multi-platform skeleton validation.
    """
    return provider_readiness(provider=provider, capability=capability)


@router.get("/rpa-target", include_in_schema=False)
def rpa_target_readiness():
    """P4.1: profile + config/session readiness for browser_real target (no production write)."""
    from app.rpa.target_readiness import evaluate_rpa_target_readiness

    rr = evaluate_rpa_target_readiness(settings)
    return rr.to_dict()


@router.get("/environment", include_in_schema=False)
def environment_readiness():
    result = check_environment_readiness()
    if result.environment_ready:
        logger.info("Environment readiness success")
    else:
        logger.warning(
            "Environment readiness warning: redis_ready=%s feishu_network_ready=%s "
            "dns_ready=%s tcp_ready=%s tls_ready=%s proxy_enabled=%s",
            result.redis_ready,
            result.feishu_network_ready,
            result.dns_ready,
            result.tcp_ready,
            result.tls_ready,
            result.proxy_enabled,
        )
    body = result.to_dict()
    body.update(check_bitable_readiness())
    body.update(check_rag_readiness())
    return body
