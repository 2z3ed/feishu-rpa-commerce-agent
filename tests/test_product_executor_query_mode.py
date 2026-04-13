from app.executors.product_executor import (
    EXECUTION_MODE_API,
    EXECUTION_MODE_MOCK,
    EXECUTION_MODE_RPA,
    get_product_executor,
    resolve_query_platform,
    resolve_execution_mode,
)
from app.clients.product_auth_provider import get_auth_headers
from app.clients.product_provider_profile import (
    ProductProviderConfigInvalidError,
    ProductProviderUnsupportedError,
    list_provider_ids,
    resolve_provider_profile,
    validate_provider_runtime,
)
from app.clients.product_provider_readiness import (
    check_platform_provider_readiness,
    check_query_provider_readiness,
)
from app.clients.product_request_adapter import (
    ProductApiRequestAdapterError,
    build_query_sku_request,
)
from app.clients.woo_readonly_prep import evaluate_woo_readonly_prep
from app.clients.product_credential_contract import ProductCredentialInvalidError
from app.core.config import settings
from app.graph.nodes.execute_action import execute_action
from fastapi.testclient import TestClient
from app.main import app


def test_query_sku_mock_mode_unchanged():
    state = {
        "intent_code": "product.query_sku_status",
        "slots": {"sku": "A001", "platform": "mock"},
        "execution_mode": "mock",
        "status": "processing",
    }
    result = execute_action(state)
    assert result["status"] == "succeeded"
    assert result["execution_mode"] == "mock"
    assert result["execution_backend"] == "mock_repo"
    assert "SKU: A001" in result["result_summary"]
    assert "平台：mock" in result["result_summary"]


def test_query_sku_api_executor_returns_unified_structure():
    old_woo = settings.WOO_API_TOKEN
    try:
        settings.WOO_API_TOKEN = "dev-token"
        executor = get_product_executor(EXECUTION_MODE_API)
        data = executor.query_sku_status("A001", "woo")
    finally:
        settings.WOO_API_TOKEN = old_woo
    assert data is not None
    assert set(data.keys()) == {"sku", "product_name", "status", "inventory", "price", "platform"}
    assert data["sku"] == "A001"
    assert data["platform"] == "woo"
    assert data["product_name"].startswith("Woo商品")


def test_query_sku_api_executor_not_found_returns_none():
    old_woo = settings.WOO_API_TOKEN
    try:
        settings.WOO_API_TOKEN = "dev-token"
        executor = get_product_executor(EXECUTION_MODE_API)
        data = executor.query_sku_status("NOT_EXISTS_SKU", "woo")
    finally:
        settings.WOO_API_TOKEN = old_woo
    assert data is None


def test_query_sku_api_mode_exception_path():
    old_woo = settings.WOO_API_TOKEN
    old_dry = settings.WOO_ENABLE_READONLY_DRY_RUN
    settings.WOO_API_TOKEN = "dev-token"
    settings.WOO_ENABLE_READONLY_DRY_RUN = False
    state = {
        "intent_code": "product.query_sku_status",
        "slots": {"sku": "ERR_TIMEOUT", "platform": "woo"},
        "execution_mode": "api",
        "status": "processing",
    }
    result = execute_action(state)
    assert result["execution_mode"] == "api"
    assert result["execution_backend"] == "sandbox_http_client"
    assert result["status"] == "failed"
    assert "[client_timeout]" in result["result_summary"]
    assert "sandbox_http@" in result["client_profile"]
    settings.WOO_API_TOKEN = old_woo
    settings.WOO_ENABLE_READONLY_DRY_RUN = old_dry


