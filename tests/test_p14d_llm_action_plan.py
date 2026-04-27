from app.core.config import settings
from app.graph.nodes.execute_action import _build_action_plan_input, _detect_action_plan_focus, execute_action
from app.graph.nodes.resolve_intent import resolve_intent
from app.schemas.llm_action_plan import ActionPlanOutput


def test_resolve_action_plan_intent_phrases():
    commands = (
        "这些异常商品下一步怎么处理",
        "给我一个处理计划",
        "低可信对象接下来怎么处理",
        "帮我安排一下处理顺序",
        "哪些先重试，哪些先换 URL",
        "哪些先重试，哪些先换URL",
        "重试和换链接怎么排",
    )
    for text in commands:
        out = resolve_intent({"normalized_text": text})
        assert out["intent_code"] == "ecom_watch.action_plan"


def test_detect_action_plan_focus():
    assert _detect_action_plan_focus("低可信对象接下来怎么处理") == "manual_review_first"
    assert _detect_action_plan_focus("帮我安排一下处理顺序") == "priority"
    assert _detect_action_plan_focus("哪些先重试") == "retry"
    assert _detect_action_plan_focus("先换 URL 再看") == "url_fix"
    assert _detect_action_plan_focus("哪些先重试，哪些先换 URL") == "retry_url_mix"


def test_build_action_plan_input_counts_from_p13_fields():
    action_plan_input = _build_action_plan_input(
        targets_data={
            "targets": [
                {
                    "id": 1,
                    "name": "A",
                    "action_priority": "high",
                    "manual_review_required": True,
                    "action_category": "url_fix",
                    "price_page_type": "listing_page",
                    "price_probe_status": "failed",
                    "price_source": "mock_price",
                },
                {
                    "id": 2,
                    "name": "B",
                    "action_priority": "low",
                    "manual_review_required": False,
                    "action_category": "observe",
                    "price_probe_status": "success",
                    "price_source": "html_extract_preview",
                    "price_page_type": "product_detail",
                },
            ]
        }
    )
    assert action_plan_input.stats.target_count == 2
    assert action_plan_input.stats.high_priority_count == 1
    assert action_plan_input.stats.manual_review_count == 1
    assert action_plan_input.stats.url_fix_count == 1
    assert action_plan_input.stats.retry_count == 1
    assert action_plan_input.stats.observe_count == 1


