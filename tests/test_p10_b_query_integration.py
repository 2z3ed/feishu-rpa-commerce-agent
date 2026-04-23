from app.clients.b_service_client import BServiceError
from app.graph.nodes.execute_action import execute_action
from app.graph.nodes.resolve_intent import resolve_intent


def test_resolve_today_summary_intent():
    state = {"normalized_text": "今天有什么变化"}
    out = resolve_intent(state)
    assert out["intent_code"] == "ecom_watch.summary_today"


def test_resolve_monitor_targets_intent():
    state = {"normalized_text": "看看当前监控对象"}
    out = resolve_intent(state)
    assert out["intent_code"] == "ecom_watch.monitor_targets"


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
    assert "#123" in result["result_summary"]


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