def test_query_sku_supports_api_mode_switch():
    old_value = settings.PRODUCT_QUERY_SKU_DEFAULT_EXECUTION_MODE
    old_rpa = settings.PRODUCT_QUERY_SKU_ENABLE_REAL_ADMIN_READONLY
    try:
        settings.PRODUCT_QUERY_SKU_DEFAULT_EXECUTION_MODE = "mock"
        settings.PRODUCT_QUERY_SKU_ENABLE_REAL_ADMIN_READONLY = False
        assert resolve_execution_mode("product.query_sku_status", "api") == EXECUTION_MODE_API
        assert resolve_execution_mode("product.query_sku_status", "mock") == EXECUTION_MODE_MOCK
        assert resolve_execution_mode("product.query_sku_status", "rpa") == EXECUTION_MODE_MOCK
        settings.PRODUCT_QUERY_SKU_ENABLE_REAL_ADMIN_READONLY = True
        assert resolve_execution_mode("product.query_sku_status", "rpa") == EXECUTION_MODE_RPA
    finally:
        settings.PRODUCT_QUERY_SKU_DEFAULT_EXECUTION_MODE = old_value
        settings.PRODUCT_QUERY_SKU_ENABLE_REAL_ADMIN_READONLY = old_rpa


def test_query_sku_default_mode_uses_dev_config():
    old_value = settings.PRODUCT_QUERY_SKU_DEFAULT_EXECUTION_MODE
    old_rpa = settings.PRODUCT_QUERY_SKU_ENABLE_REAL_ADMIN_READONLY
    try:
        settings.PRODUCT_QUERY_SKU_DEFAULT_EXECUTION_MODE = "api"
        settings.PRODUCT_QUERY_SKU_ENABLE_REAL_ADMIN_READONLY = True
        assert resolve_execution_mode("product.query_sku_status", None) == EXECUTION_MODE_API
        settings.PRODUCT_QUERY_SKU_DEFAULT_EXECUTION_MODE = "rpa"
        assert resolve_execution_mode("product.query_sku_status", None) == EXECUTION_MODE_RPA
        settings.PRODUCT_QUERY_SKU_ENABLE_REAL_ADMIN_READONLY = False
        assert resolve_execution_mode("product.query_sku_status", None) == EXECUTION_MODE_MOCK
        settings.PRODUCT_QUERY_SKU_DEFAULT_EXECUTION_MODE = "invalid"
        assert resolve_execution_mode("product.query_sku_status", None) == EXECUTION_MODE_MOCK
    finally:
        settings.PRODUCT_QUERY_SKU_DEFAULT_EXECUTION_MODE = old_value
        settings.PRODUCT_QUERY_SKU_ENABLE_REAL_ADMIN_READONLY = old_rpa


def test_query_sku_default_platform_uses_dev_config():
    old_value = settings.PRODUCT_QUERY_SKU_DEFAULT_PLATFORM
    try:
        settings.PRODUCT_QUERY_SKU_DEFAULT_PLATFORM = "odoo"
        assert resolve_query_platform("api", None) == "odoo"
        settings.PRODUCT_QUERY_SKU_DEFAULT_PLATFORM = "invalid"
        assert resolve_query_platform("api", None) == "sandbox"
        assert resolve_query_platform("mock", None) == "mock"
    finally:
        settings.PRODUCT_QUERY_SKU_DEFAULT_PLATFORM = old_value


def test_query_sku_api_mode_with_explicit_platform():
    old_woo = settings.WOO_API_TOKEN
    old_dry = settings.WOO_ENABLE_READONLY_DRY_RUN
    old_fb = settings.WOO_ENABLE_READONLY_DRY_RUN_FALLBACK
    settings.WOO_API_TOKEN = "dev-token"
    settings.WOO_ENABLE_READONLY_DRY_RUN = False
    settings.WOO_ENABLE_READONLY_DRY_RUN_FALLBACK = True
    state = {
        "intent_code": "product.query_sku_status",
        "slots": {"sku": "A001", "platform": "woo"},
        "execution_mode": "api",
        "status": "processing",
    }
    result = execute_action(state)
    assert result["execution_mode"] == "api"
    assert result["execution_backend"] == "sandbox_http_client"
    assert "sandbox_http@" in result["client_profile"]
    assert result["response_mapper"] == "woo_mapper"
    assert result["request_adapter"] == "woo_request_adapter"
    assert result["auth_profile"] == "woo_auth_profile"
    assert result["provider_profile"] == "woo"
    assert result["status"] == "succeeded"
    assert "平台：woo" in result["result_summary"]
    assert result["platform"] == "woo"
    assert result["dry_run_enabled"] == "false"
    assert result["selected_backend"] == "sandbox_http_client"
    assert result["recommended_strategy"] == "dry_run_with_fallback"
    assert result["environment_ready"] == "unknown"
    assert result["live_probe_enabled"] in {"true", "false"}
    assert result["fallback_enabled"] == "true"
    assert result["fallback_applied"] == "false"
    assert result["final_backend"] == "sandbox_http_client"
    settings.WOO_API_TOKEN = old_woo
    settings.WOO_ENABLE_READONLY_DRY_RUN = old_dry
    settings.WOO_ENABLE_READONLY_DRY_RUN_FALLBACK = old_fb


