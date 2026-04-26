from app.clients.b_service_client import BServiceError
from app.graph.nodes.execute_action import _build_monitor_targets_context, execute_action
from app.graph.nodes.resolve_intent import resolve_intent


def test_resolve_today_summary_intent():
    state = {"normalized_text": "今天有什么变化"}
    out = resolve_intent(state)
    assert out["intent_code"] == "ecom_watch.summary_today"


def test_resolve_monitor_targets_intent():
    state = {"normalized_text": "看看当前监控对象"}
    out = resolve_intent(state)
    assert out["intent_code"] == "ecom_watch.monitor_targets"


def test_resolve_refresh_monitor_prices_intent():
    for text in ("刷新监控价格", "刷新监控对象价格", "刷新价格"):
        state = {"normalized_text": text}
        out = resolve_intent(state)
        assert out["intent_code"] == "ecom_watch.refresh_monitor_prices"


def test_resolve_monitor_probe_query_intent():
    cases = {
        "查看价格采集失败": "failed",
        "查看采集失败对象": "failed",
        "查看mock价格对象": "mock",
        "查看真实价格对象": "real",
    }
    for text, expected in cases.items():
        state = {"normalized_text": text}
        out = resolve_intent(state)
        assert out["intent_code"] == "ecom_watch.monitor_probe_query"
        assert out["slots"]["query_type"] == expected


def test_resolve_monitor_diagnostics_query_intent():
    cases = {
        "查看价格异常对象": "price_anomaly",
        "查看低可信价格对象": "low_confidence",
        "查看价格监控状态": "monitor_status",
        "价格监控概览": "monitor_overview",
    }
    for text, expected in cases.items():
        out = resolve_intent({"normalized_text": text})
        assert out["intent_code"] == "ecom_watch.monitor_diagnostics_query"
        assert out["slots"]["query_type"] == expected


def test_resolve_retry_price_probe_intents():
    batch_cases = ("重试价格采集", "重试采集失败对象", "重试mock价格对象")
    for text in batch_cases:
        out = resolve_intent({"normalized_text": text})
        assert out["intent_code"] == "ecom_watch.retry_price_probes"

    single_cases = {
        "重试对象 7 价格采集": 7,
        "重试对象ID 7 价格采集": 7,
    }
    for text, expected_id in single_cases.items():
        out = resolve_intent({"normalized_text": text})
        assert out["intent_code"] == "ecom_watch.retry_price_probe"
        assert out["slots"]["target_id"] == expected_id


def test_resolve_replace_monitor_target_url_intent():
    out = resolve_intent({"normalized_text": "替换监控对象URL 12 https://example.com/products/12"})
    assert out["intent_code"] == "ecom_watch.replace_monitor_target_url"
    assert out["slots"]["target_id"] == 12
    assert out["slots"]["product_url"] == "https://example.com/products/12"


def test_resolve_refresh_monitor_target_price_intent():
    out = resolve_intent({"normalized_text": "重新采集对象 12"})
    assert out["intent_code"] == "ecom_watch.refresh_monitor_target_price"
    assert out["slots"]["target_id"] == 12


def test_resolve_monitor_price_history_intent():
    state_1 = {"normalized_text": "查看价格历史 7"}
    out_1 = resolve_intent(state_1)
    assert out_1["intent_code"] == "ecom_watch.monitor_price_history"
    assert out_1["slots"]["target_id"] == 7
    assert out_1["slots"]["query_mode"] == "target_id"

    state_2 = {"normalized_text": "查看历史价格 7"}
    out_2 = resolve_intent(state_2)
    assert out_2["intent_code"] == "ecom_watch.monitor_price_history"
    assert out_2["slots"]["target_id"] == 7
    assert out_2["slots"]["query_mode"] == "target_id"

    state_3 = {"normalized_text": "查看对象ID 7 的价格历史"}
    out_3 = resolve_intent(state_3)
    assert out_3["intent_code"] == "ecom_watch.monitor_price_history"
    assert out_3["slots"]["target_id"] == 7
    assert out_3["slots"]["query_mode"] == "target_id"

    state_4 = {"normalized_text": "查看第 7 个价格历史"}
    out_4 = resolve_intent(state_4)
    assert out_4["intent_code"] == "ecom_watch.monitor_price_history"
    assert out_4["slots"]["list_index"] == 7
    assert out_4["slots"]["query_mode"] == "list_index"


def test_resolve_price_refresh_run_detail_intent():
    for text in (
        "查看刷新结果 PRR-20260425-ABCD",
        "查看价格刷新批次 prr-20260425-ab12",
        "查看刷新批次 PRR-20260425-XYZ9",
    ):
        out = resolve_intent({"normalized_text": text})
        assert out["intent_code"] == "ecom_watch.price_refresh_run_detail"
        assert out["slots"]["run_id"].startswith("PRR-20260425-")


