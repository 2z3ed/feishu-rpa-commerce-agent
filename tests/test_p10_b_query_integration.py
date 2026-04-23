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


def test_execute_b_service_error(monkeypatch):
    def _fake_summary_raise(self):
        raise BServiceError("B 服务不可达")

    monkeypatch.setattr("app.clients.b_service_client.BServiceClient.get_today_summary", _fake_summary_raise)
    state = {"intent_code": "ecom_watch.summary_today", "slots": {}, "status": "processing"}
    result = execute_action(state)
    assert result["status"] == "failed"
    assert "查询失败" in result["result_summary"]
