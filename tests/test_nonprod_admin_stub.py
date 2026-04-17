from pathlib import Path

from fastapi.testclient import TestClient

from tools.nonprod_admin_stub import app as stub_app


def _client(monkeypatch, tmp_path: Path, fail_mode: str = ""):
    monkeypatch.setattr(stub_app, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(stub_app, "DB_PATH", tmp_path / "data" / "nonprod_stub.db")
    monkeypatch.setattr(stub_app, "FAIL_MODE", fail_mode)
    stub_app.init_db()
    return TestClient(stub_app.app)


def test_login_and_inventory_flow(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    resp = client.get("/login")
    assert resp.status_code == 200

    resp = client.post("/login", data={"username": "admin", "password": "admin123", "next": "/admin"}, follow_redirects=False)
    assert resp.status_code in {302, 303}

    cookies = resp.cookies
    home = client.get("/admin", cookies=cookies)
    assert home.status_code == 200
    assert "后台首页" in home.text

    inventory = client.get("/admin/inventory?sku=A001", cookies=cookies)
    assert inventory.status_code == 200
    assert "A001" in inventory.text
    assert "100" in inventory.text

    adjust = client.get("/admin/inventory/adjust?sku=A001", cookies=cookies)
    assert adjust.status_code == 200
    assert "库存调整" in adjust.text

    submit = client.post(
        "/admin/inventory/adjust",
        data={"sku": "A001", "delta": 5, "target_inventory": 105},
        cookies=cookies,
    )
    assert submit.status_code == 200
    assert "提交成功" in submit.text
    assert "105" in submit.text

    inventory_after = client.get("/admin/inventory?sku=A001", cookies=cookies)
    assert "105" in inventory_after.text


def test_session_invalid_guard(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    resp = client.get("/admin")
    assert resp.status_code == 200
    assert "未登录" in resp.text


def test_entry_not_ready_failure(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path, fail_mode="entry_not_ready")
    resp = client.post("/login", data={"username": "admin", "password": "admin123", "next": "/admin"}, follow_redirects=False)
    cookies = resp.cookies
    inventory = client.get("/admin/inventory", cookies=cookies)
    assert inventory.status_code == 200
    assert "入口未就绪" in inventory.text