def test_resolve_manage_monitor_target_allows_index_over_ten():
    state = {"normalized_text": "恢复监控第 12 个"}
    out = resolve_intent(state)
    assert out["intent_code"] == "ecom_watch.manage_monitor_target"
    assert out["slots"]["action"] == "resume"
    assert out["slots"]["index"] == 12


def test_resolve_product_detail_intent():
    state = {"normalized_text": "看看商品 123 的详情"}
    out = resolve_intent(state)
    assert out["intent_code"] == "ecom_watch.product_detail"
    assert out["slots"]["product_id"] == 123


def test_resolve_add_monitor_by_url_intent():
    state = {"normalized_text": "监控这个商品：https://example.com/product/abc"}
    out = resolve_intent(state)
    assert out["intent_code"] == "ecom_watch.add_monitor_by_url"
    assert out["slots"]["url"] == "https://example.com/product/abc"


def test_resolve_add_monitor_by_url_intent_alt_phrases():
    state_1 = {"normalized_text": "把这个链接加入监控：https://example.com/product/def"}
    out_1 = resolve_intent(state_1)
    assert out_1["intent_code"] == "ecom_watch.add_monitor_by_url"
    assert out_1["slots"]["url"] == "https://example.com/product/def"

    state_2 = {"normalized_text": "加入监控：https://example.com/product/ghi"}
    out_2 = resolve_intent(state_2)
    assert out_2["intent_code"] == "ecom_watch.add_monitor_by_url"
    assert out_2["slots"]["url"] == "https://example.com/product/ghi"


def test_resolve_add_monitor_by_url_intent_with_invalid_url_candidate():
    state = {"normalized_text": "加入监控：not-a-url"}
    out = resolve_intent(state)
    assert out["intent_code"] == "ecom_watch.add_monitor_by_url"
    assert out["slots"]["url"] == "not-a-url"


def test_resolve_discovery_search_intent():
    state = {"normalized_text": "搜索商品：wireless headphone"}
    out = resolve_intent(state)
    assert out["intent_code"] == "ecom_watch.discovery_search"
    assert out["slots"]["query"] == "wireless headphone"


def test_resolve_discovery_search_intent_alt_phrases():
    state_1 = {"normalized_text": "搜索：iphone case"}
    out_1 = resolve_intent(state_1)
    assert out_1["intent_code"] == "ecom_watch.discovery_search"
    assert out_1["slots"]["query"] == "iphone case"

    state_2 = {"normalized_text": "帮我找一下 privacy screen protector"}
    out_2 = resolve_intent(state_2)
    assert out_2["intent_code"] == "ecom_watch.discovery_search"
    assert out_2["slots"]["query"] == "privacy screen protector"


def test_resolve_add_from_candidates_intent():
    state_1 = {"normalized_text": "加入监控第 2 个"}
    out_1 = resolve_intent(state_1)
    assert out_1["intent_code"] == "ecom_watch.add_from_candidates"
    assert out_1["slots"]["index"] == 2

    state_2 = {"normalized_text": "监控第 1 个"}
    out_2 = resolve_intent(state_2)
    assert out_2["intent_code"] == "ecom_watch.add_from_candidates"
    assert out_2["slots"]["index"] == 1

    state_3 = {"normalized_text": "选第 3 个加入监控"}
    out_3 = resolve_intent(state_3)
    assert out_3["intent_code"] == "ecom_watch.add_from_candidates"
    assert out_3["slots"]["index"] == 3


def test_execute_summary_today_success(monkeypatch):
    def _fake_summary(self):
        return {
            "title": "今日变化",
            "summary": "价格波动 3 个，缺货 1 个",
            "highlights": ["A 商品降价", "B 商品补货"],
        }

    monkeypatch.setattr("app.clients.b_service_client.BServiceClient.get_today_summary", _fake_summary)
    state = {"intent_code": "ecom_watch.summary_today", "slots": {}, "status": "processing"}
    result = execute_action(state)
    assert result["status"] == "succeeded"
    assert "今日监控摘要" in result["result_summary"]


def test_execute_monitor_targets_success(monkeypatch):
    def _fake_targets(self):
        return {"targets": [{"id": 123, "name": "商品A", "status": "active"}]}

    monkeypatch.setattr("app.clients.b_service_client.BServiceClient.get_monitor_targets", _fake_targets)
    state = {"intent_code": "ecom_watch.monitor_targets", "slots": {}, "status": "processing"}
    result = execute_action(state)
    assert result["status"] == "succeeded"
    assert "ID=123" in result["result_summary"]


