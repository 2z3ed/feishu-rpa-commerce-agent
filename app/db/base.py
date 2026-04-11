from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import declarative_base
from app.core.time import get_shanghai_now

Base = declarative_base()


class BaseModel(Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(DateTime, default=get_shanghai_now, nullable=False)
    updated_at = Column(DateTime, default=get_shanghai_now, onupdate=get_shanghai_now, nullable=False)