def test_query_sku_api_mode_not_found_still_succeeds_with_not_found_payload():
    state = {
        "intent_code": "product.query_sku_status",
        "slots": {"sku": "NOT_EXISTS_SKU", "platform": "sandbox"},
        "execution_mode": "api",
        "status": "processing",
    }
    result = execute_action(state)
    assert result["execution_mode"] == "api"
    assert result["execution_backend"] == "sandbox_http_client"
    assert "sandbox_http@" in result["client_profile"]
    assert result["response_mapper"] == "sandbox_mapper"
    assert result["status"] == "succeeded"
    assert "状态：not_found" in result["result_summary"]


def test_query_sku_api_mode_with_odoo_mapper():
    old_odoo = settings.ODOO_SESSION_ID
    settings.ODOO_SESSION_ID = "odoo-session-001"
    state = {
        "intent_code": "product.query_sku_status",
        "slots": {"sku": "A001", "platform": "odoo"},
        "execution_mode": "api",
        "status": "processing",
    }
    result = execute_action(state)
    assert result["execution_mode"] == "api"
    assert result["status"] == "succeeded"
    assert result["platform"] == "odoo"
    assert result["response_mapper"] == "odoo_mapper"
    assert result["request_adapter"] == "odoo_request_adapter"
    assert result["auth_profile"] == "odoo_auth_profile"
    assert result["provider_profile"] == "odoo"
    assert "平台：odoo" in result["result_summary"]
    settings.ODOO_SESSION_ID = old_odoo


def test_query_sku_api_mode_client_error_path():
    state = {
        "intent_code": "product.query_sku_status",
        "slots": {"sku": "ERR_CLIENT", "platform": "sandbox"},
        "execution_mode": "api",
        "status": "processing",
    }
    result = execute_action(state)
    assert result["execution_mode"] == "api"
    assert result["execution_backend"] == "sandbox_http_client"
    assert result["status"] == "failed"
    assert "[client_error]" in result["result_summary"]


def test_query_sku_api_mode_sandbox_disabled_path():
    old_enabled = settings.ENABLE_INTERNAL_SANDBOX_API
    try:
        settings.ENABLE_INTERNAL_SANDBOX_API = False
        state = {
            "intent_code": "product.query_sku_status",
            "slots": {"sku": "A001", "platform": "sandbox"},
            "execution_mode": "api",
            "status": "processing",
        }
        result = execute_action(state)
        assert result["execution_mode"] == "api"
        assert result["execution_backend"] == "sandbox_http_client"
        assert result["status"] == "failed"
        assert "[provider_config_invalid]" in result["result_summary"]
    finally:
        settings.ENABLE_INTERNAL_SANDBOX_API = old_enabled


def test_query_sku_api_mode_mapper_error_path():
    old_woo = settings.WOO_API_TOKEN
    old_dry = settings.WOO_ENABLE_READONLY_DRY_RUN
    settings.WOO_API_TOKEN = "dev-token"
    settings.WOO_ENABLE_READONLY_DRY_RUN = False
    state = {
        "intent_code": "product.query_sku_status",
        "slots": {"sku": "ERR_MAPPER", "platform": "woo"},
        "execution_mode": "api",
        "status": "processing",
    }
    result = execute_action(state)
    assert result["execution_mode"] == "api"
    assert result["execution_backend"] == "sandbox_http_client"
    assert result["response_mapper"] == "woo_mapper"
    assert result["status"] == "failed"
    assert "[mapper_error]" in result["result_summary"]
    settings.WOO_API_TOKEN = old_woo
    settings.WOO_ENABLE_READONLY_DRY_RUN = old_dry


