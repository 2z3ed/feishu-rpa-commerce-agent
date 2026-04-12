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

    # RAG / Milvus (optional enhancement layer; default off).
    # Milvus command_interpretation rows should set intent_hint to match intent (e.g. product.query_sku_status / product.update_price).
    # Graph skips command_interpretation when intent is unknown; failure tasks use failure_explanation in finalize_result.
    ENABLE_RAG: bool = False
    MILVUS_COLLECTION_NAME: str = ""
    RAG_TOP_K: int = 5
    RAG_SCORE_THRESHOLD: float = 0.0
    # Must match collection vector dim (embedding field)
    RAG_EMBEDDING_DIM: int = 128
    RAG_USE_CASE_ENABLED_COMMAND_INTERPRETATION: bool = True
    RAG_USE_CASE_ENABLED_RULE_AUGMENT: bool = True
    RAG_USE_CASE_ENABLED_FAILURE_EXPLANATION: bool = True

    FEISHU_APP_ID: str = ""
    FEISHU_APP_SECRET: str = ""
    FEISHU_BOT_NAME: str = "commerce-agent-bot"
    # 群聊 @ 机器人判定：im.message.receive_v1 的 mentions 为 mention_event（仅 key/id/name/tenant_key），
    # 需与 mentions[].id.open_id 比对；请在开放平台「我的应用」或相关接口获取本应用机器人的 open_id。
    FEISHU_BOT_OPEN_ID: str = ""

    # Feishu Bitable (multidimensional table) — one-way write, optional
    ENABLE_FEISHU_BITABLE_WRITE: bool = False
    FEISHU_BITABLE_APP_TOKEN: str = ""
    FEISHU_BITABLE_TABLE_ID: str = ""

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

    # --- RPA (dev-stage; confirm-phase for product.update_price only) ---
    # Post-confirm execution: mock (default) | rpa — not exposed to Feishu users.
    PRODUCT_UPDATE_PRICE_CONFIRM_EXECUTION_BACKEND: str = "mock"
    RPA_EVIDENCE_BASE_DIR: str = "data/rpa_evidence"
    RPA_UPDATE_PRICE_TIMEOUT_S: int = 180
    # Allowed: none | basic | strict
    RPA_UPDATE_PRICE_VERIFY_MODE: str = "basic"
    # When true, RPA success does not mutate mock product_repo (dev inspection).
    RPA_UPDATE_PRICE_DRY_RUN: bool = False
    RPA_RUNNER_NAME: str = "local_fake"
    # Test / dev: force LocalFakeRpaRunner to fail after evidence (failure screenshot).
    RPA_FAKE_RUNNER_FORCE_FAILURE: bool = False
    # Reserved; keep false — api_then_rpa_verify not implemented this phase.
    RPA_API_THEN_RPA_VERIFY_ENABLED: bool = False

    # P3.1 — real browser runner (Playwright) against local sandbox only (not production).
    # Allowed: local_fake | browser_real (default: local_fake)
    RPA_RUNNER_TYPE: str = "local_fake"
    RPA_BROWSER_HEADLESS: bool = True
    # Base URL to reach this FastAPI app from the worker (Playwright navigates here).
    RPA_SANDBOX_BASE_URL: str = "http://127.0.0.1:8000"
    # Page load + selector wait budget (seconds); separate from RPA_UPDATE_PRICE_TIMEOUT_S graph budget.
    RPA_BROWSER_TIMEOUT_S: int = 30
    # Dev: force sandbox page to return error after submit (browser runner only).
    RPA_BROWSER_FORCE_FAILURE: bool = False

    # P3.2 — browser_real target: minimal internal page vs admin-like workbench (not production).
    # Allowed: sandbox | admin_like | list_detail (list_detail = hub → catalog → detail → save)
    RPA_TARGET_ENV: str = "sandbox"
    # Optional override for admin-like entry + workbench; defaults to RPA_SANDBOX_BASE_URL.
    RPA_ADMIN_LIKE_BASE_URL: str = ""
    # admin_like only: none | sku_missing | save_error | save_disabled
    RPA_ADMIN_LIKE_FORCE_FAILURE_MODE: str = "none"

    # P3.3 — list → detail → edit (internal only). Base URL; empty = RPA_SANDBOX_BASE_URL.
    RPA_LIST_DETAIL_BASE_URL: str = ""
    # list_detail only: none | sku_missing_in_list | detail_page_not_found | save_button_disabled | save_error
    RPA_LIST_DETAIL_FORCE_FAILURE_MODE: str = "none"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()