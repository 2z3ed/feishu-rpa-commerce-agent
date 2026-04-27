from app.core.config import settings
from app.graph.nodes.execute_action import _build_monitor_summary_input, _detect_monitor_summary_focus, execute_action
from app.graph.nodes.resolve_intent import resolve_intent
from app.schemas.llm_monitor_summary import MonitorSummaryOutput


def test_resolve_monitor_summary_intent_phrases():
    commands = (
        "总结一下当前价格监控情况",
        "帮我看一下现在监控整体怎么样",
        "当前有哪些商品需要重点处理",
        "给我汇总一下价格监控状态",
    )
    for text in commands:
        out = resolve_intent({"normalized_text": text})
        assert out["intent_code"] == "ecom_watch.monitor_summary"


def test_detect_summary_focus_by_user_text():
    assert _detect_monitor_summary_focus("总结一下当前价格监控情况") == "overview"
    assert _detect_monitor_summary_focus("帮我看一下现在监控整体怎么样") == "health_check"
    assert _detect_monitor_summary_focus("当前有哪些商品需要重点处理") == "priority_targets"


def test_build_monitor_summary_input_counts_from_p13_fields():
    summary_input = _build_monitor_summary_input(
        targets_data={
            "targets": [
                {
                    "id": 1,
                    "name": "A",
                    "price_anomaly_status": "suspected",
                    "price_confidence": "low",
                    "manual_review_required": True,
                    "action_priority": "high",
                    "action_suggestion": "先人工复查",
                },
                {
                    "id": 2,
                    "name": "B",
                    "price_anomaly_status": "normal",
                    "price_confidence": "high",
                    "manual_review_required": False,
                    "action_priority": "medium",
                    "action_suggestion": "继续观察",
                },
            ]
        }
    )
    assert summary_input.stats.target_count == 2
    assert summary_input.stats.anomaly_count == 1
    assert summary_input.stats.low_confidence_count == 1
    assert summary_input.stats.manual_review_count == 1
    assert summary_input.stats.high_priority_count == 1