def test_request_adapter_generates_platform_specific_request_meta():
    old_woo = settings.WOO_API_TOKEN
    old_ver = settings.WOO_API_VERSION_PREFIX
    old_odoo = settings.ODOO_SESSION_ID
    try:
        settings.WOO_API_TOKEN = "dev-token"
        settings.WOO_API_VERSION_PREFIX = "wp-json/wc/v3"
        settings.ODOO_SESSION_ID = "odoo-session-001"
        sandbox_req = build_query_sku_request("sandbox", "A001", resolve_provider_profile("sandbox"))
        woo_req = build_query_sku_request("woo", "A001", resolve_provider_profile("woo"))
        odoo_req = build_query_sku_request("odoo", "A001", resolve_provider_profile("odoo"))
    finally:
        settings.WOO_API_TOKEN = old_woo
        settings.WOO_API_VERSION_PREFIX = old_ver
        settings.ODOO_SESSION_ID = old_odoo
    assert sandbox_req.request_adapter == "sandbox_request_adapter"
    assert woo_req.request_adapter == "woo_request_adapter"
    assert odoo_req.request_adapter == "odoo_request_adapter"
    assert "/provider/sandbox/sku/" in sandbox_req.path
    assert woo_req.path == "/api/v1/internal/sandbox/provider/woo/wp-json/wc/v3/products"
    assert woo_req.params["sku"] == "A001"
    assert woo_req.params["per_page"] == "1"
    assert "X-Woo-Auth-Shape" in woo_req.headers
    assert "X-Woo-Auth-Mode" in woo_req.headers
    assert "/provider/odoo/product/" in odoo_req.path


def test_auth_provider_differs_by_platform():
    old_woo = settings.WOO_API_TOKEN
    old_odoo = settings.ODOO_SESSION_ID
    try:
        settings.WOO_API_TOKEN = "dev-token"
        settings.ODOO_SESSION_ID = "odoo-session-001"
        sandbox_profile, sandbox_cred, _, sandbox_headers = get_auth_headers("sandbox")
        woo_profile, woo_cred, _, woo_headers = get_auth_headers("woo")
        odoo_profile, odoo_cred, _, odoo_headers = get_auth_headers("odoo")
    finally:
        settings.WOO_API_TOKEN = old_woo
        settings.ODOO_SESSION_ID = old_odoo
    assert sandbox_profile == "sandbox_auth_profile"
    assert sandbox_cred == "sandbox_credential_profile"
    assert woo_profile == "woo_auth_profile"
    assert woo_cred == "woo_credential_profile"
    assert odoo_profile == "odoo_auth_profile"
    assert odoo_cred == "odoo_credential_profile"
    assert "X-Sandbox-Key" in sandbox_headers
    assert "X-Woo-Token" in woo_headers
    assert "X-Odoo-Session" in odoo_headers


def test_request_adapter_error_path():
    try:
        build_query_sku_request("bad_platform", "A001", resolve_provider_profile("sandbox"))
        assert False, "expected ProductApiRequestAdapterError"
    except (ProductApiRequestAdapterError, ProductCredentialInvalidError):
        assert True


def test_provider_profile_unsupported_path():
    try:
        resolve_provider_profile("not_supported")
        assert False, "expected ProductProviderUnsupportedError"
    except ProductProviderUnsupportedError:
        assert True


def test_provider_profile_config_invalid_timeout():
    profile = resolve_provider_profile("sandbox")
    try:
        validate_provider_runtime(
            profile=profile,
            intent_code="product.query_sku_status",
            base_url="internal://sandbox",
            timeout_ms=0,
            internal_sandbox_enabled=True,
        )
        assert False, "expected ProductProviderConfigInvalidError"
    except ProductProviderConfigInvalidError:
        assert True


def test_provider_readiness_sandbox_ok():
    result = check_query_provider_readiness("sandbox")
    assert result.ready is True
    assert result.provider_name == "sandbox"
    assert result.reason == "ready"


