from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.time import get_shanghai_now


def get_database_url() -> str:
    if settings.USE_SQLITE:
        return "sqlite:///./feishu_rpa.db"
    return f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"


def get_sync_database_url() -> str:
    if settings.USE_SQLITE:
        return "sqlite:///./feishu_rpa.db"
    return f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"


engine = create_engine(get_sync_database_url(), pool_pre_ping=True, pool_size=10, connect_args={"check_same_thread": False} if settings.USE_SQLITE else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> sessionmaker:
    return SessionLocal


def init_db() -> None:
    from app.db.base import Base
    from app.db.models import MessageIdempotency, TaskRecord, TaskStep
    Base.metadata.create_all(bind=engine)


class DatabaseSession:
    def __init__(self):
        self.session = SessionLocal()

    def __enter__(self):
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.session.rollback()
        self.session.close()


def override_and_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()