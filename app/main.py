import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import logger
from app.api.router import api_router
from app.db.session import init_db


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="飞书自然语言驱动的电商后台智能助手 - MVP Ingress",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting {settings.APP_NAME} - MVP Ingress Mode")
    try:
        init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning(f"Database init warning: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info(f"Shutting down {settings.APP_NAME}")


app.include_router(api_router)


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": "0.1.0",
        "mode": "MVP Ingress",
        "description": "飞书长连接接收消息 -> 解析 -> 幂等 -> 入队 -> 回执"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.APP_ENV == "development",
    )