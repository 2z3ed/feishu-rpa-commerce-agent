from celery import Celery

from app.core.config import settings


def create_celery_app() -> Celery:
    celery_app = Celery(
        "feishu_rpa",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
        include=["app.tasks.ingress_tasks"],
    )

    celery_app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="Asia/Shanghai",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=300,
        task_soft_time_limit=240,
        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=100,
    )

    return celery_app


celery_app = create_celery_app()