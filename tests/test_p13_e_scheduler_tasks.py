import pytest

pytest.importorskip("celery")

from app.clients.b_service_client import BServiceClient
from app.tasks.scheduler_tasks import schedule_refresh_monitor_prices
from app.workers.celery_app import celery_app


def test_b_service_client_refresh_monitor_prices_supports_trigger_source(monkeypatch):
    captured: dict = {}

    def _fake_post(self, path: str, payload: dict):  # type: ignore[no-untyped-def]
        captured["path"] = path
        captured["payload"] = payload
        return {"ok": True}

    monkeypatch.setattr(BServiceClient, "_post_envelope_data", _fake_post)
    client = BServiceClient(base_url="http://example.com")
    client.refresh_monitor_prices(trigger_source="scheduled")
    assert captured["path"] == "/internal/monitor/refresh-prices?trigger_source=scheduled"
    assert captured["payload"] == {}


def test_b_service_client_replace_monitor_target_url_uses_patch(monkeypatch):
    captured: dict = {}

    def _fake_request(self, **kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs)
        return {"target_id": 12}

    monkeypatch.setattr(BServiceClient, "_request_envelope_data", _fake_request)
    client = BServiceClient(base_url="http://example.com")
    out = client.replace_monitor_target_url(12, "https://example.com/p/12")
    assert captured["method"] == "PATCH"
    assert captured["path"] == "/internal/monitor/12/url"
    assert captured["json_payload"] == {"product_url": "https://example.com/p/12"}
    assert out["target_id"] == 12


def test_schedule_refresh_monitor_prices_calls_b_with_scheduled(monkeypatch):
    called: dict = {}

    def _fake_refresh(self, trigger_source: str | None = None):  # type: ignore[no-untyped-def]
        called["trigger_source"] = trigger_source
        return {"run_id": "PRR-20260425-ABCD", "total": 10, "changed": 2, "failed": 0}

    monkeypatch.setattr(BServiceClient, "refresh_monitor_prices", _fake_refresh)
    result = schedule_refresh_monitor_prices.run()
    assert called["trigger_source"] == "scheduled"
    assert result["status"] == "success"
    assert result["run_id"] == "PRR-20260425-ABCD"
    assert result["total"] == 10
    assert result["changed"] == 2
    assert result["failed"] == 0


def test_schedule_refresh_monitor_prices_handles_exception(monkeypatch):
    def _fake_refresh(self, trigger_source: str | None = None):  # type: ignore[no-untyped-def]
        raise RuntimeError("boom")

    monkeypatch.setattr(BServiceClient, "refresh_monitor_prices", _fake_refresh)
    result = schedule_refresh_monitor_prices.run()
    assert result["status"] == "failed"
    assert "boom" in result["error"]


def test_celery_beat_registers_p13e_schedule():
    schedule_conf = celery_app.conf.beat_schedule
    assert "refresh-monitor-prices-every-5-minutes" in schedule_conf
    entry = schedule_conf["refresh-monitor-prices-every-5-minutes"]
    assert entry["task"] == "app.tasks.scheduler_tasks.schedule_refresh_monitor_prices"