def test_provider_readiness_woo_ok():
    old_woo = settings.WOO_API_TOKEN
    old_base = settings.WOO_BASE_URL
    old_dry = settings.WOO_ENABLE_READONLY_DRY_RUN
    old_fb = settings.WOO_ENABLE_READONLY_DRY_RUN_FALLBACK
    old_probe = settings.WOO_ENABLE_READONLY_LIVE_PROBE
    try:
        settings.WOO_API_TOKEN = "dev-token"
        settings.WOO_BASE_URL = "https://woo.example.local"
        settings.WOO_ENABLE_READONLY_DRY_RUN = False
        settings.WOO_ENABLE_READONLY_DRY_RUN_FALLBACK = True
        settings.WOO_ENABLE_READONLY_LIVE_PROBE = False
        result = check_query_provider_readiness("woo")
    finally:
        settings.WOO_API_TOKEN = old_woo
        settings.WOO_BASE_URL = old_base
        settings.WOO_ENABLE_READONLY_DRY_RUN = old_dry
        settings.WOO_ENABLE_READONLY_DRY_RUN_FALLBACK = old_fb
        settings.WOO_ENABLE_READONLY_LIVE_PROBE = old_probe
    assert result.ready is True
    assert result.provider_name == "woo"
    assert result.request_adapter == "woo_request_adapter"
    assert result.credential_ready is True
    assert result.credential_profile == "woo_credential_profile"
    assert result.sandbox_ready is True
    assert result.production_shape_ready is True
    assert result.production_config_ready is True
    assert result.woo_readonly_prep["auth_mode"] == "token_header"
    assert result.dry_run_enabled is False
    assert result.selected_backend == "sandbox_http_client"
    assert result.fallback_enabled is True
    assert result.fallback_target == "sandbox_http_client"
    assert result.effective_backend_strategy == "sandbox_only"
    assert result.recommended_strategy == "dry_run_with_fallback"
    assert result.strategy_deviation is True
    assert result.live_probe_enabled is False


def test_provider_readiness_odoo_ok():
    old_odoo = settings.ODOO_SESSION_ID
    try:
        settings.ODOO_SESSION_ID = "odoo-session-001"
        result = check_query_provider_readiness("odoo")
    finally:
        settings.ODOO_SESSION_ID = old_odoo
    assert result.ready is True
    assert result.provider_name == "odoo"
    assert result.response_mapper == "odoo_mapper"
    assert result.credential_ready is True
    assert result.credential_profile == "odoo_credential_profile"


def test_provider_registry_includes_multi_platform_connectors():
    ids = list_provider_ids()
    assert "woo" in ids
    assert "odoo" in ids
    assert "chatwoot" in ids


def test_provider_readiness_chatwoot_ok():
    result = check_platform_provider_readiness("chatwoot", capability="customer.list_recent_conversations")
    assert result.ready is True
    assert result.provider_name == "chatwoot"
    assert result.reason == "ready"
    assert result.credential_profile == "chatwoot_credential_profile"


def test_provider_readiness_unsupported():
    result = check_query_provider_readiness("not_supported")
    assert result.ready is False
    assert result.reason == "provider_unsupported"


def test_provider_readiness_config_invalid_timeout():
    old_timeout = settings.PRODUCT_QUERY_SKU_API_TIMEOUT_MS
    try:
        settings.PRODUCT_QUERY_SKU_API_TIMEOUT_MS = 0
        result = check_query_provider_readiness("sandbox")
        assert result.ready is False
        assert result.reason == "invalid_timeout"
    finally:
        settings.PRODUCT_QUERY_SKU_API_TIMEOUT_MS = old_timeout


def test_provider_readiness_internal_sandbox_disabled():
    old_enabled = settings.ENABLE_INTERNAL_SANDBOX_API
    try:
        settings.ENABLE_INTERNAL_SANDBOX_API = False
        result = check_query_provider_readiness("sandbox")
        assert result.ready is False
        assert result.reason == "internal_sandbox_disabled"
    finally:
        settings.ENABLE_INTERNAL_SANDBOX_API = old_enabled


def test_provider_readiness_woo_missing_credential():
    old_woo = settings.WOO_API_TOKEN
    old_base = settings.WOO_BASE_URL
    try:
        settings.WOO_API_TOKEN = ""
        settings.WOO_BASE_URL = "https://woo.example.local"
        result = check_query_provider_readiness("woo")
        assert result.ready is False
        assert result.reason == "credential_missing"
        assert "WOO_API_TOKEN" in result.missing_config_keys
    finally:
        settings.WOO_API_TOKEN = old_woo
        settings.WOO_BASE_URL = old_base