def test_execute_monitor_probe_query_failed_objects(monkeypatch):
    def _fake_targets(self):
        return {
            "targets": [
                {
                    "id": 1,
                    "name": "商品A",
                    "current_price": 100,
                    "price_source": "mock_price",
                    "price_probe_status": "fallback_mock",
                    "price_probe_error": "timeout",
                },
                {
                    "id": 2,
                    "name": "商品B",
                    "current_price": 200,
                    "price_source": "html_extract_preview",
                    "price_probe_status": "success",
                    "price_probe_error": None,
                },
            ]
        }

    monkeypatch.setattr("app.clients.b_service_client.BServiceClient.get_monitor_targets", _fake_targets)
    state = {
        "intent_code": "ecom_watch.monitor_probe_query",
        "slots": {"query_type": "failed"},
        "status": "processing",
    }
    result = execute_action(state)
    assert result["status"] == "succeeded"
    assert "价格采集失败对象（共 1 个）" in result["result_summary"]
    assert "状态：fallback_mock" in result["result_summary"]
    assert "原因：timeout" in result["result_summary"]


def test_execute_monitor_probe_query_mock_and_real(monkeypatch):
    def _fake_targets(self):
        return {
            "targets": [
                {
                    "id": 1,
                    "name": "商品A",
                    "current_price": 100,
                    "price_source": "mock_price",
                    "price_probe_status": "fallback_mock",
                    "price_probe_error": "timeout",
                },
                {
                    "id": 2,
                    "name": "商品B",
                    "current_price": 200,
                    "price_source": "html_extract_preview",
                    "price_probe_status": "success",
                    "price_probe_error": None,
                },
            ]
        }

    monkeypatch.setattr("app.clients.b_service_client.BServiceClient.get_monitor_targets", _fake_targets)
    mock_state = {
        "intent_code": "ecom_watch.monitor_probe_query",
        "slots": {"query_type": "mock"},
        "status": "processing",
    }
    mock_result = execute_action(mock_state)
    assert mock_result["status"] == "succeeded"
    assert "mock价格对象（共 1 个）" in mock_result["result_summary"]

    real_state = {
        "intent_code": "ecom_watch.monitor_probe_query",
        "slots": {"query_type": "real"},
        "status": "processing",
    }
    real_result = execute_action(real_state)
    assert real_result["status"] == "succeeded"
    assert "真实价格对象（共 1 个）" in real_result["result_summary"]


def test_execute_monitor_diagnostics_queries(monkeypatch):
    def _fake_targets(self):
        return {
            "targets": [
                {
                    "id": 1,
                    "name": "商品A",
                    "current_price": 15020,
                    "last_price": 1280,
                    "price_source": "html_extract_preview",
                    "price_probe_status": "success",
                    "price_confidence": "low",
                    "price_page_type": "listing_page",
                    "price_anomaly_status": "suspected",
                    "price_anomaly_reason": "当前价格超过 10000，疑似误提取",
                    "price_action_suggestion": "建议优先人工复查该对象价格来源。",
                },
                {
                    "id": 2,
                    "name": "商品B",
                    "current_price": 220.0,
                    "price_source": "mock_price",
                    "price_probe_status": "fallback_mock",
                    "price_confidence": "low",
                    "price_page_type": "mock_page",
                    "price_anomaly_status": "normal",
                    "price_action_suggestion": "建议先重试价格采集。",
                },
            ]
        }

    monkeypatch.setattr("app.clients.b_service_client.BServiceClient.get_monitor_targets", _fake_targets)

    anomaly_state = {
        "intent_code": "ecom_watch.monitor_diagnostics_query",
        "slots": {"query_type": "price_anomaly"},
        "status": "processing",
    }
    anomaly_result = execute_action(anomaly_state)
    assert anomaly_result["status"] == "succeeded"
    assert "价格异常对象（共 1 个）" in anomaly_result["result_summary"]
    assert "异常原因：当前价格超过 10000，疑似误提取" in anomaly_result["result_summary"]

    low_state = {
        "intent_code": "ecom_watch.monitor_diagnostics_query",
        "slots": {"query_type": "low_confidence"},
        "status": "processing",
    }
    low_result = execute_action(low_state)
    assert low_result["status"] == "succeeded"
    assert "低可信价格对象（共 2 个）" in low_result["result_summary"]

    status_state = {
        "intent_code": "ecom_watch.monitor_diagnostics_query",
        "slots": {"query_type": "monitor_status"},
        "status": "processing",
    }
    status_result = execute_action(status_state)
    assert status_result["status"] == "succeeded"
    assert "价格监控状态" in status_result["result_summary"]
    assert "异常价格：1" in status_result["result_summary"]

    overview_state = {
        "intent_code": "ecom_watch.monitor_diagnostics_query",
        "slots": {"query_type": "monitor_overview"},
        "status": "processing",
    }
    overview_result = execute_action(overview_state)
    assert overview_result["status"] == "succeeded"
    assert "建议：" in overview_result["result_summary"]


