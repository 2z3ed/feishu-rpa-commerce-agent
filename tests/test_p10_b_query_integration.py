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
    def _fake_refresh(self):
        return {
            "total": 8,
            "refreshed": 6,
            "changed": 2,
            "failed": 0,
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
    assert "本轮价格变化：2 个" in result["result_summary"]
    assert "1. 商品A" in result["result_summary"]
    assert "变化：上涨 5（+2.63%）" in result["result_summary"]
    assert "2. 商品B" in result["result_summary"]
    assert "变化：下降 20（-10.00%）" in result["result_summary"]
    assert "未变化：6 个" in result["result_summary"]
    assert "刷新失败：0 个" in result["result_summary"]


def test_execute_refresh_monitor_prices_no_changes(monkeypatch):
    def _fake_refresh(self):
        return {
            "total": 10,
            "refreshed": 10,
            "changed": 0,
            "failed": 1,
            "items": [],
            "changed_items": [],
        }

    monkeypatch.setattr("app.clients.b_service_client.BServiceClient.refresh_monitor_prices", _fake_refresh)
    state = {"intent_code": "ecom_watch.refresh_monitor_prices", "slots": {}, "status": "processing"}
    result = execute_action(state)
    assert result["status"] == "succeeded"
    assert "本轮暂无价格变化" in result["result_summary"]
    assert "成功刷新：10" in result["result_summary"]
    assert "失败：1" in result["result_summary"]


def test_execute_refresh_monitor_prices_show_top_five(monkeypatch):
    def _fake_refresh(self):
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
            "total": 9,
            "refreshed": 9,
            "changed": 7,
            "failed": 0,
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
