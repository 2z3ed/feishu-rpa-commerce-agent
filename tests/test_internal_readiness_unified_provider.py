import importlib
import sys
import types

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import settings


def test_unified_provider_readiness_endpoint_for_three_platforms(monkeypatch):
    fake_lark = types.ModuleType("lark_oapi")

    class _Client:
        pass

    fake_lark.Client = _Client
    monkeypatch.setitem(sys.modules, "lark_oapi", fake_lark)
    readiness_router = importlib.import_module("app.api.v1.internal_readiness").router

    monkeypatch.setattr(settings, "ENABLE_INTERNAL_SANDBOX_API", True)
    monkeypatch.setattr(settings, "WOO_API_TOKEN", "dev-token")
    monkeypatch.setattr(settings, "WOO_BASE_URL", "https://woo.example.local")
    monkeypatch.setattr(settings, "ODOO_SESSION_ID", "odoo-session-001")

    app = FastAPI()
    app.include_router(readiness_router, prefix="/api/v1")
    client = TestClient(app)

    cases = [
        ("woo", "product.query_sku_status"),
        ("odoo", "warehouse.query_inventory"),
        ("chatwoot", "customer.list_recent_conversations"),
    ]
    for provider, capability in cases:
        resp = client.get(
            "/api/v1/internal/readiness/unified-provider",
            params={"provider": provider, "capability": capability},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["provider_id"] == provider
        assert body["capability"] == capability
        for key in (
            "ready",
            "credential_ready",
            "sandbox_ready",
            "production_shape_ready",
            "production_config_ready",
            "recommended_strategy",
            "reason",
            "reasons",
        ):
            assert key in body
        assert isinstance(body["reasons"], list)
        assert all(isinstance(x, str) and x.strip() for x in body["reasons"])
