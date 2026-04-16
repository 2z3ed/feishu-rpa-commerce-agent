from fastapi.testclient import TestClient

from app.api.v1 import internal_rpa_admin_like as pages


def test_inventory_pages_render_in_app():
    # Build a minimal FastAPI app to mount the router for rendering tests.
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(pages.router, prefix="/api/v1")
    client = TestClient(app)

    r1 = client.get("/api/v1/internal/rpa-sandbox/admin-like/inventory")
    assert r1.status_code == 200
    assert "data-testid=\"inventory-dashboard-root\"" in r1.text
    assert "data-testid=\"nonprod-badge\"" in r1.text

    r2 = client.get("/api/v1/internal/rpa-sandbox/admin-like/inventory/adjust?sku=A001&old_inventory=100&delta=5&target_inventory=105")
    assert r2.status_code == 200
    body = r2.text
    assert "data-testid=\"inventory-adjust-root\"" in body
    assert "data-testid=\"inv-sku-search\"" in body
    assert "data-testid=\"inv-table\"" in body
    assert "data-testid=\"inventory-adjust-drawer\"" in body
    assert "data-testid=\"inv-result\"" in body

