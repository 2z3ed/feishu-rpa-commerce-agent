from fastapi import APIRouter

from app.api.v1 import (
    health,
    feishu_events,
    tasks,
    internal_sandbox,
    internal_rpa_sandbox,
    internal_rpa_admin_like,
    internal_rpa_real_admin_mirror,
    internal_readiness,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health.router)
api_router.include_router(feishu_events.router)
api_router.include_router(tasks.router)
api_router.include_router(internal_sandbox.router)
api_router.include_router(internal_rpa_sandbox.router)
api_router.include_router(internal_rpa_admin_like.router)
api_router.include_router(internal_rpa_real_admin_mirror.router)
api_router.include_router(internal_readiness.router)