def test_execute_retry_price_probes_summary(monkeypatch):
    def _fake_retry(self, trigger_source: str | None = None):
        assert trigger_source == "manual_feishu"
        return {
            "run_id": "RPR-20260426-ABCD",
            "retried": 5,
            "total_candidates": 5,
            "success": 2,
            "still_failed": 3,
        }

    monkeypatch.setattr("app.clients.b_service_client.BServiceClient.retry_monitor_price_probes", _fake_retry)
    state = {"intent_code": "ecom_watch.retry_price_probes", "slots": {}, "status": "processing"}
    result = execute_action(state)
    assert result["status"] == "succeeded"
    assert "价格采集重试完成" in result["result_summary"]
    assert "重试对象：5 个" in result["result_summary"]
    assert "成功转真实价格：2 个" in result["result_summary"]
    assert "仍失败：3 个" in result["result_summary"]


def test_execute_retry_price_probe_single_success_and_failed(monkeypatch):
    success_payload = {
        "product_id": 6,
        "eligible": True,
        "retried": True,
        "price_probe_status": "success",
        "price_source": "html_extract_preview",
        "current_price": 1280.0,
    }
    failed_payload = {
        "product_id": 9,
        "eligible": True,
        "retried": True,
        "price_probe_status": "fallback_mock",
        "price_probe_error": "timeout",
        "price_source": "mock_price",
        "current_price": 210.0,
    }

    monkeypatch.setattr(
        "app.clients.b_service_client.BServiceClient.retry_monitor_target_price_probe",
        lambda self, target_id, trigger_source=None: success_payload if int(target_id) == 6 else failed_payload,
    )
    success_state = {
        "intent_code": "ecom_watch.retry_price_probe",
        "slots": {"target_id": 6},
        "status": "processing",
    }
    success_result = execute_action(success_state)
    assert success_result["status"] == "succeeded"
    assert "价格采集重试成功" in success_result["result_summary"]
    assert "对象ID：6" in success_result["result_summary"]
    assert "来源：html_extract_preview" in success_result["result_summary"]

    failed_state = {
        "intent_code": "ecom_watch.retry_price_probe",
        "slots": {"target_id": 9},
        "status": "processing",
    }
    failed_result = execute_action(failed_state)
    assert failed_result["status"] == "succeeded"
    assert "价格采集重试后仍未成功" in failed_result["result_summary"]
    assert "对象ID：9" in failed_result["result_summary"]
    assert "状态：fallback_mock" in failed_result["result_summary"]
    assert "原因：timeout" in failed_result["result_summary"]


def test_build_monitor_targets_context_keeps_price_fields():
    context = _build_monitor_targets_context(
        targets_data={
            "targets": [
                {
                    "product_id": 7,
                    "product_name": "商品A",
                    "status": "active",
                    "product_url": "https://a.example",
                    "current_price": 199.0,
                    "last_price": 209.0,
                    "price_delta": -10.0,
                    "price_delta_percent": -4.78,
                    "price_changed": True,
                    "last_checked_at": "2026-04-25T17:30:00",
                    "price_source": "mock_price",
                }
            ]
        }
    )
    target = context["targets"][0]
    assert target["target_id"] == 7
    assert target["current_price"] == 199.0
    assert target["last_price"] == 209.0
    assert target["price_delta"] == -10.0
    assert target["price_delta_percent"] == -4.78
    assert target["price_changed"] is True
    assert target["last_checked_at"] == "2026-04-25T17:30:00"
    assert target["price_source"] == "mock_price"


def test_execute_refresh_monitor_prices_success(monkeypatch):
    def _fake_refresh(self, trigger_source: str | None = None):
        assert trigger_source == "manual_feishu"
        return {
            "run_id": "PRR-20260425-ABCD",
            "status": "succeeded",
            "total": 8,
            "refreshed": 6,
            "changed": 2,
            "failed": 0,
            "duration_ms": 1200,
            "changed_items": [
                {
                    "product_id": 7,
                    "product_name": "商品A",
                    "current_price": 195,
                    "last_price": 190,
                    "price_delta": 5,
                    "price_delta_percent": 2.63,
                    "price_changed": True,
                    "price_source": "mock_price",
                    "last_checked_at": "2026-04-25T18:30:00",
                },
                {
                    "product_id": 8,
                    "product_name": "商品B",
                    "current_price": 180,
                    "last_price": 200,
                    "price_delta": -20,
                    "price_delta_percent": -10.0,
                    "price_changed": True,
                    "price_source": "mock_price",
                    "last_checked_at": "2026-04-25T18:31:00",
                },
            ],
        }

    monkeypatch.setattr("app.clients.b_service_client.BServiceClient.refresh_monitor_prices", _fake_refresh)
    state = {"intent_code": "ecom_watch.refresh_monitor_prices", "slots": {}, "status": "processing"}
    result = execute_action(state)
    assert result["status"] == "succeeded"
    assert "监控价格已刷新" in result["result_summary"]
    assert "刷新批次：PRR-20260425-ABCD" in result["result_summary"]
    assert "状态：succeeded" in result["result_summary"]
    assert "本轮价格变化：2" in result["result_summary"]
    assert "耗时：1200ms" in result["result_summary"]
    assert "1. 商品A" in result["result_summary"]
    assert "变化：上涨 5（+2.63%）" in result["result_summary"]
    assert "2. 商品B" in result["result_summary"]
    assert "变化：下降 20（-10.00%）" in result["result_summary"]
    assert "未变化：6 个" in result["result_summary"]
    assert "失败：0" in result["result_summary"]