def test_provider_readiness_woo_production_config_not_ready_when_base_url_missing():
    old_woo = settings.WOO_API_TOKEN
    old_base = settings.WOO_BASE_URL
    old_dry = settings.WOO_ENABLE_READONLY_DRY_RUN
    try:
        settings.WOO_API_TOKEN = "dev-token"
        settings.WOO_BASE_URL = ""
        settings.WOO_ENABLE_READONLY_DRY_RUN = True
        result = check_query_provider_readiness("woo")
    finally:
        settings.WOO_API_TOKEN = old_woo
        settings.WOO_BASE_URL = old_base
        settings.WOO_ENABLE_READONLY_DRY_RUN = old_dry
    assert result.ready is True
    assert result.production_shape_ready is True
    assert result.production_config_ready is False
    assert "WOO_BASE_URL" in result.woo_readonly_prep["missing_config_keys"]
    assert result.selected_backend == "sandbox_http_client"


def test_provider_readiness_woo_selects_dry_run_backend_when_enabled_and_ready():
    old_woo = settings.WOO_API_TOKEN
    old_base = settings.WOO_BASE_URL
    old_dry = settings.WOO_ENABLE_READONLY_DRY_RUN
    old_fb = settings.WOO_ENABLE_READONLY_DRY_RUN_FALLBACK
    old_probe = settings.WOO_ENABLE_READONLY_LIVE_PROBE
    try:
        settings.WOO_API_TOKEN = "dev-token"
        settings.WOO_BASE_URL = "https://woo.example.local"
        settings.WOO_ENABLE_READONLY_DRY_RUN = True
        settings.WOO_ENABLE_READONLY_DRY_RUN_FALLBACK = True
        settings.WOO_ENABLE_READONLY_LIVE_PROBE = False
        result = check_query_provider_readiness("woo")
    finally:
        settings.WOO_API_TOKEN = old_woo
        settings.WOO_BASE_URL = old_base
        settings.WOO_ENABLE_READONLY_DRY_RUN = old_dry
        settings.WOO_ENABLE_READONLY_DRY_RUN_FALLBACK = old_fb
        settings.WOO_ENABLE_READONLY_LIVE_PROBE = old_probe
    assert result.production_config_ready is True
    assert result.dry_run_enabled is True
    assert result.selected_backend == "woo_http_dry_run_client"
    assert result.effective_backend_strategy == "dry_run_with_fallback"
    assert result.recommended_strategy == "dry_run_with_fallback"
    assert result.strategy_deviation is False


def test_query_sku_api_mode_woo_dry_run_backend_path():
    old_woo = settings.WOO_API_TOKEN
    old_base = settings.WOO_BASE_URL
    old_dry = settings.WOO_ENABLE_READONLY_DRY_RUN
    old_fb = settings.WOO_ENABLE_READONLY_DRY_RUN_FALLBACK
    try:
        settings.WOO_API_TOKEN = "dev-token"
        settings.WOO_BASE_URL = "http://127.0.0.1:9"
        settings.WOO_ENABLE_READONLY_DRY_RUN = True
        settings.WOO_ENABLE_READONLY_DRY_RUN_FALLBACK = False
        state = {
            "intent_code": "product.query_sku_status",
            "slots": {"sku": "A001", "platform": "woo"},
            "execution_mode": "api",
            "status": "processing",
        }
        result = execute_action(state)
    finally:
        settings.WOO_API_TOKEN = old_woo
        settings.WOO_BASE_URL = old_base
        settings.WOO_ENABLE_READONLY_DRY_RUN = old_dry
        settings.WOO_ENABLE_READONLY_DRY_RUN_FALLBACK = old_fb
    assert result["execution_mode"] == "api"
    assert result["platform"] == "woo"
    assert result["execution_backend"] == "woo_http_dry_run_client"
    assert result["selected_backend"] == "woo_http_dry_run_client"
    assert result["dry_run_enabled"] == "true"
    assert result["fallback_enabled"] == "false"
    assert result["fallback_applied"] == "false"
    assert result["dry_run_failure"] in {"dry_run_client_error", "dry_run_timeout", "dry_run_not_ready"}
    assert result["status"] == "failed"
    assert "[dry_run_client_error]" in result["result_summary"] or "[dry_run_timeout]" in result["result_summary"]


