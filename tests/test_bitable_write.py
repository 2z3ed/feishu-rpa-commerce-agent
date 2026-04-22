"""Minimal tests for Feishu Bitable ledger append writes."""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.core.config import settings
from app.services.feishu import bitable_write as bitable_write_module
from app.services.feishu.bitable_write import check_bitable_readiness, try_write_bitable_ledger


def test_check_bitable_readiness_default_disabled(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_FEISHU_BITABLE_WRITE", False)
    monkeypatch.setattr(settings, "FEISHU_BITABLE_APP_TOKEN", "")
    monkeypatch.setattr(settings, "FEISHU_BITABLE_TABLE_ID", "")
    rd = check_bitable_readiness()
    assert rd["bitable_write_enabled"] is False
    assert rd["bitable_write_allowed"] is False
    assert rd["bitable_reason"] == "bitable_write_disabled"
    assert rd["bitable_ledger_strategy"] == "append"


def test_check_bitable_config_incomplete_when_enabled(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_FEISHU_BITABLE_WRITE", True)
    monkeypatch.setattr(settings, "FEISHU_BITABLE_APP_TOKEN", "")
    monkeypatch.setattr(settings, "FEISHU_BITABLE_TABLE_ID", "")
    rd = check_bitable_readiness()
    assert rd["bitable_config_ready"] is False
    assert rd["bitable_write_allowed"] is False
    assert "FEISHU_BITABLE_APP_TOKEN" in rd["bitable_missing"]
    assert "FEISHU_BITABLE_TABLE_ID" in rd["bitable_missing"]


def _minimal_task_record(task_id: str = "TASK-BITABLE-1"):
    return SimpleNamespace(
        task_id=task_id,
        target_task_id=None,
        task_type="ingress",
        intent_text="查询 SKU A001",
        status="succeeded",
        result_summary="SKU: A001",
        error_message="",
        created_at=None,
        updated_at=None,
    )


def test_try_write_skipped_when_disabled(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_FEISHU_BITABLE_WRITE", False)
    with patch("app.services.feishu.bitable_write.log_step") as m:
        try_write_bitable_ledger(
            task_id="TASK-BITABLE-1",
            graph_result={
                "intent_code": "product.query_sku_status",
                "status": "succeeded",
                "query_product_data": {"sku": "A001", "product_name": "x", "inventory": 1, "price": 9.9, "platform": "mock"},
                "result_summary": "SKU: A001",
            },
            task_record=_minimal_task_record(),
            db=MagicMock(),
        )
    codes = [c[0][1] for c in m.call_args_list]
    assert "bitable_write_skipped" in codes


def test_try_write_failed_when_enabled_but_config_missing(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_FEISHU_BITABLE_WRITE", True)
    monkeypatch.setattr(settings, "FEISHU_BITABLE_APP_TOKEN", "")
    monkeypatch.setattr(settings, "FEISHU_BITABLE_TABLE_ID", "")
    with patch("app.services.feishu.bitable_write.log_step") as m:
        try_write_bitable_ledger(
            task_id="TASK-BITABLE-2",
            graph_result={
                "intent_code": "product.query_sku_status",
                "status": "succeeded",
                "query_product_data": {"sku": "A001"},
                "result_summary": "x",
            },
            task_record=_minimal_task_record("TASK-BITABLE-2"),
            db=MagicMock(),
        )
    codes = [c[0][1] for c in m.call_args_list]
    assert "bitable_write_failed" in codes


def test_try_write_ledger_no_op_for_unknown_intent(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_FEISHU_BITABLE_WRITE", True)
    monkeypatch.setattr(settings, "FEISHU_BITABLE_APP_TOKEN", "tok")
    monkeypatch.setattr(settings, "FEISHU_BITABLE_TABLE_ID", "tbl")
    tr = SimpleNamespace(
        task_id="TASK-X",
        target_task_id=None,
        task_type="ingress",
        intent_text="x",
        status="succeeded",
        result_summary="",
        error_message="",
        created_at=None,
        updated_at=None,
    )
    db = MagicMock()
    with patch("app.services.feishu.bitable_write.log_step") as m:
        try_write_bitable_ledger(
            task_id="TASK-X",
            graph_result={"intent_code": "unknown", "status": "succeeded"},
            task_record=tr,
            db=db,
        )
    started = [c for c in m.call_args_list if c[0][1] == "bitable_write_started"]
    assert len(started) == 0


def test_try_write_ledger_update_price_awaiting_calls_append(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_FEISHU_BITABLE_WRITE", True)
    monkeypatch.setattr(settings, "FEISHU_BITABLE_APP_TOKEN", "tok")
    monkeypatch.setattr(settings, "FEISHU_BITABLE_TABLE_ID", "tbl")
    tr = SimpleNamespace(
        task_id="TASK-UP-1",
        target_task_id=None,
        task_type="ingress",
        intent_text="改价",
        status="awaiting_confirmation",
        result_summary="请确认",
        error_message="",
        created_at=None,
        updated_at=None,
    )
    with patch("app.services.feishu.bitable_write._bitable_append_row") as append:
        try_write_bitable_ledger(
            task_id="TASK-UP-1",
            graph_result={
                "intent_code": "product.update_price",
                "status": "awaiting_confirmation",
                "slots": {"sku": "A001", "target_price": 9.9},
            },
            task_record=tr,
            db=MagicMock(),
        )
    append.assert_called_once()
    assert append.call_args.kwargs["kind"] == "update_price_awaiting"


def test_try_write_ledger_adjust_inventory_success_calls_append(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_FEISHU_BITABLE_WRITE", True)
    monkeypatch.setattr(settings, "FEISHU_BITABLE_APP_TOKEN", "tok")
    monkeypatch.setattr(settings, "FEISHU_BITABLE_TABLE_ID", "tbl")
    tr = SimpleNamespace(
        task_id="TASK-P9C-1",
        target_task_id="TASK-P9C-ORIG-1",
        task_type="ingress",
        intent_text="确认执行 TASK-P9C-ORIG-1",
        status="succeeded",
        result_summary="A001 库存已从 100 调整到 105，RPA 执行成功，核验通过",
        error_message="",
        created_at=None,
        updated_at=None,
        finished_at=None,
    )
    db = MagicMock()
    q = db.query.return_value
    q.filter.return_value = q
    q.order_by.return_value = q
    q.first.return_value = ("intent=system.confirm_task, provider_id=odoo, capability=warehouse.adjust_inventory, execution_mode=rpa, run_id=TASK-P9C-1, operation_result=write_adjust_inventory, verify_passed=True, verify_reason=post_inventory_matches_target, old_inventory=100, target_inventory=105, post_inventory=105, page_failure_code=, failure_layer=, page_steps=open_entry|ensure_session|search_sku|open_editor|input_inventory|submit_change|read_feedback|verify_result, page_evidence_count=1, screenshot_paths=/tmp/shot.png, raw_result_path=/tmp/runtime-result.json",)
    monkeypatch.setattr("app.services.feishu.bitable_write._resolve_rpa_evidence_table_id", lambda app_token: "tbl_rpa")
    with patch("app.services.feishu.bitable_write._bitable_append_row") as append:
        try_write_bitable_ledger(
            task_id="TASK-P9C-1",
            graph_result={
                "intent_code": "warehouse.adjust_inventory",
                "status": "succeeded",
                "execution_mode": "rpa",
                "capability": "warehouse.adjust_inventory",
                "slots": {"sku": "A001"},
                "parsed_result": {
                    "run_id": "TASK-P9C-1",
                    "old_inventory": 100,
                    "target_inventory": 105,
                    "post_inventory": 105,
                    "verify_passed": True,
                    "verify_reason": "post_inventory_matches_target",
                    "page_steps": ["open_entry", "verify_result"],
                    "page_evidence_count": 1,
                    "screenshot_paths": ["/tmp/shot.png"],
                    "raw_result_path": "/tmp/runtime-result.json",
                    "operation_result": "write_adjust_inventory",
                },
            },
            task_record=tr,
            db=db,
        )
    append.assert_called_once()
    assert append.call_args.kwargs["kind"] == "adjust_inventory_rpa_success"
    fields = append.call_args.kwargs["fields"]
    assert fields["台账类型"] == "rpa_runtime_success"
    assert fields["task_id"] == "TASK-P9C-1"
    assert fields["run_id"] == "TASK-P9C-1"
    assert fields["sku"] == "A001"
    assert fields["old_inventory"] == 100
    assert fields["target_inventory"] == 105
    assert fields["new_inventory"] == 105
    assert fields["verify_passed"] is True


def test_resolve_rpa_evidence_table_id_prefers_named_table(monkeypatch):
    monkeypatch.setattr(
        "app.services.feishu.bitable_write._fetch_tenant_access_token",
        lambda: "tenant-token",
    )

    class _Resp:
        def raise_for_status(self):
            return None

        @property
        def content(self):
            return b"x"

        def json(self):
            return {
                "code": 0,
                "data": {
                    "items": [
                        {"name": "数据表", "table_id": "tbl_default"},
                        {"name": "RPA执行证据台账", "table_id": "tbl_rpa"},
                    ]
                },
            }

    monkeypatch.setattr(bitable_write_module.requests, "get", lambda *args, **kwargs: _Resp())
    out = bitable_write_module._resolve_rpa_evidence_table_id("app_tok")
    assert out == "tbl_rpa"
