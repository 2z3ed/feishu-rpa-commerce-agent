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
    B_SERVICE_BASE_URL: str = "http://127.0.0.1:8005"

    # P14-A: LLM intent fallback (default off, only for rule-miss).
    ENABLE_LLM_INTENT_FALLBACK: bool = False
    LLM_INTENT_PROVIDER: str = "mock"
    LLM_INTENT_MODEL: str = ""
    LLM_INTENT_TIMEOUT_SECONDS: int = 8
    LLM_INTENT_CONFIDENCE_THRESHOLD: float = 0.75

    # Feishu Bitable (multidimensional table) — one-way write, optional
    ENABLE_FEISHU_BITABLE_WRITE: bool = False
    FEISHU_BITABLE_APP_TOKEN: str = ""
    FEISHU_BITABLE_TABLE_ID: str = ""
    FEISHU_RPA_EVIDENCE_TABLE_ID: str = ""

    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # SQLite 作为本地开发备选
    USE_SQLITE: bool = False

    # Dev-only switch for product.query_sku_status executor path.
    # Allowed: mock | api | rpa (rpa requires PRODUCT_QUERY_SKU_ENABLE_REAL_ADMIN_READONLY=true)
    PRODUCT_QUERY_SKU_DEFAULT_EXECUTION_MODE: str = "mock"
    PRODUCT_QUERY_SKU_ENABLE_REAL_ADMIN_READONLY: bool = False

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
    # Post-confirm execution: mock | rpa | api_then_rpa_verify — not exposed to Feishu users.
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
    # Legacy no-op: use PRODUCT_UPDATE_PRICE_CONFIRM_EXECUTION_BACKEND=api_then_rpa_verify instead.
    RPA_API_THEN_RPA_VERIFY_ENABLED: bool = False
    # P3.4 dev only: page URL shows a wrong current_price so readback mismatches API (tests / manual).
    RPA_API_THEN_RPA_VERIFY_FORCE_PAGE_MISMATCH: bool = False

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

    # P4.1 — target profile: internal controlled pages (default) vs real admin prep (config/readiness only).
    RPA_TARGET_PROFILE: str = "internal_controlled"
    # Real admin (preparation only; no production write automation in P4.1).
    RPA_REAL_ADMIN_BASE_URL: str = ""
    RPA_REAL_ADMIN_HOME_PATH: str = ""
    RPA_REAL_ADMIN_CATALOG_PATH: str = ""
    # Must include literal {sku}, e.g. /admin/products/edit?sku={sku}
    RPA_REAL_ADMIN_DETAIL_PATH_TEMPLATE: str = ""
    # Query param name or field name used to search SKU on list/catalog (documentation + readiness).
    RPA_REAL_ADMIN_SKU_SEARCH_PARAM: str = ""
    RPA_REAL_ADMIN_SKU_SEARCH_NOTES: str = ""
    # P4.2 — 只读读回（CSS 选择器；真实后台请按 DOM 填写；本地 mirror 见 internal_rpa_real_admin_mirror）
    RPA_REAL_ADMIN_DETAIL_PRICE_SELECTOR: str = ""
    RPA_REAL_ADMIN_CATALOG_EMPTY_SELECTOR: str = ""
    RPA_REAL_ADMIN_DETAIL_SKU_SELECTOR: str = ""
    RPA_REAL_ADMIN_DETAIL_STATUS_SELECTOR: str = ""
    RPA_REAL_ADMIN_DETAIL_MESSAGE_SELECTOR: str = ""
    RPA_REAL_ADMIN_DETAIL_PRODUCT_NAME_SELECTOR: str = ""
    # api_then_rpa_verify 比对用；空则回退为请求 target_price
    RPA_REAL_ADMIN_DETAIL_NEW_PRICE_SELECTOR: str = ""
    # P4.5 — real_admin_prepared 写链（RPA 页面写入 + 写后核验）
    RPA_REAL_ADMIN_DETAIL_SAVE_BUTTON_SELECTOR: str = ""
    RPA_REAL_ADMIN_DETAIL_SAVE_RESULT_SELECTOR: str = ""
    # P4.6 — 写后比对容差（默认 0.009；建议与币种/展示格式匹配）
    RPA_REAL_ADMIN_PRICE_COMPARE_TOLERANCE: float = 0.009
    # Session injection (no password automation): Cookie header value or JSON headers.
    RPA_REAL_ADMIN_SESSION_COOKIE: str = ""
    RPA_REAL_ADMIN_SESSION_HEADERS_JSON: str = ""
    # Optional: merged into Playwright extra_http_headers for all browser_real runs (JSON object).
    RPA_BROWSER_EXTRA_HTTP_HEADERS_JSON: str = ""
    # Optional: {"localStorage":{"k":"v"},"sessionStorage":{}} applied before first navigation.
    RPA_BROWSER_STORAGE_INIT_JSON: str = ""
    # Optional safe GET probe to home URL when structurally ready (default off).
    RPA_REAL_ADMIN_READINESS_HTTP_PROBE: bool = False
    RPA_REAL_ADMIN_READINESS_PROBE_TIMEOUT_S: int = 5

    # P7.0 PoC — local Yingdao bridge (no console/API dependency).
    # Allowed: internal_sandbox | yingdao_bridge
    ODOO_ADJUST_INVENTORY_CONFIRM_EXECUTION_BACKEND: str = "internal_sandbox"
    YINGDAO_BRIDGE_BASE_URL: str = "http://127.0.0.1:17891"
    YINGDAO_BRIDGE_TIMEOUT_S: int = 30
    YINGDAO_BRIDGE_ENVIRONMENT: str = "local_poc"
    # Local bridge file exchange dirs (bridge service side defaults).
    YINGDAO_BRIDGE_INPUT_DIR: str = "tmp/yingdao_bridge/inbox"
    YINGDAO_BRIDGE_OUTPUT_DIR: str = "tmp/yingdao_bridge/outbox"
    YINGDAO_BRIDGE_WAIT_TIMEOUT_S: int = 20
    YINGDAO_BRIDGE_POLL_INTERVAL_MS: int = 200
    # P7.1 PoC — controlled page minimal execution chain (still non-production).
    # Allowed: file_exchange | controlled_page | real_nonprod_page
    YINGDAO_BRIDGE_EXECUTION_MODE: str = "file_exchange"
    YINGDAO_CONTROLLED_PAGE_BASE_URL: str = "http://127.0.0.1:8000"
    YINGDAO_CONTROLLED_PAGE_PROFILE: str = "internal_inventory_adjust_v1"
    YINGDAO_REAL_NONPROD_PAGE_BASE_URL: str = "http://127.0.0.1:18081"
    YINGDAO_REAL_NONPROD_PAGE_PROFILE: str = "real_nonprod_page"
    YINGDAO_REAL_NONPROD_PAGE_ENTRY_URL: str = "http://127.0.0.1:18081/login"
    YINGDAO_REAL_NONPROD_PAGE_ADMIN_ENTRY_URL: str = "http://127.0.0.1:18081/admin"
    YINGDAO_REAL_NONPROD_PAGE_SESSION_MODE: str = "cookie"
    YINGDAO_REAL_NONPROD_PAGE_SESSION_COOKIE_NAME: str = "nonprod_stub_session"
    YINGDAO_REAL_NONPROD_PAGE_SESSION_COOKIE_VALUE: str = "admin-session"
    YINGDAO_REAL_NONPROD_PAGE_SEARCH_INPUT_SELECTOR: str = 'input[name="sku"]'
    YINGDAO_REAL_NONPROD_PAGE_SEARCH_BUTTON_SELECTOR: str = 'button[type="submit"]'
    YINGDAO_REAL_NONPROD_PAGE_RESULT_ROW_SELECTOR: str = "table"
    YINGDAO_REAL_NONPROD_PAGE_EDITOR_ENTRY_SELECTOR: str = "/admin/inventory/adjust?sku=A001"
    YINGDAO_REAL_NONPROD_PAGE_EDITOR_CONTAINER_SELECTOR: str = ".card"
    YINGDAO_REAL_NONPROD_PAGE_INVENTORY_INPUT_SELECTOR: str = 'input[name="delta"]'
    YINGDAO_REAL_NONPROD_PAGE_SUBMIT_BUTTON_SELECTOR: str = 'button[type="submit"]'
    YINGDAO_REAL_NONPROD_PAGE_SUCCESS_TOAST_SELECTOR: str = ".msg-ok"
    YINGDAO_REAL_NONPROD_PAGE_ERROR_TOAST_SELECTOR: str = ".msg-err"
    YINGDAO_REAL_NONPROD_PAGE_VERIFY_FIELD_SELECTOR: str = 'a[href^="/admin/inventory?sku="]'

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()