def test_execute_refresh_monitor_prices_no_changes(monkeypatch):
    def _fake_refresh(self, trigger_source: str | None = None):
        assert trigger_source == "manual_feishu"
        return {
            "run_id": "PRR-20260425-ABCD",
            "status": "succeeded",
            "total": 10,
            "refreshed": 10,
            "changed": 0,
            "failed": 1,
            "duration_ms": 888,
            "items": [],
            "changed_items": [],
        }

    monkeypatch.setattr("app.clients.b_service_client.BServiceClient.refresh_monitor_prices", _fake_refresh)
    state = {"intent_code": "ecom_watch.refresh_monitor_prices", "slots": {}, "status": "processing"}
    result = execute_action(state)
    assert result["status"] == "succeeded"
    assert "本轮暂无价格变化" in result["result_summary"]
    assert "刷新批次：PRR-20260425-ABCD" in result["result_summary"]
    assert "成功刷新：10" in result["result_summary"]
    assert "失败：1" in result["result_summary"]
    assert "耗时：888ms" in result["result_summary"]


def test_execute_refresh_monitor_prices_show_top_five(monkeypatch):
    def _fake_refresh(self, trigger_source: str | None = None):
        assert trigger_source == "manual_feishu"
        changed_items = []
        for i in range(1, 8):
            changed_items.append(
                {
                    "product_id": i,
                    "product_name": f"商品{i}",
                    "current_price": 100 + i,
                    "last_price": 99 + i,
                    "price_delta": 1,
                    "price_delta_percent": 1.0,
                    "price_changed": True,
                    "price_source": "mock_price",
                    "last_checked_at": "2026-04-25T18:30:00",
                }
            )
        return {
            "run_id": "PRR-20260425-ABCD",
            "status": "succeeded",
            "total": 9,
            "refreshed": 9,
            "changed": 7,
            "failed": 0,
            "duration_ms": 1000,
            "changed_items": changed_items,
        }

    monkeypatch.setattr("app.clients.b_service_client.BServiceClient.refresh_monitor_prices", _fake_refresh)
    state = {"intent_code": "ecom_watch.refresh_monitor_prices", "slots": {}, "status": "processing"}
    result = execute_action(state)
    assert result["status"] == "succeeded"
    assert "1. 商品1" in result["result_summary"]
    assert "5. 商品5" in result["result_summary"]
    assert "6. 商品6" not in result["result_summary"]
    assert "还有 2 个价格变化对象未展示。" in result["result_summary"]
    assert "未变化：2 个" in result["result_summary"]


def test_execute_price_refresh_run_detail_success(monkeypatch):
    def _fake_get_run(self, run_id: str):
        assert run_id == "PRR-20260425-ABCD"
        return {
            "run_id": run_id,
            "status": "succeeded",
            "total": 10,
            "refreshed": 10,
            "changed": 3,
            "failed": 0,
            "duration_ms": 1200,
            "items": [
                {
                    "product_id": 1,
                    "product_name": "商品A",
                    "current_price": 199,
                    "last_price": 209,
                    "price_delta": -10,
                    "price_delta_percent": -4.78,
                    "price_changed": True,
                }
            ],
        }

    monkeypatch.setattr("app.clients.b_service_client.BServiceClient.get_price_refresh_run", _fake_get_run)
    state = {
        "intent_code": "ecom_watch.price_refresh_run_detail",
        "slots": {"run_id": "PRR-20260425-ABCD"},
        "status": "processing",
    }
    result = execute_action(state)
    assert result["status"] == "succeeded"
    assert "价格刷新结果：PRR-20260425-ABCD" in result["result_summary"]
    assert "价格变化：3" in result["result_summary"]
    assert "变化：下降 10（-4.78%）" in result["result_summary"]


def test_execute_price_refresh_run_detail_no_changes(monkeypatch):
    def _fake_get_run(self, run_id: str):
        return {
            "run_id": run_id,
            "status": "succeeded",
            "total": 5,
            "refreshed": 5,
            "changed": 0,
            "failed": 0,
            "duration_ms": 300,
            "items": [],
        }

    monkeypatch.setattr("app.clients.b_service_client.BServiceClient.get_price_refresh_run", _fake_get_run)
    state = {
        "intent_code": "ecom_watch.price_refresh_run_detail",
        "slots": {"run_id": "PRR-20260425-AAAA"},
        "status": "processing",
    }
    result = execute_action(state)
    assert result["status"] == "succeeded"
    assert "变化对象：" in result["result_summary"]
    assert "\n无" in result["result_summary"]