def test_execute_action_plan_success(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_LLM_ACTION_PLAN", True)
    monkeypatch.setattr(settings, "LLM_ACTION_PLAN_PROVIDER", "mock")
    monkeypatch.setattr(
        "app.clients.b_service_client.BServiceClient.get_monitor_targets",
        lambda self: {
            "targets": [
                {
                    "id": 1,
                    "name": "商品A",
                    "action_priority": "high",
                    "manual_review_required": True,
                    "action_category": "manual_review",
                    "price_source": "mock_price",
                    "price_probe_status": "fallback_mock",
                },
                {
                    "id": 2,
                    "name": "商品B",
                    "action_priority": "medium",
                    "manual_review_required": False,
                    "action_category": "url_fix",
                    "price_page_type": "listing_page",
                },
            ]
        },
    )
    logs = []
    monkeypatch.setattr("app.graph.nodes.execute_action.log_step", lambda *a: logs.append(a))
    state = {
        "task_id": "TASK-P14D-OK",
        "intent_code": "ecom_watch.action_plan",
        "slots": {},
        "status": "processing",
        "raw_text": "给我一个处理计划",
    }
    result = execute_action(state)
    assert result["status"] == "succeeded"
    assert "当前处理优先级判断" in result["result_summary"]
    assert "不会自动处理提醒" in result["result_summary"]
    assert result["capability"] == "monitor.action_plan"
    assert any(step[1] == "llm_action_plan_started" for step in logs)
    assert any(step[1] == "llm_action_plan_succeeded" for step in logs)


def test_execute_action_plan_retry_url_phrase_from_intent_resolve(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_LLM_ACTION_PLAN", True)
    monkeypatch.setattr(settings, "LLM_ACTION_PLAN_PROVIDER", "mock")
    monkeypatch.setattr(
        "app.clients.b_service_client.BServiceClient.get_monitor_targets",
        lambda self: {
            "targets": [
                {
                    "id": 1,
                    "name": "商品A",
                    "action_priority": "high",
                    "manual_review_required": True,
                    "action_category": "retry",
                    "price_probe_status": "failed",
                },
                {
                    "id": 2,
                    "name": "商品B",
                    "action_priority": "medium",
                    "manual_review_required": False,
                    "action_category": "url_fix",
                    "price_page_type": "listing_page",
                },
            ]
        },
    )
    logs = []
    monkeypatch.setattr("app.graph.nodes.execute_action.log_step", lambda *a: logs.append(a))

    resolved = resolve_intent({"normalized_text": "哪些先重试，哪些先换 URL"})
    assert resolved["intent_code"] == "ecom_watch.action_plan"
    result = execute_action(
        {
            "task_id": "TASK-P14D-RETRY-URL",
            "intent_code": resolved["intent_code"],
            "slots": resolved.get("slots", {}),
            "status": "processing",
            "raw_text": "哪些先重试，哪些先换 URL",
        }
    )
    assert result["status"] == "succeeded"
    assert any(step[1] == "llm_action_plan_started" for step in logs)
    assert any(step[1] == "llm_action_plan_succeeded" for step in logs)
    assert result["action_executed_detail"]["plan_focus"] in {"retry", "url_fix", "retry_url_mix"}
    assert result["action_executed_detail"]["plan_focus"] == "retry_url_mix"


def test_execute_action_plan_fallback_on_provider_failure(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_LLM_ACTION_PLAN", True)
    monkeypatch.setattr(settings, "LLM_ACTION_PLAN_PROVIDER", "openai")
    monkeypatch.setattr(
        "app.clients.b_service_client.BServiceClient.get_monitor_targets",
        lambda self: {"targets": [{"id": 2, "name": "商品B", "price_confidence": "low"}]},
    )
    logs = []
    monkeypatch.setattr("app.graph.nodes.execute_action.log_step", lambda *a: logs.append(a))
    state = {
        "task_id": "TASK-P14D-FB",
        "intent_code": "ecom_watch.action_plan",
        "slots": {},
        "status": "processing",
    }
    result = execute_action(state)
    assert result["status"] == "succeeded"
    assert any(step[1] == "llm_action_plan_failed" for step in logs)
    assert any(step[1] == "llm_action_plan_fallback_used" for step in logs)


def test_execute_action_plan_no_targets_returns_friendly_text(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_LLM_ACTION_PLAN", True)
    monkeypatch.setattr(settings, "LLM_ACTION_PLAN_PROVIDER", "mock")
    monkeypatch.setattr("app.clients.b_service_client.BServiceClient.get_monitor_targets", lambda self: {"targets": []})
    monkeypatch.setattr("app.graph.nodes.execute_action.log_step", lambda *a: None)
    state = {
        "task_id": "TASK-P14D-EMPTY",
        "intent_code": "ecom_watch.action_plan",
        "slots": {},
        "status": "processing",
    }
    result = execute_action(state)
    assert result["status"] == "succeeded"
    assert "当前还没有监控对象" in result["result_summary"]


def test_execute_action_plan_service_mock_failure_degrades(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_LLM_ACTION_PLAN", True)
    monkeypatch.setattr(settings, "LLM_ACTION_PLAN_PROVIDER", "mock")
    monkeypatch.setattr(
        "app.clients.b_service_client.BServiceClient.get_monitor_targets",
        lambda self: {"targets": [{"id": 7, "name": "商品X", "price_probe_status": "failed"}]},
    )
    monkeypatch.setattr(
        "app.graph.nodes.execute_action.run_llm_action_plan",
        lambda _inp: ActionPlanOutput(
            plan_text="当前无法生成智能计划，但已获取到基础诊断信息。",
            provider="mock",
            fallback_used=True,
            error="timeout",
        ),
    )
    logs = []
    monkeypatch.setattr("app.graph.nodes.execute_action.log_step", lambda *a: logs.append(a))
    state = {
        "task_id": "TASK-P14D-MOCK-FAIL",
        "intent_code": "ecom_watch.action_plan",
        "slots": {},
        "status": "processing",
    }
    result = execute_action(state)
    assert result["status"] == "succeeded"
    assert "当前无法生成智能计划" in result["result_summary"]
    assert any(step[1] == "llm_action_plan_fallback_used" for step in logs)
