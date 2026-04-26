from __future__ import annotations

from app.clients.b_service_client import BServiceClient
from app.core.logging import logger
from app.workers.celery_app import celery_app


@celery_app.task(bind=True, name="app.tasks.scheduler_tasks.schedule_refresh_monitor_prices")
def schedule_refresh_monitor_prices(self) -> dict:
    logger.info("=== P13E SCHEDULE TRIGGER START ===")
    try:
        logger.info("=== P13E CALL B REFRESH ===")
        result = BServiceClient().refresh_monitor_prices(trigger_source="scheduled")
        run_id = str(result.get("run_id") or "")
        total = int(result.get("total") or 0)
        changed = int(result.get("changed") or 0)
        failed = int(result.get("failed") or 0)
        logger.info(
            "=== P13E SCHEDULE RESULT === run_id=%s total=%s changed=%s failed=%s",
            run_id,
            total,
            changed,
            failed,
        )
        return {
            "status": "success",
            "run_id": run_id,
            "total": total,
            "changed": changed,
            "failed": failed,
            "raw_result": result,
        }
    except Exception as exc:
        logger.exception("=== P13E SCHEDULE FAILED === error=%s", exc)
        return {"status": "failed", "error": str(exc)}