def test_execute_price_refresh_run_detail_not_found(monkeypatch):
    def _fake_get_run(self, run_id: str):
        raise BServiceError("B 服务错误：refresh run not found (code=HTTP_404, status=404)")

    monkeypatch.setattr("app.clients.b_service_client.BServiceClient.get_price_refresh_run", _fake_get_run)
    state = {
        "intent_code": "ecom_watch.price_refresh_run_detail",
        "slots": {"run_id": "PRR-20260425-ZZZZ"},
        "status": "processing",
    }
    result = execute_action(state)
    assert result["status"] == "failed"
    assert "查询失败" in result["result_summary"]


def test_execute_monitor_price_history_success(monkeypatch):
    def _fake_price_history(self, target_id: int, limit: int = 5):
        assert target_id == 7
        assert limit == 5
        return {
            "product_name": "Mock Phone X",
            "snapshots": [
                {
                    "checked_at": "2026-04-25T18:30:00",
                    "price": 199,
                    "price_delta": -10,
                    "price_delta_percent": -4.78,
                    "price_source": "mock_price",
                },
                {
                    "checked_at": "2026-04-25T18:20:00",
                    "price": 209,
                    "price_delta": None,
                    "price_delta_percent": None,
                    "price_source": "mock_price",
                },
            ],
        }

    monkeypatch.setattr(
        "app.clients.b_service_client.BServiceClient.get_monitor_target_price_history",
        _fake_price_history,
    )
    state = {
        "intent_code": "ecom_watch.monitor_price_history",
        "slots": {"target_id": 7, "query_mode": "target_id", "ambiguous_input": True},
        "status": "processing",
    }
    result = execute_action(state)
    assert result["status"] == "succeeded"
    assert "价格历史：Mock Phone X（对象ID=7）" in result["result_summary"]
    assert "变化：下降 10（-4.78%）" in result["result_summary"]
    assert "变化：首次记录" in result["result_summary"]
    assert "本次按对象ID查询：7。" in result["result_summary"]
    assert "如果你想按列表序号查询，请发送：查看第 7 个价格历史" in result["result_summary"]


def test_execute_monitor_price_history_by_list_index(monkeypatch):
    def _fake_load_latest_targets_context(*, chat_id: str, user_open_id: str):
        assert chat_id == "chat-1"
        assert user_open_id == "user-1"
        return {
            "targets": [
                {"target_id": 5, "name": "A"},
                {"target_id": 12, "name": "B"},
                {"target_id": 20, "name": "C"},
            ]
        }

    def _fake_price_history(self, target_id: int, limit: int = 5):
        assert target_id == 12
        return {
            "product_name": "Mock Phone X",
            "snapshots": [
                {
                    "checked_at": "2026-04-25T18:30:00",
                    "price": 199,
                    "price_delta": -10,
                    "price_delta_percent": -4.78,
                    "price_source": "mock_price",
                }
            ],
        }

    monkeypatch.setattr(
        "app.graph.nodes.execute_action._load_latest_monitor_targets_context",
        _fake_load_latest_targets_context,
    )
    monkeypatch.setattr(
        "app.clients.b_service_client.BServiceClient.get_monitor_target_price_history",
        _fake_price_history,
    )
    state = {
        "intent_code": "ecom_watch.monitor_price_history",
        "slots": {"list_index": 2, "query_mode": "list_index"},
        "status": "processing",
        "source_chat_id": "chat-1",
        "user_open_id": "user-1",
    }
    result = execute_action(state)
    assert result["status"] == "succeeded"
    assert "对象ID=12" in result["result_summary"]
    assert "本次按列表序号查询：第 2 个监控对象。" in result["result_summary"]


def test_execute_monitor_price_history_empty(monkeypatch):
    def _fake_price_history(self, target_id: int, limit: int = 5):
        return {"product_name": "Mock Phone X", "snapshots": []}

    monkeypatch.setattr(
        "app.clients.b_service_client.BServiceClient.get_monitor_target_price_history",
        _fake_price_history,
    )
    state = {
        "intent_code": "ecom_watch.monitor_price_history",
        "slots": {"target_id": 7},
        "status": "processing",
    }
    result = execute_action(state)
    assert result["status"] == "succeeded"
    assert "该监控对象暂未产生价格历史" in result["result_summary"]
    assert "请先发送：刷新监控价格" in result["result_summary"]


