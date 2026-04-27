from app.core.config import settings
from app.graph.nodes.execute_action import execute_action
from app.graph.nodes.resolve_intent import resolve_intent
from app.schemas.llm_anomaly_explanation import AnomalyExplanationOutput


def test_resolve_anomaly_explanation_intent_phrases():
    commands = (
        "为什么这些商品价格不准",
        "解释一下低可信对象的问题",
        "为什么这个商品需要人工处理",
        "这些异常是怎么来的",
        "mock_price 是什么意思",
        "fallback_mock 为什么不能直接用",
    )
    for text in commands:
        out = resolve_intent({"normalized_text": text})
        assert out["intent_code"] == "ecom_watch.anomaly_explanation"


def test_execute_anomaly_explanation_success(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_LLM_ANOMALY_EXPLANATION", True)
    monkeypatch.setattr(settings, "LLM_ANOMALY_EXPLANATION_PROVIDER", "mock")
    monkeypatch.setattr(
        "app.clients.b_service_client.BServiceClient.get_monitor_targets",
        lambda self: {
            "targets": [
                {
                    "id": 1,
                    "name": "商品A",
                    "price_source": "mock_price",
                    "price_probe_status": "fallback_mock",
                    "price_confidence": "low",
                    "price_page_type": "listing_page",
                    "price_anomaly_status": "suspected",
                    "manual_review_required": True,
                }
            ]
        },
    )
    logs = []
    monkeypatch.setattr("app.graph.nodes.execute_action.log_step", lambda *a: logs.append(a))

    state = {
        "task_id": "TASK-P14C-OK",
        "intent_code": "ecom_watch.anomaly_explanation",
        "slots": {},
        "status": "processing",
        "raw_text": "为什么这些商品价格不准",
    }
    result = execute_action(state)
    assert result["status"] == "succeeded"
    assert "当前问题是什么" in result["result_summary"]
    assert "不会自动处理提醒" in result["result_summary"]
    assert result["capability"] == "monitor.anomaly_explanation"
    assert any(step[1] == "llm_anomaly_explanation_started" for step in logs)
    assert any(step[1] == "llm_anomaly_explanation_succeeded" for step in logs)


def test_execute_anomaly_explanation_fallback_on_provider_failure(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_LLM_ANOMALY_EXPLANATION", True)
    monkeypatch.setattr(settings, "LLM_ANOMALY_EXPLANATION_PROVIDER", "openai")
    monkeypatch.setattr(
        "app.clients.b_service_client.BServiceClient.get_monitor_targets",
        lambda self: {"targets": [{"id": 2, "name": "商品B", "price_confidence": "low"}]},
    )
    logs = []
    monkeypatch.setattr("app.graph.nodes.execute_action.log_step", lambda *a: logs.append(a))

    state = {
        "task_id": "TASK-P14C-FB",
        "intent_code": "ecom_watch.anomaly_explanation",
        "slots": {},
        "status": "processing",
    }
    result = execute_action(state)
    assert result["status"] == "succeeded"
    assert any(step[1] == "llm_anomaly_explanation_failed" for step in logs)
    assert any(step[1] == "llm_anomaly_explanation_fallback_used" for step in logs)


def test_execute_anomaly_explanation_no_anomaly_friendly_message(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_LLM_ANOMALY_EXPLANATION", True)
    monkeypatch.setattr(settings, "LLM_ANOMALY_EXPLANATION_PROVIDER", "mock")
    monkeypatch.setattr(
        "app.clients.b_service_client.BServiceClient.get_monitor_targets",
        lambda self: {
            "targets": [
                {
                    "id": 3,
                    "name": "商品C",
                    "price_confidence": "high",
                    "price_probe_status": "success",
                    "price_anomaly_status": "normal",
                    "manual_review_required": False,
                }
            ]
        },
    )
    monkeypatch.setattr("app.graph.nodes.execute_action.log_step", lambda *a: None)
    state = {
        "task_id": "TASK-P14C-NO-ANOMALY",
        "intent_code": "ecom_watch.anomaly_explanation",
        "slots": {},
        "status": "processing",
    }
    result = execute_action(state)
    assert result["status"] == "succeeded"
    assert "没有明显异常" in result["result_summary"]


def test_execute_anomaly_explanation_degrade_when_service_returns_fallback(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_LLM_ANOMALY_EXPLANATION", True)
    monkeypatch.setattr(settings, "LLM_ANOMALY_EXPLANATION_PROVIDER", "mock")
    monkeypatch.setattr(
        "app.clients.b_service_client.BServiceClient.get_monitor_targets",
        lambda self: {"targets": [{"id": 7, "name": "商品X", "price_probe_status": "failed"}]},
    )
    monkeypatch.setattr(
        "app.graph.nodes.execute_action.run_llm_anomaly_explanation",
        lambda _inp: AnomalyExplanationOutput(
            explanation_text="当前无法生成智能解释，但已获取到基础诊断信息。",
            provider="mock",
            fallback_used=True,
            error="timeout",
        ),
    )
    logs = []
    monkeypatch.setattr("app.graph.nodes.execute_action.log_step", lambda *a: logs.append(a))

    state = {
        "task_id": "TASK-P14C-MOCK-FAIL",
        "intent_code": "ecom_watch.anomaly_explanation",
        "slots": {},
        "status": "processing",
    }
    result = execute_action(state)
    assert result["status"] == "succeeded"
    assert "当前无法生成智能解释" in result["result_summary"]
    assert any(step[1] == "llm_anomaly_explanation_fallback_used" for step in logs)
