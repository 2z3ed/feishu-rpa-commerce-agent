import os
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "feishu-rpa-commerce-agent"
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    TZ: str = "Asia/Shanghai"
    LOG_LEVEL: str = "INFO"

    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "feishu_rpa"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530

    FEISHU_APP_ID: str = ""
    FEISHU_APP_SECRET: str = ""
    FEISHU_BOT_NAME: str = "commerce-agent-bot"

    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # SQLite 作为本地开发备选
    USE_SQLITE: bool = False

    # Dev-only switch for product.query_sku_status executor path.
    # Allowed: mock | api (default: mock)
    PRODUCT_QUERY_SKU_DEFAULT_EXECUTION_MODE: str = "mock"

    # Dev-only default platform for product.query_sku_status.
    # Allowed: mock | woo | odoo | sandbox (default: sandbox)
    PRODUCT_QUERY_SKU_DEFAULT_PLATFORM: str = "sandbox"

    # Dev-only query_sku_status api sandbox client settings.
    # Use "internal://sandbox" to call in-process FastAPI sandbox endpoint.
    PRODUCT_QUERY_SKU_API_BASE_URL: str = "internal://sandbox"
    PRODUCT_QUERY_SKU_API_TIMEOUT_MS: int = 2000
    ENABLE_INTERNAL_SANDBOX_API: bool = True

    # Backward-compatible alias (deprecated naming).
    PRODUCT_QUERY_SKU_SANDBOX_BASE_URL: str = "internal://sandbox"

    # Dev credential placeholders for provider auth contract (query_sku_status api path only).
    WOO_API_TOKEN: str = ""
    WOO_API_KEY: str = ""
    WOO_API_SECRET: str = ""
    # Woo read-only production prep config (no real production call in this phase).
    WOO_BASE_URL: str = ""
    WOO_API_VERSION_PREFIX: str = "wp-json/wc/v3"
    # Allowed: token_header | query_key_secret
    WOO_AUTH_MODE: str = "token_header"
    WOO_READONLY_TIMEOUT_MS: int = 2000
    WOO_ALLOW_INTERNAL_SANDBOX_FALLBACK: bool = True
    WOO_ENABLE_READONLY_DRY_RUN: bool = False
    WOO_ENABLE_READONLY_DRY_RUN_FALLBACK: bool = True
    # Guarded live readonly probe entry (disabled by default).
    WOO_ENABLE_READONLY_LIVE_PROBE: bool = False
    WOO_LIVE_BASE_URL: str = ""
    WOO_LIVE_TIMEOUT_MS: int = 2000
    ODOO_SESSION_ID: str = ""
    ODOO_DB: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()