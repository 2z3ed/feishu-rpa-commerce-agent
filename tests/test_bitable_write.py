"""Minimal tests for Feishu Bitable one-way write (query_sku success only)."""
from unittest.mock import patch

from app.core.config import settings
from app.services.feishu.bitable_write import check_bitable_readiness, try_write_query_sku_bitable


def test_check_bitable_readiness_default_disabled(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_FEISHU_BITABLE_WRITE", False)
    monkeypatch.setattr(settings, "FEISHU_BITABLE_APP_TOKEN", "")
    monkeypatch.setattr(settings, "FEISHU_BITABLE_TABLE_ID", "")
    rd = check_bitable_readiness()
    assert rd["bitable_write_enabled"] is False
    assert rd["bitable_write_allowed"] is False
    assert rd["bitable_reason"] == "bitable_write_disabled"


def test_check_bitable_config_incomplete_when_enabled(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_FEISHU_BITABLE_WRITE", True)
    monkeypatch.setattr(settings, "FEISHU_BITABLE_APP_TOKEN", "")
    monkeypatch.setattr(settings, "FEISHU_BITABLE_TABLE_ID", "")
    rd = check_bitable_readiness()
    assert rd["bitable_config_ready"] is False
    assert rd["bitable_write_allowed"] is False
    assert "FEISHU_BITABLE_APP_TOKEN" in rd["bitable_missing"]
    assert "FEISHU_BITABLE_TABLE_ID" in rd["bitable_missing"]


def test_try_write_skipped_when_disabled(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_FEISHU_BITABLE_WRITE", False)
    with patch("app.services.feishu.bitable_write.log_step") as m:
        try_write_query_sku_bitable(
            task_id="TASK-BITABLE-1",
            graph_result={
                "intent_code": "product.query_sku_status",
                "status": "succeeded",
                "query_product_data": {"sku": "A001", "product_name": "x", "inventory": 1, "price": 9.9, "platform": "mock"},
                "result_summary": "SKU: A001",
            },
            intent_text="查询 SKU A001",
        )
    codes = [c[0][1] for c in m.call_args_list]
    assert "bitable_write_skipped" in codes


def test_try_write_failed_when_enabled_but_config_missing(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_FEISHU_BITABLE_WRITE", True)
    monkeypatch.setattr(settings, "FEISHU_BITABLE_APP_TOKEN", "")
    monkeypatch.setattr(settings, "FEISHU_BITABLE_TABLE_ID", "")
    with patch("app.services.feishu.bitable_write.log_step") as m:
        try_write_query_sku_bitable(
            task_id="TASK-BITABLE-2",
            graph_result={
                "intent_code": "product.query_sku_status",
                "status": "succeeded",
                "query_product_data": {"sku": "A001"},
                "result_summary": "x",
            },
            intent_text="q",
        )
    codes = [c[0][1] for c in m.call_args_list]
    assert "bitable_write_failed" in codes


def test_try_write_not_run_for_non_query_intent():
    with patch("app.services.feishu.bitable_write.log_step") as m:
        try_write_query_sku_bitable(
            task_id="TASK-X",
            graph_result={"intent_code": "product.update_price", "status": "succeeded"},
            intent_text="x",
        )
    m.assert_not_called()