def test_execute_monitor_summary_success(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_LLM_MONITOR_SUMMARY", True)
    monkeypatch.setattr(settings, "LLM_MONITOR_SUMMARY_PROVIDER", "mock")

    called = {"count": 0}
    logs = []

    def _fake_targets(self):
        called["count"] += 1
        return {
            "targets": [
                {"id": 1, "name": "A", "price_anomaly_status": "suspected", "price_confidence": "low", "manual_review_required": True, "action_priority": "high"},
                {"id": 2, "name": "B", "price_anomaly_status": "normal", "price_confidence": "high", "manual_review_required": False, "action_priority": "medium"},
            ]
        }

    monkeypatch.setattr("app.clients.b_service_client.BServiceClient.get_monitor_targets", _fake_targets)
    monkeypatch.setattr("app.graph.nodes.execute_action.log_step", lambda *a: logs.append(a))

    state = {"task_id": "TASK-P14B-OK", "intent_code": "ecom_watch.monitor_summary", "slots": {}, "status": "processing"}
    result = execute_action(state)
    assert result["status"] == "succeeded"
    assert "当前价格监控运营总结" in result["result_summary"]
    assert "不建议自动处理" in result["result_summary"]
    assert called["count"] == 1
    assert any(step[1] == "llm_monitor_summary_started" for step in logs)
    assert any(step[1] == "llm_monitor_summary_succeeded" for step in logs)
    assert result["capability"] == "monitor.summary"
    assert result["action_executed_detail"]["summary_focus"] == "overview"


def test_execute_monitor_summary_fallback_when_provider_unavailable(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_LLM_MONITOR_SUMMARY", True)
    monkeypatch.setattr(settings, "LLM_MONITOR_SUMMARY_PROVIDER", "openai")
    monkeypatch.setattr(
        "app.clients.b_service_client.BServiceClient.get_monitor_targets",
        lambda self: {"targets": [{"id": 1, "name": "A", "action_priority": "high"}]},
    )
    logs = []
    monkeypatch.setattr("app.graph.nodes.execute_action.log_step", lambda *a: logs.append(a))

    state = {"task_id": "TASK-P14B-FB", "intent_code": "ecom_watch.monitor_summary", "slots": {}, "status": "processing"}
    result = execute_action(state)
    assert result["status"] == "succeeded"
    assert "当前价格监控运营总结" in result["result_summary"]
    assert any(step[1] == "llm_monitor_summary_failed" for step in logs)
    assert any(step[1] == "llm_monitor_summary_fallback_used" for step in logs)


def test_execute_monitor_summary_no_targets_returns_friendly_text(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_LLM_MONITOR_SUMMARY", True)
    monkeypatch.setattr(settings, "LLM_MONITOR_SUMMARY_PROVIDER", "mock")
    monkeypatch.setattr("app.clients.b_service_client.BServiceClient.get_monitor_targets", lambda self: {"targets": []})
    monkeypatch.setattr("app.graph.nodes.execute_action.log_step", lambda *a: None)

    state = {"task_id": "TASK-P14B-EMPTY", "intent_code": "ecom_watch.monitor_summary", "slots": {}, "status": "processing"}
    result = execute_action(state)
    assert result["status"] == "succeeded"
    assert "当前还没有监控对象" in result["result_summary"]


def test_execute_monitor_summary_service_mock_failure_degrades(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_LLM_MONITOR_SUMMARY", True)
    monkeypatch.setattr(settings, "LLM_MONITOR_SUMMARY_PROVIDER", "mock")
    monkeypatch.setattr(
        "app.clients.b_service_client.BServiceClient.get_monitor_targets",
        lambda self: {"targets": [{"id": 1, "name": "A"}]},
    )
    monkeypatch.setattr(
        "app.graph.nodes.execute_action.run_llm_monitor_summary",
        lambda _inp: MonitorSummaryOutput(
            summary_text="当前无法生成智能总结，但已获取到基础监控数据。",
            provider="mock",
            fallback_used=True,
            error="timeout",
        ),
    )
    logs = []
    monkeypatch.setattr("app.graph.nodes.execute_action.log_step", lambda *a: logs.append(a))

    state = {"task_id": "TASK-P14B-MOCK-FAIL", "intent_code": "ecom_watch.monitor_summary", "slots": {}, "status": "processing"}
    result = execute_action(state)
    assert result["status"] == "succeeded"
    assert "当前无法生成智能总结" in result["result_summary"]
    assert any(step[1] == "llm_monitor_summary_fallback_used" for step in logs)


def test_execute_monitor_summary_health_check_focus(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_LLM_MONITOR_SUMMARY", True)
    monkeypatch.setattr(settings, "LLM_MONITOR_SUMMARY_PROVIDER", "mock")
    monkeypatch.setattr(
        "app.clients.b_service_client.BServiceClient.get_monitor_targets",
        lambda self: {
            "targets": [
                {"id": 1, "name": "A", "price_anomaly_status": "suspected", "price_confidence": "low", "action_priority": "high"},
                {"id": 2, "name": "B", "price_anomaly_status": "normal", "price_confidence": "high", "action_priority": "low"},
            ]
        },
    )
    logs = []
    monkeypatch.setattr("app.graph.nodes.execute_action.log_step", lambda *a: logs.append(a))

    state = {
        "task_id": "TASK-P14B-HEALTH",
        "intent_code": "ecom_watch.monitor_summary",
        "slots": {},
        "status": "processing",
        "raw_text": "帮我看一下现在监控整体怎么样",
    }
    result = execute_action(state)
    assert result["status"] == "succeeded"
    assert "监控健康度检查" in result["result_summary"]
    assert result["action_executed_detail"]["summary_focus"] == "health_check"
    assert any("summary_focus=health_check" in str(step[3]) for step in logs if len(step) >= 4)


def test_execute_monitor_summary_priority_targets_focus(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_LLM_MONITOR_SUMMARY", True)
    monkeypatch.setattr(settings, "LLM_MONITOR_SUMMARY_PROVIDER", "mock")
    monkeypatch.setattr(
        "app.clients.b_service_client.BServiceClient.get_monitor_targets",
        lambda self: {
            "targets": [
                {
                    "id": 10,
                    "name": "商品A",
                    "action_priority": "high",
                    "manual_review_required": True,
                    "price_anomaly_reason": "疑似价格异常",
                    "action_suggestion": "先人工复核后再决定处理动作",
                },
                {
                    "id": 11,
                    "action_priority": "high",
                    "manual_review_required": False,
                    "price_probe_error": "timeout",
                },
                {
                    "id": 12,
                    "name": "商品C",
                    "action_priority": "medium",
                    "manual_review_required": True,
                    "price_confidence": "low",
                },
                {"id": 13, "name": "商品D", "action_priority": "low", "manual_review_required": False},
            ]
        },
    )

    state = {
        "task_id": "TASK-P14B-PRIORITY",
        "intent_code": "ecom_watch.monitor_summary",
        "slots": {},
        "status": "processing",
        "raw_text": "当前有哪些商品需要重点处理",
    }
    result = execute_action(state)
    assert result["status"] == "succeeded"
    assert "重点处理对象总结" in result["result_summary"]
    assert "当前高优先级对象：2 个" in result["result_summary"]
    assert "当前人工接管对象：2 个" in result["result_summary"]
    assert "建议优先处理（前 3 个）" in result["result_summary"]
    assert "风险原因：" in result["result_summary"]
    assert "建议动作：" in result["result_summary"]
    assert "系统不会自动处理" in result["result_summary"]
    assert result["action_executed_detail"]["summary_focus"] == "priority_targets"
    assert result["capability"] == "monitor.summary"