def test_execute_monitor_price_history_list_index_out_of_range(monkeypatch):
    monkeypatch.setattr(
        "app.graph.nodes.execute_action._load_latest_monitor_targets_context",
        lambda **_: {"targets": [{"target_id": 1}]},
    )
    state = {
        "intent_code": "ecom_watch.monitor_price_history",
        "slots": {"list_index": 7, "query_mode": "list_index"},
        "status": "processing",
        "source_chat_id": "chat-1",
        "user_open_id": "user-1",
    }
    result = execute_action(state)
    assert result["status"] == "failed"
    assert "编号超出范围" in result["result_summary"]


def test_execute_product_detail_success(monkeypatch):
    def _fake_detail(self, product_id: int):
        assert product_id == 123
        return {"name": "商品A", "status": "active", "price": 199}

    monkeypatch.setattr("app.clients.b_service_client.BServiceClient.get_product_detail", _fake_detail)
    state = {"intent_code": "ecom_watch.product_detail", "slots": {"product_id": 123}, "status": "processing"}
    result = execute_action(state)
    assert result["status"] == "succeeded"
    assert "商品详情 #123" in result["result_summary"]


def test_execute_add_monitor_by_url_success(monkeypatch):
    def _fake_add_monitor(self, url: str):
        assert url == "https://example.com/product/abc"
        return {"count": 1, "targets": [{"product_id": 99, "product_name": "Example 商品", "is_active": True}]}

    monkeypatch.setattr("app.clients.b_service_client.BServiceClient.add_monitor_by_url", _fake_add_monitor)
    state = {
        "intent_code": "ecom_watch.add_monitor_by_url",
        "slots": {"url": "https://example.com/product/abc"},
        "status": "processing",
    }
    result = execute_action(state)
    assert result["status"] == "succeeded"
    assert "已加入监控" in result["result_summary"]
    assert "名称：Example 商品" in result["result_summary"]
    assert "对象ID：99" in result["result_summary"]


def test_execute_replace_monitor_target_url_success(monkeypatch):
    def _fake_replace_url(self, target_id: int, product_url: str):
        assert target_id == 12
        assert product_url == "https://example.com/p/12"
        return {
            "target": {
                "id": 12,
                "product_url": product_url,
                "price_confidence": "unknown",
                "price_page_type": "unknown",
            }
        }

    monkeypatch.setattr("app.clients.b_service_client.BServiceClient.replace_monitor_target_url", _fake_replace_url)
    state = {
        "intent_code": "ecom_watch.replace_monitor_target_url",
        "slots": {"target_id": 12, "product_url": "https://example.com/p/12"},
        "status": "processing",
    }
    result = execute_action(state)
    assert result["status"] == "succeeded"
    assert "已更新监控对象 URL" in result["result_summary"]
    assert "对象ID：12" in result["result_summary"]
    assert "建议下一步：重新采集对象 12" in result["result_summary"]


def test_execute_refresh_monitor_target_price_success(monkeypatch):
    def _fake_refresh_target(self, target_id: int):
        assert target_id == 12
        return {
            "target_id": 12,
            "price_probe_status": "success",
            "price_confidence": "high",
            "price_page_type": "product_detail",
        }

    monkeypatch.setattr("app.clients.b_service_client.BServiceClient.refresh_monitor_target_price", _fake_refresh_target)
    state = {
        "intent_code": "ecom_watch.refresh_monitor_target_price",
        "slots": {"target_id": 12},
        "status": "processing",
    }
    result = execute_action(state)
    assert result["status"] == "succeeded"
    assert "已触发重新采集" in result["result_summary"]
    assert "对象ID：12" in result["result_summary"]
    assert "可信度：high" in result["result_summary"]
    assert "页面类型：product_detail" in result["result_summary"]


def test_execute_discovery_search_success(monkeypatch):
    def _fake_discovery_search(self, query: str):
        assert query == "wireless headphone"
        return {"batch_id": 12, "query": query}

    def _fake_get_batch(self, batch_id: int):
        assert batch_id == 12
        return {
            "batch_id": 12,
            "query": "wireless headphone",
            "candidates": [
                {"title": "A", "url": "https://a.example", "domain": "a.example"},
                {"title": "B", "url": "https://b.example", "domain": "b.example"},
            ],
        }

    monkeypatch.setattr("app.clients.b_service_client.BServiceClient.discovery_search", _fake_discovery_search)
    monkeypatch.setattr("app.clients.b_service_client.BServiceClient.get_discovery_batch", _fake_get_batch)
    state = {
        "intent_code": "ecom_watch.discovery_search",
        "slots": {"query": "wireless headphone"},
        "status": "processing",
    }
    result = execute_action(state)
    assert result["status"] == "succeeded"
    assert "搜索结果：wireless headphone" in result["result_summary"]
    assert "批次：12" in result["result_summary"]
    assert "URL: https://a.example" in result["result_summary"]


