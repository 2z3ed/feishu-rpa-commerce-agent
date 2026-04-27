from app.core.config import settings
from app.graph.nodes.execute_action import execute_action
from app.graph.nodes.resolve_intent import resolve_intent
from app.schemas.llm_intent import LLMIntentFallbackOutput


def test_rule_hit_does_not_call_llm_fallback(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_LLM_INTENT_FALLBACK", True)

    def _raise_if_called(_text: str):
        raise AssertionError("LLM fallback should not be called for rule hit")

    monkeypatch.setattr("app.graph.nodes.resolve_intent.run_llm_intent_fallback", _raise_if_called)
    out = resolve_intent({"task_id": "TASK-RULE-HIT", "normalized_text": "看看当前监控对象"})
    assert out["intent_code"] == "ecom_watch.monitor_targets"


def test_rule_miss_triggers_llm_fallback_success(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_LLM_INTENT_FALLBACK", True)
    monkeypatch.setattr(settings, "LLM_INTENT_CONFIDENCE_THRESHOLD", 0.75)
    logs = []
    monkeypatch.setattr("app.graph.nodes.resolve_intent.log_step", lambda *a: logs.append(a))

    out = resolve_intent({"task_id": "TASK-FB-OK", "normalized_text": "帮我看看哪些商品不太对"})
    assert out["intent_code"] == "ecom_watch.monitor_diagnostics_query"
    assert out["slots"]["query_type"] == "price_anomaly"
    assert any(step[1] == "llm_intent_fallback_started" for step in logs)
    assert any(step[1] == "llm_intent_fallback_succeeded" for step in logs)


def test_low_confidence_returns_clarification(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_LLM_INTENT_FALLBACK", True)
    monkeypatch.setattr(settings, "LLM_INTENT_CONFIDENCE_THRESHOLD", 0.75)

    out = resolve_intent({"task_id": "TASK-FB-LOW", "normalized_text": "处理一下那个有问题的"})
    assert out["intent_code"] == "unknown"
    assert "clarification_question" in out
    action_out = execute_action(out)
    assert action_out["status"] == "failed"
    assert "确认" in action_out["result_summary"] or "需要" in action_out["result_summary"]


def test_illegal_intent_is_blocked(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_LLM_INTENT_FALLBACK", True)

    def _fake_fallback(_text: str):
        return LLMIntentFallbackOutput(
            intent="dangerous.delete_all_monitors",
            slots={},
            confidence=0.99,
            clarification_question="该请求不在允许范围，请改为查看异常对象。",
            reason="dangerous",
        )

    monkeypatch.setattr("app.graph.nodes.resolve_intent.run_llm_intent_fallback", _fake_fallback)
    out = resolve_intent({"task_id": "TASK-FB-BLOCK", "normalized_text": "把异常商品都删掉"})
    assert out["intent_code"] == "unknown"
    assert "clarification_question" in out


def test_fallback_system_confirm_task_is_blocked(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_LLM_INTENT_FALLBACK", True)
    logs = []
    monkeypatch.setattr("app.graph.nodes.resolve_intent.log_step", lambda *a: logs.append(a))

    def _fake_fallback(_text: str):
        return LLMIntentFallbackOutput(
            intent="system.confirm_task",
            slots={"task_id": "TASK-20260409-E4D73C"},
            confidence=0.95,
            clarification_question="确认执行必须使用明确命令：确认执行 TASK-xxxx。",
            reason="not_allowed_confirm_from_fallback",
        )

    monkeypatch.setattr("app.graph.nodes.resolve_intent.run_llm_intent_fallback", _fake_fallback)
    out = resolve_intent({"task_id": "TASK-FB-CONFIRM-BLOCK", "normalized_text": "帮我确认一下那个任务"})
    assert out["intent_code"] == "unknown"
    assert "clarification_question" in out
    assert any(step[1] == "llm_intent_fallback_failed" for step in logs)


def test_fallback_product_update_price_goes_to_awaiting_confirmation(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_LLM_INTENT_FALLBACK", True)
    monkeypatch.setattr("app.graph.nodes.execute_action.log_step", lambda *a, **k: None)

    def _fake_fallback(_text: str):
        return LLMIntentFallbackOutput(
            intent="product.update_price",
            slots={"sku": "A001", "target_price": 59.9},
            confidence=0.91,
            clarification_question="",
            reason="high_confidence_update_price",
        )

    monkeypatch.setattr("app.graph.nodes.resolve_intent.run_llm_intent_fallback", _fake_fallback)
    resolved = resolve_intent({"task_id": "TASK-FB-PRICE", "normalized_text": "把 A001 价格调到 59.9"})
    assert resolved["intent_code"] == "product.update_price"
    executed = execute_action(resolved)
    assert executed["status"] == "awaiting_confirmation"
    assert executed["status"] != "succeeded"


def test_rule_hit_system_confirm_task_keeps_old_behavior():
    out = resolve_intent({"normalized_text": "确认执行 TASK-20260409-E4D73C"})
    assert out["intent_code"] == "system.confirm_task"
    assert out["slots"]["task_id"] == "TASK-20260409-E4D73C"


def test_mock_provider_retry_phrase_variant_hits_fallback(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_LLM_INTENT_FALLBACK", True)
    out = resolve_intent({"task_id": "TASK-FB-RETRY", "normalized_text": "失败的监控重新跑"})
    assert out["intent_code"] == "ecom_watch.retry_price_probes"


def test_mock_provider_update_price_phrase_goes_awaiting_confirmation(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_LLM_INTENT_FALLBACK", True)
    monkeypatch.setattr("app.graph.nodes.execute_action.log_step", lambda *a, **k: None)
    resolved = resolve_intent({"task_id": "TASK-FB-PRICE99", "normalized_text": "帮我把 SKU A001 的价格改成 99"})
    assert resolved["intent_code"] == "product.update_price"
    executed = execute_action(resolved)
    assert executed["status"] == "awaiting_confirmation"


def test_llm_exception_safe_fallback_unknown(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_LLM_INTENT_FALLBACK", True)

    def _raise(_text: str):
        raise RuntimeError("provider down")

    monkeypatch.setattr("app.graph.nodes.resolve_intent.run_llm_intent_fallback", _raise)
    out = resolve_intent({"task_id": "TASK-FB-ERR", "normalized_text": "帮我看看哪些商品不太对"})
    assert out["intent_code"] == "unknown"


def test_flag_off_keeps_old_behavior(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_LLM_INTENT_FALLBACK", False)
    out = resolve_intent({"task_id": "TASK-FB-OFF", "normalized_text": "帮我看看哪些商品不太对"})
    assert out["intent_code"] == "unknown"

