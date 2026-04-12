"""Internal readiness endpoint for development/testing."""
from fastapi import APIRouter, Query

from app.clients.environment_readiness import check_environment_readiness
from app.clients.product_provider_readiness import check_query_provider_readiness
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