def test_query_sku_api_mode_woo_dry_run_fallback_applied():
    old_woo = settings.WOO_API_TOKEN
    old_base = settings.WOO_BASE_URL
    old_dry = settings.WOO_ENABLE_READONLY_DRY_RUN
    old_fb = settings.WOO_ENABLE_READONLY_DRY_RUN_FALLBACK
    old_internal = settings.ENABLE_INTERNAL_SANDBOX_API
    try:
        settings.WOO_API_TOKEN = "dev-token"
        settings.WOO_BASE_URL = "http://127.0.0.1:9"
        settings.WOO_ENABLE_READONLY_DRY_RUN = True
        settings.WOO_ENABLE_READONLY_DRY_RUN_FALLBACK = True
        settings.ENABLE_INTERNAL_SANDBOX_API = True
        state = {
            "intent_code": "product.query_sku_status",
            "slots": {"sku": "A001", "platform": "woo"},
            "execution_mode": "api",
            "status": "processing",
        }
        result = execute_action(state)
    finally:
        settings.WOO_API_TOKEN = old_woo
        settings.WOO_BASE_URL = old_base
        settings.WOO_ENABLE_READONLY_DRY_RUN = old_dry
        settings.WOO_ENABLE_READONLY_DRY_RUN_FALLBACK = old_fb
        settings.ENABLE_INTERNAL_SANDBOX_API = old_internal
    assert result["status"] == "succeeded"
    assert result["platform"] == "woo"
    assert result["selected_backend"] == "woo_http_dry_run_client"
    assert result["final_backend"] == "sandbox_http_client"
    assert result["fallback_applied"] == "true"
    assert "fallback_applied" in result["backend_selection_reason"]


def test_woo_readonly_prep_query_key_secret_mode_requires_key_and_secret():
    old_mode = settings.WOO_AUTH_MODE
    old_base = settings.WOO_BASE_URL
    old_key = settings.WOO_API_KEY
    old_secret = settings.WOO_API_SECRET
    try:
        settings.WOO_AUTH_MODE = "query_key_secret"
        settings.WOO_BASE_URL = "https://woo.example.local"
        settings.WOO_API_KEY = ""
        settings.WOO_API_SECRET = ""
        prep = evaluate_woo_readonly_prep()
    finally:
        settings.WOO_AUTH_MODE = old_mode
        settings.WOO_BASE_URL = old_base
        settings.WOO_API_KEY = old_key
        settings.WOO_API_SECRET = old_secret
    assert prep.production_config_ready is False
    assert "WOO_API_KEY" in prep.missing_config_keys
    assert "WOO_API_SECRET" in prep.missing_config_keys


def test_provider_readiness_odoo_missing_credential():
    old_odoo = settings.ODOO_SESSION_ID
    try:
        settings.ODOO_SESSION_ID = ""
        result = check_query_provider_readiness("odoo")
        assert result.ready is False
        assert result.reason == "credential_missing"
        assert "ODOO_SESSION_ID" in result.missing_config_keys
    finally:
        settings.ODOO_SESSION_ID = old_odoo


def test_provider_readiness_odoo_invalid_credential():
    old_odoo = settings.ODOO_SESSION_ID
    try:
        settings.ODOO_SESSION_ID = "x1"
        result = check_query_provider_readiness("odoo")
        assert result.ready is False
        assert result.reason == "credential_invalid"
    finally:
        settings.ODOO_SESSION_ID = old_odoo