def test_execute_add_from_candidates_success(monkeypatch):
    def _fake_load_latest_context(*, chat_id: str, user_open_id: str):
        assert chat_id == "chat-1"
        assert user_open_id == "user-1"
        return {
            "batch_id": 12,
            "source_type": "discovery",
            "candidates": [
                {"candidate_id": 1001, "title": "A 商品", "url": "https://a.example"},
                {"candidate_id": 1002, "title": "B 商品", "url": "https://b.example"},
            ],
        }

    def _fake_add_from_candidates(self, *, batch_id: int, candidate_ids: list[int], source_type: str | None = None):
        assert batch_id == 12
        assert candidate_ids == [1002]
        assert source_type == "discovery"
        return {
            "count": 1,
            "targets": [{"id": 77, "name": "B 商品", "url": "https://b.example", "status": "active"}],
        }

    monkeypatch.setattr("app.graph.nodes.execute_action._load_latest_discovery_context", _fake_load_latest_context)
    monkeypatch.setattr("app.clients.b_service_client.BServiceClient.add_from_candidates", _fake_add_from_candidates)
    state = {
        "intent_code": "ecom_watch.add_from_candidates",
        "slots": {"index": 2},
        "status": "processing",
        "source_chat_id": "chat-1",
        "user_open_id": "user-1",
    }
    result = execute_action(state)
    assert result["status"] == "succeeded"
    assert "已加入监控" in result["result_summary"]
    assert "第 2 个" in result["result_summary"]
    assert "对象ID：77" in result["result_summary"]


def test_execute_add_from_candidates_missing_context(monkeypatch):
    monkeypatch.setattr(
        "app.graph.nodes.execute_action._load_latest_discovery_context",
        lambda **_: None,
    )
    state = {
        "intent_code": "ecom_watch.add_from_candidates",
        "slots": {"index": 2},
        "status": "processing",
        "source_chat_id": "chat-1",
        "user_open_id": "user-1",
    }
    result = execute_action(state)
    assert result["status"] == "failed"
    assert "未找到最近一次搜索结果" in result["result_summary"]


def test_execute_b_service_error(monkeypatch):
    def _fake_summary_raise(self):
        raise BServiceError("B 服务不可达")

    monkeypatch.setattr("app.clients.b_service_client.BServiceClient.get_today_summary", _fake_summary_raise)
    state = {"intent_code": "ecom_watch.summary_today", "slots": {}, "status": "processing"}
    result = execute_action(state)
    assert result["status"] == "failed"
    assert "查询失败" in result["result_summary"]


def test_execute_add_monitor_by_url_b_service_error(monkeypatch):
    def _fake_add_monitor_raise(self, _url: str):
        raise BServiceError("B 服务错误：invalid url")

    monkeypatch.setattr("app.clients.b_service_client.BServiceClient.add_monitor_by_url", _fake_add_monitor_raise)
    state = {
        "intent_code": "ecom_watch.add_monitor_by_url",
        "slots": {"url": "not-a-url"},
        "status": "processing",
    }
    result = execute_action(state)
    assert result["status"] == "failed"
    assert "加入监控失败" in result["result_summary"]


def test_execute_replace_monitor_target_url_b_service_error(monkeypatch):
    def _fake_replace_url_raise(self, _target_id: int, _product_url: str):
        raise BServiceError("B 服务错误：target not found")

    monkeypatch.setattr(
        "app.clients.b_service_client.BServiceClient.replace_monitor_target_url",
        _fake_replace_url_raise,
    )
    state = {
        "intent_code": "ecom_watch.replace_monitor_target_url",
        "slots": {"target_id": 999, "product_url": "https://example.com/p/999"},
        "status": "processing",
    }
    result = execute_action(state)
    assert result["status"] == "failed"
    assert "替换URL失败" in result["result_summary"]


def test_execute_refresh_monitor_target_price_b_service_error(monkeypatch):
    def _fake_refresh_target_raise(self, _target_id: int):
        raise BServiceError("B 服务错误：refresh failed")

    monkeypatch.setattr(
        "app.clients.b_service_client.BServiceClient.refresh_monitor_target_price",
        _fake_refresh_target_raise,
    )
    state = {
        "intent_code": "ecom_watch.refresh_monitor_target_price",
        "slots": {"target_id": 12},
        "status": "processing",
    }
    result = execute_action(state)
    assert result["status"] == "failed"
    assert "重新采集失败" in result["result_summary"]


def test_execute_discovery_search_b_service_error(monkeypatch):
    def _fake_discovery_raise(self, _query: str):
        raise BServiceError("B 服务错误：search backend unavailable")

    monkeypatch.setattr("app.clients.b_service_client.BServiceClient.discovery_search", _fake_discovery_raise)
    state = {
        "intent_code": "ecom_watch.discovery_search",
        "slots": {"query": "wireless headphone"},
        "status": "processing",
    }
    result = execute_action(state)
    assert result["status"] == "failed"
    assert "搜索失败" in result["result_summary"]
