from fastapi import APIRouter
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.session import get_sync_database_url
from app.schemas.common import CommonResponse
from app.schemas.feishu import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


def check_redis() -> tuple[bool, str]:
    try:
        try:
            import redis  # type: ignore
        except Exception as e:  # pragma: no cover
            return False, f"redis client not installed: {e}"
        r = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            socket_connect_timeout=2
        )
        r.ping()
        return True, "connected"
    except Exception as e:
        return False, str(e)


def check_database() -> tuple[bool, str]:
    try:
        engine = create_engine(get_sync_database_url())
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "connected"
    except Exception as e:
        return False, str(e)


@router.get("", response_model=CommonResponse)
def health_check():
    db_ok, db_msg = check_database()
    db_status = "connected" if db_ok else "disconnected"
    
    redis_ok, redis_msg = check_redis()
    redis_status = "connected" if redis_ok else "disconnected"

    all_ok = db_ok and redis_ok

    return CommonResponse(
        code=0 if all_ok else 1,
        message="success" if all_ok else "service unhealthy",
        data={
            "database": {"status": db_status, "error": None if db_ok else db_msg},
            "redis": {"status": redis_status, "error": None if redis_ok else redis_msg}
        }
    )