def test_internal_readiness_endpoint():
    client = TestClient(app)
    resp = client.get("/api/v1/internal/readiness/query-sku-provider", params={"provider": "sandbox"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["provider_name"] == "sandbox"
    assert "ready" in body


def test_internal_environment_readiness_endpoint():
    client = TestClient(app)
    resp = client.get("/api/v1/internal/readiness/environment")
    assert resp.status_code == 200
    body = resp.json()
    assert "redis_ready" in body
    assert "feishu_network_ready" in body
    assert "environment_ready" in body
    for key in (
        "dns_ready",
        "tcp_ready",
        "tls_ready",
        "target_host",
        "broker_host",
        "proxy_enabled",
        "proxy_source",
        "proxy_env",
        "feishu_resolved",
        "bitable_write_enabled",
        "bitable_config_ready",
        "bitable_write_allowed",
        "bitable_reason",
        "bitable_missing",
        "bitable_ledger_strategy",
    ):
        assert key in body


def test_update_price_stays_mock_mode():
    state = {
        "intent_code": "product.update_price",
        "slots": {"sku": "A001", "target_price": 49.9},
        "execution_mode": "api",
        "task_id": "TASK-MODE-KEEP-MOCK",
        "raw_text": "修改 SKU A001 价格到 49.9",
        "status": "processing",
    }
    result = execute_action(state)
    assert result["execution_mode"] == "mock"
    assert result["status"] == "awaiting_confirmation"
    assert "请回复：确认执行 TASK-MODE-KEEP-MOCK" in result["result_summary"]


def test_query_sku_rpa_mode_dispatches_real_admin_bridge(monkeypatch):
    old_enable = settings.PRODUCT_QUERY_SKU_ENABLE_REAL_ADMIN_READONLY
    try:
        settings.PRODUCT_QUERY_SKU_ENABLE_REAL_ADMIN_READONLY = True

        def fake_rpa_query(*, task_id: str, trace_id: str, sku: str):
            assert task_id == "TASK-QUERY-RPA-1"
            assert sku == "A001"
            return (
                {
                    "query_result": {
                        "sku": "A001",
                        "product_name": "Mirror A001",
                        "status": "ok",
                        "inventory": 9,
                        "price": 59.9,
                        "platform": "woo",
                        "read_source": "browser_real",
                        "profile": "real_admin_prepared",
                        "detail_loaded": True,
                        "target_sku_hit": True,
                        "evidence_count": 3,
                    },
                    "_rpa_meta": {
                        "execution_backend": "rpa_browser_real",
                        "selected_backend": "rpa_browser_real",
                        "final_backend": "rpa_browser_real",
                        "rpa_runner": "browser_real",
                        "verify_mode": "basic",
                        "evidence_count": 3,
                        "platform": "woo",
                    },
                },
                None,
            )

        monkeypatch.setattr("app.graph.nodes.execute_action.run_query_sku_status_real_admin_readonly", fake_rpa_query)
        state = {
            "intent_code": "product.query_sku_status",
            "slots": {"sku": "A001"},
            "execution_mode": "rpa",
            "task_id": "TASK-QUERY-RPA-1",
            "status": "processing",
        }
        result = execute_action(state)
        assert result["status"] == "succeeded"
        assert result["execution_mode"] == "rpa"
        assert result["execution_backend"] == "rpa_browser_real"
        assert result["rpa_runner"] == "browser_real"
        assert result["evidence_count"] == 3
        assert result["platform"] == "woo"
    finally:
        settings.PRODUCT_QUERY_SKU_ENABLE_REAL_ADMIN_READONLY = old_enable


def test_odoo_inventory_route_succeeds_in_task_chain():
    state = {
        "intent_code": "warehouse.query_inventory",
        "slots": {"sku": "A001", "platform": "odoo"},
        "execution_mode": "api",
        "status": "processing",
    }
    result = execute_action(state)
    assert result["status"] == "succeeded"
    assert result["platform"] == "odoo"
    assert result["provider_id"] == "odoo"
    assert result["capability"] == "warehouse.query_inventory"
    assert "库存：" in result["result_summary"]


def test_chatwoot_recent_conversations_route_succeeds_in_task_chain():
    state = {
        "intent_code": "customer.list_recent_conversations",
        "slots": {"limit": 3, "platform": "chatwoot"},
        "execution_mode": "api",
        "status": "processing",
    }
    result = execute_action(state)
    assert result["status"] == "succeeded"
    assert result["platform"] == "chatwoot"
    assert result["provider_id"] == "chatwoot"
    assert result["capability"] == "customer.list_recent_conversations"
    assert "最近会话数：3" in result["result_summary"]
