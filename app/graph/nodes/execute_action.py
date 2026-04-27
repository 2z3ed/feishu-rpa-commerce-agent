"""
Execute Action Node

Executes the identified action based on intent.
"""
import json
import re
from app.core.logging import logger
from app.db.session import SessionLocal
from app.db.models import TaskRecord, TaskStep
from app.core.time import get_shanghai_now
from app.executors import get_product_executor, resolve_execution_mode, resolve_query_platform
from app.clients.woo_readonly_prep import get_woo_rollout_policy
from app.clients.product_provider_profile import resolve_provider_profile
from app.clients.product_provider_readiness import check_platform_provider_readiness
from app.clients.odoo_inventory_client import (
    OdooInventoryClient,
    OdooInventoryClientDisabled,
    OdooInventoryClientError,
    OdooInventoryClientNotFound,
    OdooInventoryClientRequestError,
    OdooInventoryClientTimeout,
)
from app.core.config import settings
from app.rpa.confirm_update_price import (
    run_confirm_update_price_api_then_rpa_verify,
    run_confirm_update_price_rpa,
)
from app.rpa.query_sku_status import run_query_sku_status_real_admin_readonly
from app.rpa.yingdao_runner import run_yingdao_adjust_inventory, YingdaoBridgeError
from app.schemas.llm_anomaly_explanation import AnomalyExplanationInput, AnomalyExplanationStats
from app.schemas.llm_monitor_summary import MonitorSummaryInput, MonitorSummaryStats
from app.services.llm.anomaly_explanation import run_llm_anomaly_explanation
from app.services.llm.monitor_summary import run_llm_monitor_summary
from app.utils.task_logger import log_step
from app.clients.b_service_client import BServiceClient, BServiceError

_DISCOVERY_CONTEXT_STEP_CODE = "discovery_context_saved"
_MONITOR_TARGETS_CONTEXT_STEP_CODE = "monitor_targets_context_saved"


def _extract_confirm_failure_layer(result: dict) -> str:
    pr = result.get("parsed_result")
    if isinstance(pr, dict):
        layer = str(pr.get("failure_layer") or "").strip()
        if layer:
            return layer
    code = str(result.get("error_code") or "").strip()
    return code or "unknown_exception"


def _strip_error_prefix(raw: str) -> str:
    text = (raw or "").strip()
    return re.sub(r"^\[[^\]]+\]\s*", "", text).strip()


def _evaluate_adjust_inventory_gate(slots: dict) -> tuple[bool, str]:
    """Return (allow, reason) for the minimal gate entry."""
    sku = str(slots.get("sku") or "").strip().upper()
    delta_raw = slots.get("delta")
    target_inventory_raw = slots.get("target_inventory")
    try:
        delta = int(delta_raw)
    except Exception:
        delta = 0
    try:
        target_inventory = int(target_inventory_raw)
    except Exception:
        target_inventory = 0
    if not sku:
        return False, "sku_required"
    if delta == 0 and target_inventory == 0:
        return False, "delta_or_target_inventory_required"
    return True, "allow"


def _extract_discovery_candidate_minimal(candidate: dict) -> dict | None:
    if not isinstance(candidate, dict):
        return None
    candidate_id = candidate.get("candidate_id")
    if candidate_id in (None, ""):
        candidate_id = candidate.get("id")
    if candidate_id in (None, ""):
        return None
    return {
        "candidate_id": int(candidate_id),
        "title": str(candidate.get("title") or candidate.get("name") or "未命名候选"),
        "url": str(candidate.get("url") or candidate.get("product_url") or ""),
    }


def _build_discovery_context(*, batch_data: dict, query: str) -> dict:
    batch_id = batch_data.get("batch_id")
    source_type = batch_data.get("source_type")
    raw_candidates = batch_data.get("candidates")
    candidates: list[dict] = []
    if isinstance(raw_candidates, list):
        for candidate in raw_candidates:
            minimal = _extract_discovery_candidate_minimal(candidate)
            if minimal is not None:
                candidates.append(minimal)
    return {
        "batch_id": int(batch_id) if batch_id not in (None, "") else None,
        "source_type": str(source_type or "discovery"),
        "query": query,
        "candidates": candidates,
    }


def _save_discovery_context(*, task_id: str, state: dict, context: dict) -> None:
    payload = {
        "chat_id": str(state.get("source_chat_id") or ""),
        "user_open_id": str(state.get("user_open_id") or ""),
        "batch_id": context.get("batch_id"),
        "source_type": context.get("source_type"),
        "query": context.get("query"),
        "candidates": context.get("candidates"),
    }
    log_step(
        task_id,
        _DISCOVERY_CONTEXT_STEP_CODE,
        "success",
        json.dumps(payload, ensure_ascii=False),
    )


def _load_latest_discovery_context(*, chat_id: str, user_open_id: str) -> dict | None:
    if not chat_id:
        return None
    db = SessionLocal()
    try:
        query = (
            db.query(TaskStep.detail)
            .join(TaskRecord, TaskRecord.task_id == TaskStep.task_id)
            .filter(
                TaskStep.step_code == _DISCOVERY_CONTEXT_STEP_CODE,
                TaskRecord.chat_id == chat_id,
                TaskRecord.status == "succeeded",
            )
            .order_by(TaskStep.created_at.desc())
        )
        if user_open_id:
            query = query.filter(TaskRecord.user_open_id == user_open_id)
        row = query.first()
        if not row:
            return None
        raw_detail = row[0] if isinstance(row, tuple) else getattr(row, "detail", "")
        payload = json.loads(raw_detail or "{}")
        if not isinstance(payload, dict):
            return None
        return payload
    except Exception:
        return None
    finally:
        db.close()


def _extract_monitor_target_minimal(item: dict) -> dict | None:
    if not isinstance(item, dict):
        return None
    raw_id = item.get("id")
    if raw_id in (None, ""):
        raw_id = item.get("product_id") or item.get("target_id")
    if raw_id in (None, ""):
        return None
    name = str(item.get("name") or item.get("product_name") or item.get("title") or "未命名")
    status = str(item.get("status") or ("active" if item.get("is_active", True) else "inactive"))
    url = str(item.get("url") or item.get("product_url") or "")
    return {
        "target_id": int(raw_id),
        "name": name,
        "status": status,
        "url": url,
        "current_price": item.get("current_price"),
        "last_price": item.get("last_price"),
        "price_delta": item.get("price_delta"),
        "price_delta_percent": item.get("price_delta_percent"),
        "price_changed": bool(item.get("price_changed", False)),
        "last_checked_at": item.get("last_checked_at"),
        "price_source": item.get("price_source"),
        "price_probe_status": item.get("price_probe_status"),
        "price_probe_error": item.get("price_probe_error"),
        "price_probe_checked_at": item.get("price_probe_checked_at"),
        "price_probe_raw_text": item.get("price_probe_raw_text"),
        "price_confidence": item.get("price_confidence"),
        "price_page_type": item.get("price_page_type"),
        "price_anomaly_status": item.get("price_anomaly_status"),
        "price_anomaly_reason": item.get("price_anomaly_reason"),
        "price_action_suggestion": item.get("price_action_suggestion"),
        "action_priority": item.get("action_priority"),
        "action_category": item.get("action_category"),
        "manual_review_required": item.get("manual_review_required"),
        "alert_candidate": item.get("alert_candidate"),
        "action_suggestion": item.get("action_suggestion"),
    }


def _build_monitor_targets_context(*, targets_data: dict) -> dict:
    raw_targets = targets_data.get("targets")
    if not isinstance(raw_targets, list):
        raw_targets = targets_data.get("items") if isinstance(targets_data.get("items"), list) else []
    targets: list[dict] = []
    for item in raw_targets:
        if not isinstance(item, dict):
            continue
        minimal = _extract_monitor_target_minimal(item)
        if minimal is None:
            continue
        targets.append(minimal)
    return {"targets": targets}


def _save_monitor_targets_context(*, task_id: str, state: dict, context: dict) -> None:
    payload = {
        "chat_id": str(state.get("source_chat_id") or ""),
        "user_open_id": str(state.get("user_open_id") or ""),
        "targets": context.get("targets") if isinstance(context.get("targets"), list) else [],
    }
    log_step(
        task_id,
        _MONITOR_TARGETS_CONTEXT_STEP_CODE,
        "success",
        json.dumps(payload, ensure_ascii=False),
    )


def _load_latest_monitor_targets_context(*, chat_id: str, user_open_id: str) -> dict | None:
    if not chat_id:
        return None
    db = SessionLocal()
    try:
        query = (
            db.query(TaskStep.detail)
            .join(TaskRecord, TaskRecord.task_id == TaskStep.task_id)
            .filter(
                TaskStep.step_code == _MONITOR_TARGETS_CONTEXT_STEP_CODE,
                TaskRecord.chat_id == chat_id,
                TaskRecord.status == "succeeded",
            )
            .order_by(TaskStep.created_at.desc())
        )
        if user_open_id:
            query = query.filter(TaskRecord.user_open_id == user_open_id)
        row = query.first()
        if not row:
            return None
        raw_detail = row[0] if isinstance(row, tuple) else getattr(row, "detail", "")
        payload = json.loads(raw_detail or "{}")
        if not isinstance(payload, dict):
            return None
        return payload
    except Exception:
        return None
    finally:
        db.close()


def _build_monitor_summary_input(*, targets_data: dict) -> MonitorSummaryInput:
    context = _build_monitor_targets_context(targets_data=targets_data)
    targets = context.get("targets") if isinstance(context.get("targets"), list) else []

    anomaly_count = 0
    low_confidence_count = 0
    manual_review_count = 0
    high_priority_count = 0

    for item in targets:
        if not isinstance(item, dict):
            continue
        anomaly_status = str(item.get("price_anomaly_status") or "").strip().lower()
        if anomaly_status in {"suspected", "anomaly", "abnormal"}:
            anomaly_count += 1

        confidence = str(item.get("price_confidence") or "").strip().lower()
        if confidence in {"low", "unknown"}:
            low_confidence_count += 1

        if bool(item.get("manual_review_required")):
            manual_review_count += 1

        priority = str(item.get("action_priority") or "").strip().lower()
        if priority == "high":
            high_priority_count += 1

    return MonitorSummaryInput(
        stats=MonitorSummaryStats(
            target_count=len(targets),
            anomaly_count=anomaly_count,
            low_confidence_count=low_confidence_count,
            manual_review_count=manual_review_count,
            high_priority_count=high_priority_count,
        ),
        targets=targets,
    )


def _detect_monitor_summary_focus(text: str) -> str:
    normalized = str(text or "").strip().lower()
    if not normalized:
        return "overview"

    priority_keywords = ("哪些", "重点处理", "需要处理", "人工接管", "优先处理")
    if any(keyword in normalized for keyword in priority_keywords):
        return "priority_targets"

    health_keywords = ("整体", "怎么样", "健康", "状态")
    if any(keyword in normalized for keyword in health_keywords):
        return "health_check"

    return "overview"


def _build_anomaly_explanation_input(*, targets_data: dict) -> AnomalyExplanationInput:
    context = _build_monitor_targets_context(targets_data=targets_data)
    targets = context.get("targets") if isinstance(context.get("targets"), list) else []

    anomaly_count = 0
    low_confidence_count = 0
    failed_probe_count = 0
    manual_review_count = 0

    for item in targets:
        if not isinstance(item, dict):
            continue
        anomaly_status = str(item.get("price_anomaly_status") or "").strip().lower()
        if anomaly_status in {"suspected", "anomaly", "abnormal"}:
            anomaly_count += 1

        confidence = str(item.get("price_confidence") or "").strip().lower()
        if confidence in {"low", "unknown"}:
            low_confidence_count += 1

        probe_status = str(item.get("price_probe_status") or "").strip().lower()
        if probe_status in {"failed", "fallback_mock"}:
            failed_probe_count += 1

        if bool(item.get("manual_review_required")):
            manual_review_count += 1

    return AnomalyExplanationInput(
        stats=AnomalyExplanationStats(
            target_count=len(targets),
            anomaly_count=anomaly_count,
            low_confidence_count=low_confidence_count,
            failed_probe_count=failed_probe_count,
            manual_review_count=manual_review_count,
        ),
        targets=targets,
    )


def _detect_anomaly_explanation_focus(text: str) -> str:
    normalized = str(text or "").strip().lower()
    if not normalized:
        return "overview"
    if "低可信" in normalized or "可信度" in normalized:
        return "low_confidence"
    if "人工处理" in normalized or "人工接管" in normalized:
        return "manual_review"
    if "mock_price" in normalized or "fallback_mock" in normalized:
        return "mock_source"
    return "overview"


def _apply_adjust_inventory_governance_baseline(state: dict, result: dict | None = None) -> None:
    """Keep adjust_inventory governance fields stable across success/blocked/verify-failed paths."""
    result = result if isinstance(result, dict) else {}
    pr = result.get("parsed_result")
    if not isinstance(pr, dict):
        pr = state.get("parsed_result") if isinstance(state.get("parsed_result"), dict) else {}

    state["provider_id"] = str(result.get("provider_id") or "odoo")
    state["capability"] = str(result.get("capability") or "warehouse.adjust_inventory")
    state["platform"] = str(result.get("platform") or "odoo")
    state["confirm_backend"] = str(result.get("confirm_backend") or pr.get("confirm_backend") or state.get("confirm_backend") or "none")
    state["operation_result"] = str(result.get("operation_result") or pr.get("operation_result") or state.get("operation_result") or "")
    state["verify_passed"] = (
        result["verify_passed"]
        if "verify_passed" in result
        else pr.get("verify_passed", state.get("verify_passed"))
    )
    state["verify_reason"] = str(result.get("verify_reason") or pr.get("verify_reason") or state.get("verify_reason") or "")
    state["failure_layer"] = str(pr.get("failure_layer") or result.get("failure_layer") or state.get("failure_layer") or "")
    state["target_task_id"] = str(pr.get("target_task_id") or result.get("target_task_id") or state.get("target_task_id") or "")
    state["original_update_task_id"] = str(
        pr.get("original_update_task_id") or result.get("original_update_task_id") or state.get("original_update_task_id") or ""
    )
    state["confirm_task_id"] = str(pr.get("confirm_task_id") or result.get("confirm_task_id") or state.get("confirm_task_id") or "")

    # Keep these observable fields deterministic on adjust_inventory confirm path.
    state["readiness_status"] = str(state.get("readiness_status") or "ready")
    state["endpoint_profile"] = str(state.get("endpoint_profile") or "odoo_product_stock_v1")
    state["session_injection_mode"] = str(state.get("session_injection_mode") or "header")
    state["execution_backend"] = str(state.get("execution_backend") or "internal_sandbox")
    state["selected_backend"] = str(state.get("selected_backend") or "internal_sandbox")
    state["final_backend"] = str(state.get("final_backend") or "internal_sandbox")


def execute_action(state: dict) -> dict:
    """
    Execute action based on intent.
    
    Args:
        state: Current graph state
        
    Returns:
        Updated state with execution result
    """
    intent_code = state.get("intent_code", "unknown")
    slots = state.get("slots", {})
    task_id = state.get("task_id", "")
    raw_text = state.get("raw_text", "")
    execution_mode = resolve_execution_mode(intent_code, state.get("execution_mode"))
    state["execution_mode"] = execution_mode
    executor = get_product_executor(execution_mode)
    state["platform"] = "mock"
    state["execution_backend"] = "mock_repo"
    state["client_profile"] = "mock_repo"
    state["response_mapper"] = "none"
    state["request_adapter"] = "none"
    state["auth_profile"] = "none"
    state["provider_profile"] = "none"
    state["credential_profile"] = "none"
    state["production_config_ready"] = "n/a"
    state["dry_run_enabled"] = "false"
    state["selected_backend"] = "mock_repo"
    state["backend_selection_reason"] = "mock_mode"
    state["fallback_enabled"] = "false"
    state["fallback_applied"] = "false"
    state["fallback_target"] = "none"
    state["final_backend"] = "mock_repo"
    state["dry_run_failure"] = "none"
    state["recommended_strategy"] = "n/a"
    state["environment_ready"] = "unknown"
    state["live_probe_enabled"] = "false"
    state["provider_id"] = "mock"
    state["capability"] = "none"
    state["readiness_status"] = "unknown"
    state["endpoint_profile"] = "none"
    state["session_injection_mode"] = "none"
    state.setdefault("evidence_count", 0)
    state.setdefault("rpa_runner", "none")
    state.setdefault("verify_mode", "none")
    
    if intent_code == "unknown":
        clarification_question = str(state.get("clarification_question") or "").strip()
        state["error_message"] = "Unknown intent"
        state["status"] = "failed"
        state["result_summary"] = (
            clarification_question
            if clarification_question
            else "未识别到已知命令，请尝试其他表述方式"
        )
        logger.warning("Cannot execute unknown intent")
        return state
    
    try:
        if intent_code == "product.query_sku_status":
            state["capability"] = "product.query_sku_status"
            state["execution_backend"] = "sandbox_http_client" if execution_mode == "api" else "mock_repo"
            state["selected_backend"] = state["execution_backend"]
            if execution_mode == "api":
                state["client_profile"] = getattr(executor, "get_backend_profile", lambda: "sandbox_http_client")()
                resolved_platform = resolve_query_platform(execution_mode, slots.get("platform"))
                state["platform"] = resolved_platform
                state["provider_id"] = resolved_platform
                state["response_mapper"] = getattr(executor, "get_mapper_name", lambda p: "sandbox_mapper")(resolved_platform)
                state["provider_profile"] = getattr(executor, "get_provider_profile_name", lambda p: "unknown")(resolved_platform)
                try:
                    pf = resolve_provider_profile(resolved_platform)
                    state["endpoint_profile"] = pf.endpoint_profile
                    state["session_injection_mode"] = pf.session_injection_mode
                except Exception:
                    state["endpoint_profile"] = "unknown"
                    state["session_injection_mode"] = "unknown"
                state["request_adapter"] = "pending"
                state["auth_profile"] = "pending"
                state["credential_profile"] = "pending"
                state["production_config_ready"] = "pending"
                state["dry_run_enabled"] = "pending"
                state["selected_backend"] = "pending"
                state["backend_selection_reason"] = "pending"
                state["fallback_enabled"] = "pending"
                state["fallback_applied"] = "pending"
                state["fallback_target"] = "pending"
                state["final_backend"] = "pending"
                state["dry_run_failure"] = "pending"
            if execution_mode == "rpa":
                task_trace = (state.get("source_message_id") or "").strip() or task_id
                rpa_result, rpa_err = run_query_sku_status_real_admin_readonly(
                    task_id=task_id,
                    trace_id=task_trace,
                    sku=str(slots.get("sku") or ""),
                )
                if rpa_err:
                    meta = rpa_err.get("_rpa_meta") or {}
                    state["error_message"] = str(rpa_err.get("error") or "readonly query failed")
                    state["status"] = "failed"
                    state["result_summary"] = f"执行失败：{state['error_message']}"
                    state["execution_backend"] = meta.get("execution_backend", "rpa_browser_real")
                    state["selected_backend"] = meta.get("selected_backend", state["execution_backend"])
                    state["final_backend"] = meta.get("final_backend", state["execution_backend"])
                    state["client_profile"] = "rpa_runner"
                    state["rpa_runner"] = meta.get("rpa_runner", "browser_real")
                    state["verify_mode"] = str(meta.get("verify_mode", "basic"))
                    state["evidence_count"] = int(meta.get("evidence_count", 0))
                    state["platform"] = meta.get("platform", "woo")
                    state["provider_id"] = state["platform"]
                    state["capability"] = "product.query_sku_status"
                    state["readiness_status"] = "ready"
                    state["endpoint_profile"] = "real_admin_readonly_v1"
                    state["session_injection_mode"] = "cookie_or_header"
                    state["backend_selection_reason"] = str(rpa_err.get("error_code") or "rpa_query_failed")
                    return state
                result = (rpa_result or {}).get("query_result", {})
                rpa_meta = (rpa_result or {}).get("_rpa_meta", {})
                state["execution_backend"] = rpa_meta.get("execution_backend", "rpa_browser_real")
                state["selected_backend"] = rpa_meta.get("selected_backend", state["execution_backend"])
                state["final_backend"] = rpa_meta.get("final_backend", state["execution_backend"])
                state["client_profile"] = "rpa_runner"
                state["rpa_runner"] = rpa_meta.get("rpa_runner", "browser_real")
                state["verify_mode"] = str(rpa_meta.get("verify_mode", "basic"))
                state["evidence_count"] = int(rpa_meta.get("evidence_count", 0))
                state["backend_selection_reason"] = "real_admin_prepared_readonly_query"
                state["provider_id"] = "woo"
                state["readiness_status"] = "ready"
                state["endpoint_profile"] = "real_admin_readonly_v1"
                state["session_injection_mode"] = "cookie_or_header"
            else:
                result = execute_product_query_sku_status(executor, slots, execution_mode)
            if execution_mode == "api":
                state["execution_backend"] = getattr(executor, "get_selected_backend", lambda: "sandbox_http_client")()
                state["client_profile"] = getattr(executor, "get_backend_profile", lambda: "sandbox_http_client")()
                state["request_adapter"] = getattr(executor, "get_request_adapter_name", lambda: "unknown")()
                state["auth_profile"] = getattr(executor, "get_auth_profile", lambda: "unknown")()
                state["credential_profile"] = getattr(executor, "get_credential_profile", lambda: "unknown")()
                state["production_config_ready"] = getattr(
                    executor, "get_production_config_ready", lambda: "n/a"
                )()
                state["dry_run_enabled"] = getattr(executor, "get_dry_run_enabled", lambda: "false")()
                state["selected_backend"] = getattr(
                    executor, "get_selected_backend", lambda: state.get("execution_backend", "sandbox_http_client")
                )()
                state["backend_selection_reason"] = getattr(
                    executor, "get_backend_selection_reason", lambda: "unknown"
                )()
                rollout = get_woo_rollout_policy(execution_mode, resolved_platform)
                state["recommended_strategy"] = str(rollout["recommended_strategy"])
                state["live_probe_enabled"] = "true" if bool(settings.WOO_ENABLE_READONLY_LIVE_PROBE) else "false"
                state["fallback_enabled"] = getattr(executor, "get_fallback_enabled", lambda: "false")()
                state["fallback_applied"] = getattr(executor, "get_fallback_applied", lambda: "false")()
                state["fallback_target"] = getattr(executor, "get_fallback_target", lambda: "none")()
                state["final_backend"] = getattr(
                    executor, "get_final_backend", lambda: state.get("execution_backend", "sandbox_http_client")
                )()
                state["dry_run_failure"] = getattr(executor, "get_dry_run_failure", lambda: "none")()
                state["readiness_status"] = "ready"
            elif execution_mode == "mock":
                state["provider_id"] = "mock"
                state["readiness_status"] = "n/a"
                state["endpoint_profile"] = "mock_repo_v1"
                state["session_injection_mode"] = "none"
            state["query_product_data"] = result
            state["result_summary"] = format_product_query_result(result)
            state["status"] = "succeeded"
            state["platform"] = result.get("platform", state.get("platform", "mock"))
            logger.info("Product query executed successfully: sku=%s", slots.get('sku'))

        elif intent_code == "ecom_watch.summary_today":
            b_client = BServiceClient()
            result = b_client.get_today_summary()
            state["status"] = "succeeded"
            state["result_summary"] = format_b_today_summary_result(result)
            state["platform"] = "ecom_watch"
            state["provider_id"] = "ecom_watch"
            state["capability"] = "summary.today"
            state["readiness_status"] = "ready"
            state["endpoint_profile"] = "b_internal_summary_today_v1"
            state["session_injection_mode"] = "none"
            state["execution_backend"] = "httpx_b_service"
            state["selected_backend"] = "httpx_b_service"
            state["final_backend"] = "httpx_b_service"
            state["backend_selection_reason"] = "p10_query_chain"
            state["client_profile"] = "b_service_client"

        elif intent_code == "ecom_watch.monitor_targets":
            b_client = BServiceClient()
            result = b_client.get_monitor_targets()
            context = _build_monitor_targets_context(targets_data=result)
            _save_monitor_targets_context(task_id=task_id, state=state, context=context)
            state["status"] = "succeeded"
            state["result_summary"] = format_b_monitor_targets_result(result)
            state["platform"] = "ecom_watch"
            state["provider_id"] = "ecom_watch"
            state["capability"] = "monitor.targets"
            state["readiness_status"] = "ready"
            state["endpoint_profile"] = "b_internal_monitor_targets_v1"
            state["session_injection_mode"] = "none"
            state["execution_backend"] = "httpx_b_service"
            state["selected_backend"] = "httpx_b_service"
            state["final_backend"] = "httpx_b_service"
            state["backend_selection_reason"] = "p10_query_chain"
            state["client_profile"] = "b_service_client"

        elif intent_code == "ecom_watch.monitor_summary":
            b_client = BServiceClient()
            result = b_client.get_monitor_targets()
            summary_input = _build_monitor_summary_input(targets_data=result)
            summary_focus = _detect_monitor_summary_focus(
                state.get("normalized_text") or state.get("raw_text") or ""
            )
            summary_input.summary_focus = summary_focus
            stats = summary_input.stats
            log_step(
                task_id,
                "llm_monitor_summary_started",
                "processing",
                (
                    f"provider={settings.LLM_MONITOR_SUMMARY_PROVIDER} "
                    f"target_count={stats.target_count} "
                    f"anomaly_count={stats.anomaly_count} "
                    f"low_confidence_count={stats.low_confidence_count} "
                    f"manual_review_count={stats.manual_review_count} "
                    f"high_priority_count={stats.high_priority_count} "
                    f"summary_focus={summary_focus}"
                ),
            )
            summary_output = run_llm_monitor_summary(summary_input)
            summary_text = str(summary_output.summary_text or "").strip()
            if not summary_text:
                summary_text = "当前无法生成智能总结，但已获取到基础监控数据。"

            if summary_output.fallback_used:
                log_step(
                    task_id,
                    "llm_monitor_summary_failed",
                    "failed",
                    (
                        f"provider={summary_output.provider} "
                        f"target_count={stats.target_count} "
                        f"anomaly_count={stats.anomaly_count} "
                        f"low_confidence_count={stats.low_confidence_count} "
                        f"manual_review_count={stats.manual_review_count} "
                        f"high_priority_count={stats.high_priority_count} "
                        f"summary_focus={summary_focus} "
                        f"error={str(summary_output.error or '')[:120]}"
                    ),
                )
                log_step(
                    task_id,
                    "llm_monitor_summary_fallback_used",
                    "success",
                    (
                        f"provider={summary_output.provider} "
                        f"target_count={stats.target_count} "
                        f"anomaly_count={stats.anomaly_count} "
                        f"low_confidence_count={stats.low_confidence_count} "
                        f"manual_review_count={stats.manual_review_count} "
                        f"high_priority_count={stats.high_priority_count} "
                        f"summary_length={len(summary_text)} "
                        f"summary_focus={summary_focus}"
                    ),
                )
            else:
                log_step(
                    task_id,
                    "llm_monitor_summary_succeeded",
                    "success",
                    (
                        f"provider={summary_output.provider} "
                        f"target_count={stats.target_count} "
                        f"anomaly_count={stats.anomaly_count} "
                        f"low_confidence_count={stats.low_confidence_count} "
                        f"manual_review_count={stats.manual_review_count} "
                        f"high_priority_count={stats.high_priority_count} "
                        f"summary_length={len(summary_text)} "
                        f"summary_focus={summary_focus}"
                    ),
                )

            state["status"] = "succeeded"
            state["result_summary"] = summary_text
            state["platform"] = "ecom_watch"
            state["provider_id"] = "ecom_watch"
            state["capability"] = "monitor.summary"
            state["readiness_status"] = "ready"
            state["endpoint_profile"] = "b_internal_monitor_targets_v1"
            state["session_injection_mode"] = "none"
            state["execution_backend"] = "httpx_b_service"
            state["selected_backend"] = "httpx_b_service"
            state["final_backend"] = "httpx_b_service"
            state["backend_selection_reason"] = "p14b_monitor_summary_chain"
            state["client_profile"] = "b_service_client"
            state["action_executed_detail"] = {
                "provider": summary_output.provider,
                "target_count": stats.target_count,
                "anomaly_count": stats.anomaly_count,
                "low_confidence_count": stats.low_confidence_count,
                "manual_review_count": stats.manual_review_count,
                "high_priority_count": stats.high_priority_count,
                "summary_length": len(summary_text),
                "summary_focus": summary_focus,
                "fallback_used": bool(summary_output.fallback_used),
                "error": str(summary_output.error or "")[:120],
            }

        elif intent_code == "ecom_watch.anomaly_explanation":
            b_client = BServiceClient()
            result = b_client.get_monitor_targets()
            explanation_input = _build_anomaly_explanation_input(targets_data=result)
            explanation_focus = _detect_anomaly_explanation_focus(
                state.get("normalized_text") or state.get("raw_text") or ""
            )
            explanation_input.explanation_focus = explanation_focus
            stats = explanation_input.stats
            log_step(
                task_id,
                "llm_anomaly_explanation_started",
                "processing",
                (
                    f"provider={settings.LLM_ANOMALY_EXPLANATION_PROVIDER} "
                    f"target_count={stats.target_count} "
                    f"anomaly_count={stats.anomaly_count} "
                    f"low_confidence_count={stats.low_confidence_count} "
                    f"failed_probe_count={stats.failed_probe_count} "
                    f"manual_review_count={stats.manual_review_count} "
                    f"explanation_focus={explanation_focus}"
                ),
            )
            explanation_output = run_llm_anomaly_explanation(explanation_input)
            explanation_text = str(explanation_output.explanation_text or "").strip()
            if not explanation_text:
                explanation_text = "当前无法生成智能解释，但已获取到基础诊断信息。"

            if explanation_output.fallback_used:
                log_step(
                    task_id,
                    "llm_anomaly_explanation_failed",
                    "failed",
                    (
                        f"provider={explanation_output.provider} "
                        f"target_count={stats.target_count} "
                        f"anomaly_count={stats.anomaly_count} "
                        f"low_confidence_count={stats.low_confidence_count} "
                        f"failed_probe_count={stats.failed_probe_count} "
                        f"manual_review_count={stats.manual_review_count} "
                        f"explanation_focus={explanation_focus} "
                        f"error={str(explanation_output.error or '')[:120]}"
                    ),
                )
                log_step(
                    task_id,
                    "llm_anomaly_explanation_fallback_used",
                    "success",
                    (
                        f"provider={explanation_output.provider} "
                        f"target_count={stats.target_count} "
                        f"explained_count={min(3, stats.target_count)} "
                        f"anomaly_count={stats.anomaly_count} "
                        f"low_confidence_count={stats.low_confidence_count} "
                        f"fallback_used=true "
                        f"explanation_focus={explanation_focus} "
                        f"explanation_length={len(explanation_text)}"
                    ),
                )
            else:
                log_step(
                    task_id,
                    "llm_anomaly_explanation_succeeded",
                    "success",
                    (
                        f"provider={explanation_output.provider} "
                        f"target_count={stats.target_count} "
                        f"explained_count={min(3, stats.target_count)} "
                        f"anomaly_count={stats.anomaly_count} "
                        f"low_confidence_count={stats.low_confidence_count} "
                        f"fallback_used=false "
                        f"explanation_focus={explanation_focus} "
                        f"explanation_length={len(explanation_text)}"
                    ),
                )

            state["status"] = "succeeded"
            state["result_summary"] = explanation_text
            state["platform"] = "ecom_watch"
            state["provider_id"] = "ecom_watch"
            state["capability"] = "monitor.anomaly_explanation"
            state["readiness_status"] = "ready"
            state["endpoint_profile"] = "b_internal_monitor_targets_v1"
            state["session_injection_mode"] = "none"
            state["execution_backend"] = "httpx_b_service"
            state["selected_backend"] = "httpx_b_service"
            state["final_backend"] = "httpx_b_service"
            state["backend_selection_reason"] = "p14c_anomaly_explanation_chain"
            state["client_profile"] = "b_service_client"
            state["action_executed_detail"] = {
                "provider": explanation_output.provider,
                "target_count": stats.target_count,
                "explained_count": min(3, stats.target_count),
                "anomaly_count": stats.anomaly_count,
                "low_confidence_count": stats.low_confidence_count,
                "failed_probe_count": stats.failed_probe_count,
                "manual_review_count": stats.manual_review_count,
                "fallback_used": bool(explanation_output.fallback_used),
                "explanation_focus": explanation_focus,
                "explanation_length": len(explanation_text),
                "error": str(explanation_output.error or "")[:120],
            }

        elif intent_code == "ecom_watch.monitor_probe_query":
            query_type = str(slots.get("query_type") or "failed").strip().lower()
            b_client = BServiceClient()
            result = b_client.get_monitor_targets()
            state["status"] = "succeeded"
            state["result_summary"] = format_b_monitor_probe_query_result(result, query_type=query_type)
            state["platform"] = "ecom_watch"
            state["provider_id"] = "ecom_watch"
            state["capability"] = "monitor.probe_query"
            state["readiness_status"] = "ready"
            state["endpoint_profile"] = "b_internal_monitor_targets_v1"
            state["session_injection_mode"] = "none"
            state["execution_backend"] = "httpx_b_service"
            state["selected_backend"] = "httpx_b_service"
            state["final_backend"] = "httpx_b_service"
            state["backend_selection_reason"] = "p13g_probe_query_chain"
            state["client_profile"] = "b_service_client"
            state["action_executed_detail"] = result

        elif intent_code == "ecom_watch.monitor_diagnostics_query":
            query_type = str(slots.get("query_type") or "monitor_status").strip().lower()
            b_client = BServiceClient()
            result = b_client.get_monitor_targets()
            state["status"] = "succeeded"
            state["result_summary"] = format_b_monitor_diagnostics_query_result(result, query_type=query_type)
            state["platform"] = "ecom_watch"
            state["provider_id"] = "ecom_watch"
            state["capability"] = "monitor.diagnostics_query"
            state["readiness_status"] = "ready"
            state["endpoint_profile"] = "b_internal_monitor_targets_v1"
            state["session_injection_mode"] = "none"
            state["execution_backend"] = "httpx_b_service"
            state["selected_backend"] = "httpx_b_service"
            state["final_backend"] = "httpx_b_service"
            state["backend_selection_reason"] = "p13i_diagnostics_query_chain"
            state["client_profile"] = "b_service_client"
            state["action_executed_detail"] = result

        elif intent_code == "ecom_watch.replace_monitor_target_url":
            target_id = slots.get("target_id")
            product_url = str(slots.get("product_url") or "").strip()
            if target_id is None:
                raise ValueError("缺少 target_id")
            if not product_url:
                raise ValueError("缺少 product_url")
            b_client = BServiceClient()
            result = b_client.replace_monitor_target_url(int(target_id), product_url)
            state["status"] = "succeeded"
            state["result_summary"] = format_b_replace_monitor_target_url_result(
                result,
                target_id=int(target_id),
                product_url=product_url,
            )
            state["platform"] = "ecom_watch"
            state["provider_id"] = "ecom_watch"
            state["capability"] = "monitor.replace_url"
            state["readiness_status"] = "ready"
            state["endpoint_profile"] = "b_internal_monitor_update_url_v1"
            state["session_injection_mode"] = "none"
            state["execution_backend"] = "httpx_b_service"
            state["selected_backend"] = "httpx_b_service"
            state["final_backend"] = "httpx_b_service"
            state["backend_selection_reason"] = "p13j_replace_url_chain"
            state["client_profile"] = "b_service_client"
            state["action_executed_detail"] = result

        elif intent_code == "ecom_watch.refresh_monitor_target_price":
            target_id = slots.get("target_id")
            if target_id is None:
                raise ValueError("缺少 target_id")
            b_client = BServiceClient()
            result = b_client.refresh_monitor_target_price(int(target_id))
            state["status"] = "succeeded"
            state["result_summary"] = format_b_refresh_monitor_target_price_result(result, int(target_id))
            state["platform"] = "ecom_watch"
            state["provider_id"] = "ecom_watch"
            state["capability"] = "monitor.refresh_target_price"
            state["readiness_status"] = "ready"
            state["endpoint_profile"] = "b_internal_monitor_refresh_price_v1"
            state["session_injection_mode"] = "none"
            state["execution_backend"] = "httpx_b_service"
            state["selected_backend"] = "httpx_b_service"
            state["final_backend"] = "httpx_b_service"
            state["backend_selection_reason"] = "p13j_refresh_single_chain"
            state["client_profile"] = "b_service_client"
            state["action_executed_detail"] = result

        elif intent_code == "ecom_watch.retry_price_probe":
            target_id = slots.get("target_id")
            if target_id is None:
                raise ValueError("缺少 target_id")
            b_client = BServiceClient()
            result = b_client.retry_monitor_target_price_probe(int(target_id), trigger_source="manual_feishu")
            state["status"] = "succeeded"
            state["result_summary"] = format_b_retry_price_probe_result(result)
            state["platform"] = "ecom_watch"
            state["provider_id"] = "ecom_watch"
            state["capability"] = "monitor.retry_price_probe"
            state["readiness_status"] = "ready"
            state["endpoint_profile"] = "b_internal_monitor_retry_price_probe_v1"
            state["session_injection_mode"] = "none"
            state["execution_backend"] = "httpx_b_service"
            state["selected_backend"] = "httpx_b_service"
            state["final_backend"] = "httpx_b_service"
            state["backend_selection_reason"] = "p13h_retry_single_chain"
            state["client_profile"] = "b_service_client"
            state["action_executed_detail"] = result

        elif intent_code == "ecom_watch.retry_price_probes":
            b_client = BServiceClient()
            result = b_client.retry_monitor_price_probes(trigger_source="manual_feishu")
            state["status"] = "succeeded"
            state["result_summary"] = format_b_retry_price_probes_result(result)
            state["platform"] = "ecom_watch"
            state["provider_id"] = "ecom_watch"
            state["capability"] = "monitor.retry_price_probes"
            state["readiness_status"] = "ready"
            state["endpoint_profile"] = "b_internal_monitor_retry_price_probes_v1"
            state["session_injection_mode"] = "none"
            state["execution_backend"] = "httpx_b_service"
            state["selected_backend"] = "httpx_b_service"
            state["final_backend"] = "httpx_b_service"
            state["backend_selection_reason"] = "p13h_retry_batch_chain"
            state["client_profile"] = "b_service_client"
            state["action_executed_detail"] = result

        elif intent_code == "ecom_watch.refresh_monitor_prices":
            b_client = BServiceClient()
            result = b_client.refresh_monitor_prices(trigger_source="manual_feishu")
            state["status"] = "succeeded"
            state["result_summary"] = format_b_refresh_monitor_prices_result(result)
            state["platform"] = "ecom_watch"
            state["provider_id"] = "ecom_watch"
            state["capability"] = "monitor.refresh_prices"
            state["readiness_status"] = "ready"
            state["endpoint_profile"] = "b_internal_monitor_refresh_prices_v1"
            state["session_injection_mode"] = "none"
            state["execution_backend"] = "httpx_b_service"
            state["selected_backend"] = "httpx_b_service"
            state["final_backend"] = "httpx_b_service"
            state["backend_selection_reason"] = "p13a_refresh_chain"
            state["client_profile"] = "b_service_client"
            state["action_executed_detail"] = result

        elif intent_code == "ecom_watch.monitor_price_history":
            query_mode = str(slots.get("query_mode") or "target_id").strip().lower()
            selected_index = None
            target_id = None
            if query_mode == "list_index":
                raw_index = slots.get("list_index")
                try:
                    selected_index = int(raw_index)
                except Exception:
                    selected_index = 0
                if selected_index <= 0:
                    state["error_message"] = "编号必须是大于 0 的整数"
                    state["status"] = "failed"
                    state["result_summary"] = "查询失败：编号必须是大于 0 的整数"
                    state["platform"] = "ecom_watch"
                    state["provider_id"] = "ecom_watch"
                    state["capability"] = "monitor.price_history"
                    state["readiness_status"] = "ready"
                    state["endpoint_profile"] = "b_internal_monitor_price_history_v1"
                    state["session_injection_mode"] = "none"
                    state["execution_backend"] = "httpx_b_service"
                    state["selected_backend"] = "httpx_b_service"
                    state["final_backend"] = "httpx_b_service"
                    state["backend_selection_reason"] = "p13b_price_history_invalid_index"
                    state["client_profile"] = "b_service_client"
                    return state
                context = _load_latest_monitor_targets_context(
                    chat_id=str(state.get("source_chat_id") or ""),
                    user_open_id=str(state.get("user_open_id") or ""),
                )
                if not context:
                    state["error_message"] = "未找到最近一次监控列表"
                    state["status"] = "failed"
                    state["result_summary"] = "查询失败：未找到最近一次监控列表，请先发送“看看当前监控对象”"
                    state["platform"] = "ecom_watch"
                    state["provider_id"] = "ecom_watch"
                    state["capability"] = "monitor.price_history"
                    state["readiness_status"] = "ready"
                    state["endpoint_profile"] = "b_internal_monitor_price_history_v1"
                    state["session_injection_mode"] = "none"
                    state["execution_backend"] = "httpx_b_service"
                    state["selected_backend"] = "httpx_b_service"
                    state["final_backend"] = "httpx_b_service"
                    state["backend_selection_reason"] = "p13b_price_history_missing_targets_context"
                    state["client_profile"] = "b_service_client"
                    return state
                targets = context.get("targets") if isinstance(context.get("targets"), list) else []
                if selected_index > len(targets):
                    state["error_message"] = f"编号超出范围（当前最多 {len(targets)} 个）"
                    state["status"] = "failed"
                    state["result_summary"] = f"查询失败：编号超出范围（当前最多 {len(targets)} 个）"
                    state["platform"] = "ecom_watch"
                    state["provider_id"] = "ecom_watch"
                    state["capability"] = "monitor.price_history"
                    state["readiness_status"] = "ready"
                    state["endpoint_profile"] = "b_internal_monitor_price_history_v1"
                    state["session_injection_mode"] = "none"
                    state["execution_backend"] = "httpx_b_service"
                    state["selected_backend"] = "httpx_b_service"
                    state["final_backend"] = "httpx_b_service"
                    state["backend_selection_reason"] = "p13b_price_history_out_of_range"
                    state["client_profile"] = "b_service_client"
                    return state
                selected = targets[selected_index - 1] if isinstance(targets[selected_index - 1], dict) else {}
                target_id = selected.get("target_id")
                if target_id in (None, ""):
                    raise ValueError("监控对象缺少 target_id")
            else:
                target_id = slots.get("target_id")
                if target_id is None:
                    raise ValueError("缺少 target_id")
            b_client = BServiceClient()
            result = b_client.get_monitor_target_price_history(int(target_id), limit=5)
            state["status"] = "succeeded"
            state["result_summary"] = format_b_monitor_price_history_result(
                result,
                int(target_id),
                query_mode=query_mode,
                selected_index=selected_index,
                ambiguous_input=bool(slots.get("ambiguous_input")),
            )
            state["platform"] = "ecom_watch"
            state["provider_id"] = "ecom_watch"
            state["capability"] = "monitor.price_history"
            state["readiness_status"] = "ready"
            state["endpoint_profile"] = "b_internal_monitor_price_history_v1"
            state["session_injection_mode"] = "none"
            state["execution_backend"] = "httpx_b_service"
            state["selected_backend"] = "httpx_b_service"
            state["final_backend"] = "httpx_b_service"
            state["backend_selection_reason"] = "p13b_price_history_chain"
            state["client_profile"] = "b_service_client"
            state["action_executed_detail"] = result

        elif intent_code == "ecom_watch.price_refresh_run_detail":
            run_id = str(slots.get("run_id") or "").strip().upper()
            if not run_id:
                raise ValueError("缺少 run_id")
            b_client = BServiceClient()
            result = b_client.get_price_refresh_run(run_id)
            state["status"] = "succeeded"
            state["result_summary"] = format_b_price_refresh_run_detail_result(result)
            state["platform"] = "ecom_watch"
            state["provider_id"] = "ecom_watch"
            state["capability"] = "monitor.price_refresh_run_detail"
            state["readiness_status"] = "ready"
            state["endpoint_profile"] = "b_internal_monitor_price_refresh_run_v1"
            state["session_injection_mode"] = "none"
            state["execution_backend"] = "httpx_b_service"
            state["selected_backend"] = "httpx_b_service"
            state["final_backend"] = "httpx_b_service"
            state["backend_selection_reason"] = "p13d_price_refresh_run_query_chain"
            state["client_profile"] = "b_service_client"
            state["action_executed_detail"] = result

        elif intent_code == "ecom_watch.manage_monitor_target":
            raw_index = slots.get("index")
            try:
                selected_index = int(raw_index)
            except Exception:
                selected_index = 0
            action = str(slots.get("action") or "").strip().lower()
            if selected_index <= 0:
                state["error_message"] = "编号必须是大于 0 的整数"
                state["status"] = "failed"
                state["result_summary"] = "操作失败：编号必须是大于 0 的整数"
                state["platform"] = "ecom_watch"
                state["provider_id"] = "ecom_watch"
                state["capability"] = "monitor.manage"
                state["readiness_status"] = "ready"
                state["endpoint_profile"] = "b_internal_monitor_manage_v1"
                state["session_injection_mode"] = "none"
                state["execution_backend"] = "httpx_b_service"
                state["selected_backend"] = "httpx_b_service"
                state["final_backend"] = "httpx_b_service"
                state["backend_selection_reason"] = "p11d_manage_invalid_index"
                state["client_profile"] = "b_service_client"
                return state
            if action not in ("pause", "resume", "delete"):
                state["error_message"] = "不支持的管理动作"
                state["status"] = "failed"
                state["result_summary"] = "操作失败：不支持的管理动作（仅支持 暂停/恢复/删除）"
                state["platform"] = "ecom_watch"
                state["provider_id"] = "ecom_watch"
                state["capability"] = "monitor.manage"
                state["readiness_status"] = "ready"
                state["endpoint_profile"] = "b_internal_monitor_manage_v1"
                state["session_injection_mode"] = "none"
                state["execution_backend"] = "httpx_b_service"
                state["selected_backend"] = "httpx_b_service"
                state["final_backend"] = "httpx_b_service"
                state["backend_selection_reason"] = "p11d_manage_invalid_action"
                state["client_profile"] = "b_service_client"
                return state

            context = _load_latest_monitor_targets_context(
                chat_id=str(state.get("source_chat_id") or ""),
                user_open_id=str(state.get("user_open_id") or ""),
            )
            if not context:
                state["error_message"] = "未找到最近一次监控列表"
                state["status"] = "failed"
                state["result_summary"] = "操作失败：未找到最近一次监控列表，请先发送“看看当前监控对象”"
                state["platform"] = "ecom_watch"
                state["provider_id"] = "ecom_watch"
                state["capability"] = "monitor.manage"
                state["readiness_status"] = "ready"
                state["endpoint_profile"] = "b_internal_monitor_manage_v1"
                state["session_injection_mode"] = "none"
                state["execution_backend"] = "httpx_b_service"
                state["selected_backend"] = "httpx_b_service"
                state["final_backend"] = "httpx_b_service"
                state["backend_selection_reason"] = "p11d_manage_missing_targets_context"
                state["client_profile"] = "b_service_client"
                return state

            targets = context.get("targets") if isinstance(context.get("targets"), list) else []
            if selected_index > len(targets):
                state["error_message"] = f"编号超出范围（当前最多 {len(targets)} 个）"
                state["status"] = "failed"
                state["result_summary"] = f"操作失败：编号超出范围（当前最多 {len(targets)} 个）"
                state["platform"] = "ecom_watch"
                state["provider_id"] = "ecom_watch"
                state["capability"] = "monitor.manage"
                state["readiness_status"] = "ready"
                state["endpoint_profile"] = "b_internal_monitor_manage_v1"
                state["session_injection_mode"] = "none"
                state["execution_backend"] = "httpx_b_service"
                state["selected_backend"] = "httpx_b_service"
                state["final_backend"] = "httpx_b_service"
                state["backend_selection_reason"] = "p11d_manage_out_of_range"
                state["client_profile"] = "b_service_client"
                return state

            selected = targets[selected_index - 1] if isinstance(targets[selected_index - 1], dict) else {}
            target_id = selected.get("target_id")
            if target_id in (None, ""):
                raise ValueError("监控对象缺少 target_id")

            b_client = BServiceClient()
            if action == "pause":
                result = b_client.pause_monitor_target(int(target_id))
                verb = "已暂停监控"
                state["endpoint_profile"] = "b_internal_monitor_pause_v1"
            elif action == "resume":
                result = b_client.resume_monitor_target(int(target_id))
                verb = "已恢复监控"
                state["endpoint_profile"] = "b_internal_monitor_resume_v1"
            else:
                result = b_client.delete_monitor_target(int(target_id))
                verb = "已删除监控对象"
                state["endpoint_profile"] = "b_internal_monitor_delete_v1"

            name = str(selected.get("name") or "未命名")
            state["status"] = "succeeded"
            state["result_summary"] = "\n".join(
                [
                    f"{verb}。",
                    f"- 选择编号：第 {selected_index} 个",
                    f"- 名称：{name}",
                    f"- 对象ID：{int(target_id)}",
                ]
            )
            state["platform"] = "ecom_watch"
            state["provider_id"] = "ecom_watch"
            state["capability"] = "monitor.manage"
            state["readiness_status"] = "ready"
            state["session_injection_mode"] = "none"
            state["execution_backend"] = "httpx_b_service"
            state["selected_backend"] = "httpx_b_service"
            state["final_backend"] = "httpx_b_service"
            state["backend_selection_reason"] = "p11d_manage_chain"
            state["client_profile"] = "b_service_client"
            state["action_executed_detail"] = result

        elif intent_code == "ecom_watch.product_detail":
            product_id = slots.get("product_id")
            if product_id is None:
                raise ValueError("缺少 product_id")
            b_client = BServiceClient()
            result = b_client.get_product_detail(int(product_id))
            state["status"] = "succeeded"
            state["result_summary"] = format_b_product_detail_result(result, int(product_id))
            state["platform"] = "ecom_watch"
            state["provider_id"] = "ecom_watch"
            state["capability"] = "products.detail"
            state["readiness_status"] = "ready"
            state["endpoint_profile"] = "b_internal_product_detail_v1"
            state["session_injection_mode"] = "none"
            state["execution_backend"] = "httpx_b_service"
            state["selected_backend"] = "httpx_b_service"
            state["final_backend"] = "httpx_b_service"
            state["backend_selection_reason"] = "p10_query_chain"
            state["client_profile"] = "b_service_client"

        elif intent_code == "ecom_watch.add_monitor_by_url":
            url = str(slots.get("url") or "").strip()
            if not url:
                raise ValueError("缺少 url")
            b_client = BServiceClient()
            result = b_client.add_monitor_by_url(url)
            state["status"] = "succeeded"
            state["result_summary"] = format_b_add_monitor_by_url_result(result, url)
            state["platform"] = "ecom_watch"
            state["provider_id"] = "ecom_watch"
            state["capability"] = "monitor.add_by_url"
            state["readiness_status"] = "ready"
            state["endpoint_profile"] = "b_internal_monitor_add_by_url_v1"
            state["session_injection_mode"] = "none"
            state["execution_backend"] = "httpx_b_service"
            state["selected_backend"] = "httpx_b_service"
            state["final_backend"] = "httpx_b_service"
            state["backend_selection_reason"] = "p11_add_by_url_chain"
            state["client_profile"] = "b_service_client"

        elif intent_code == "ecom_watch.discovery_search":
            query = str(slots.get("query") or "").strip()
            if not query:
                state["error_message"] = "请输入搜索关键词"
                state["status"] = "failed"
                state["result_summary"] = "搜索失败：请输入搜索关键词"
                state["platform"] = "ecom_watch"
                state["provider_id"] = "ecom_watch"
                state["capability"] = "discovery.search"
                state["readiness_status"] = "ready"
                state["endpoint_profile"] = "b_internal_discovery_search_batch_v1"
                state["session_injection_mode"] = "none"
                state["execution_backend"] = "httpx_b_service"
                state["selected_backend"] = "httpx_b_service"
                state["final_backend"] = "httpx_b_service"
                state["backend_selection_reason"] = "p11b_discovery_chain_empty_query"
                state["client_profile"] = "b_service_client"
                return state
            b_client = BServiceClient()
            search_result = b_client.discovery_search(query)
            batch_id = search_result.get("batch_id")
            if batch_id in (None, ""):
                raise ValueError("discovery/search 响应缺少 batch_id")
            batch_result = b_client.get_discovery_batch(batch_id)
            context = _build_discovery_context(batch_data=batch_result, query=query)
            if context.get("batch_id") is None:
                raise ValueError("discovery/batches 响应缺少 batch_id")
            _save_discovery_context(task_id=task_id, state=state, context=context)
            state["status"] = "succeeded"
            state["result_summary"] = format_b_discovery_batch_result(batch_result, query)
            state["platform"] = "ecom_watch"
            state["provider_id"] = "ecom_watch"
            state["capability"] = "discovery.search"
            state["readiness_status"] = "ready"
            state["endpoint_profile"] = "b_internal_discovery_search_batch_v1"
            state["session_injection_mode"] = "none"
            state["execution_backend"] = "httpx_b_service"
            state["selected_backend"] = "httpx_b_service"
            state["final_backend"] = "httpx_b_service"
            state["backend_selection_reason"] = "p11b_discovery_chain"
            state["client_profile"] = "b_service_client"

        elif intent_code == "ecom_watch.add_from_candidates":
            raw_index = slots.get("index")
            try:
                selected_index = int(raw_index)
            except Exception:
                selected_index = 0
            if selected_index <= 0:
                state["error_message"] = "编号必须是大于 0 的整数"
                state["status"] = "failed"
                state["result_summary"] = "加入监控失败：编号必须是大于 0 的整数"
                state["platform"] = "ecom_watch"
                state["provider_id"] = "ecom_watch"
                state["capability"] = "monitor.add_from_candidates"
                state["readiness_status"] = "ready"
                state["endpoint_profile"] = "b_internal_monitor_add_from_candidates_v1"
                state["session_injection_mode"] = "none"
                state["execution_backend"] = "httpx_b_service"
                state["selected_backend"] = "httpx_b_service"
                state["final_backend"] = "httpx_b_service"
                state["backend_selection_reason"] = "p11c_add_from_candidates_invalid_index"
                state["client_profile"] = "b_service_client"
                return state

            context = _load_latest_discovery_context(
                chat_id=str(state.get("source_chat_id") or ""),
                user_open_id=str(state.get("user_open_id") or ""),
            )
            if not context:
                state["error_message"] = "未找到最近一次搜索结果"
                state["status"] = "failed"
                state["result_summary"] = "加入监控失败：未找到最近一次搜索结果，请先发送“搜索商品：关键词”"
                state["platform"] = "ecom_watch"
                state["provider_id"] = "ecom_watch"
                state["capability"] = "monitor.add_from_candidates"
                state["readiness_status"] = "ready"
                state["endpoint_profile"] = "b_internal_monitor_add_from_candidates_v1"
                state["session_injection_mode"] = "none"
                state["execution_backend"] = "httpx_b_service"
                state["selected_backend"] = "httpx_b_service"
                state["final_backend"] = "httpx_b_service"
                state["backend_selection_reason"] = "p11c_add_from_candidates_missing_context"
                state["client_profile"] = "b_service_client"
                return state

            candidates = context.get("candidates") if isinstance(context.get("candidates"), list) else []
            if selected_index > len(candidates):
                state["error_message"] = f"编号超出范围（当前最多 {len(candidates)} 个）"
                state["status"] = "failed"
                state["result_summary"] = f"加入监控失败：编号超出范围（当前最多 {len(candidates)} 个）"
                state["platform"] = "ecom_watch"
                state["provider_id"] = "ecom_watch"
                state["capability"] = "monitor.add_from_candidates"
                state["readiness_status"] = "ready"
                state["endpoint_profile"] = "b_internal_monitor_add_from_candidates_v1"
                state["session_injection_mode"] = "none"
                state["execution_backend"] = "httpx_b_service"
                state["selected_backend"] = "httpx_b_service"
                state["final_backend"] = "httpx_b_service"
                state["backend_selection_reason"] = "p11c_add_from_candidates_out_of_range"
                state["client_profile"] = "b_service_client"
                return state

            selected_candidate = candidates[selected_index - 1]
            candidate_id = selected_candidate.get("candidate_id")
            if candidate_id in (None, ""):
                raise ValueError("候选项缺少 candidate_id")
            batch_id = context.get("batch_id")
            if batch_id in (None, ""):
                raise ValueError("最近一次搜索结果缺少 batch_id")

            b_client = BServiceClient()
            result = b_client.add_from_candidates(
                batch_id=int(batch_id),
                candidate_ids=[int(candidate_id)],
                source_type=str(context.get("source_type") or "discovery"),
            )
            state["status"] = "succeeded"
            state["result_summary"] = format_b_add_from_candidates_result(
                data=result,
                selected_index=selected_index,
                selected_candidate=selected_candidate,
            )
            state["platform"] = "ecom_watch"
            state["provider_id"] = "ecom_watch"
            state["capability"] = "monitor.add_from_candidates"
            state["readiness_status"] = "ready"
            state["endpoint_profile"] = "b_internal_monitor_add_from_candidates_v1"
            state["session_injection_mode"] = "none"
            state["execution_backend"] = "httpx_b_service"
            state["selected_backend"] = "httpx_b_service"
            state["final_backend"] = "httpx_b_service"
            state["backend_selection_reason"] = "p11c_add_from_candidates_chain"
            state["client_profile"] = "b_service_client"

        elif intent_code == "warehouse.query_inventory":
            result = execute_odoo_query_inventory(slots)
            state["status"] = "succeeded"
            state["result_summary"] = format_warehouse_query_inventory_result(result)
            state["platform"] = result["platform"]
            state["provider_id"] = result["provider_id"]
            state["capability"] = result["capability"]
            state["readiness_status"] = result["readiness_status"]
            state["endpoint_profile"] = result["endpoint_profile"]
            state["session_injection_mode"] = result["session_injection_mode"]
            state["provider_profile"] = result["provider_profile"]
            state["auth_profile"] = result["auth_profile"]
            state["request_adapter"] = result["request_adapter"]
            state["response_mapper"] = result["response_mapper"]
            state["credential_profile"] = result["credential_profile"]
            state["execution_backend"] = "internal_sandbox"
            state["selected_backend"] = "internal_sandbox"
            state["final_backend"] = "internal_sandbox"
            state["backend_selection_reason"] = "provider_capability_route"
            state["client_profile"] = "sandbox_http@odoo_inventory"

        elif intent_code == "warehouse.adjust_inventory":
            gate_allow, gate_reason = _evaluate_adjust_inventory_gate(slots)
            state["gate_reason"] = gate_reason
            state["gate_allow"] = gate_allow
            state["gate_status"] = "allow" if gate_allow else "blocked"
            if not gate_allow:
                state["status"] = "failed"
                state["result_summary"] = f"[warehouse.adjust_inventory] 门禁拦截：{gate_reason}"
                state["error_message"] = f"[gate_blocked] {gate_reason}"
                state["provider_id"] = "odoo"
                state["capability"] = "warehouse.adjust_inventory"
                state["readiness_status"] = "gate_blocked"
                state["endpoint_profile"] = "odoo_product_stock_v1"
                state["session_injection_mode"] = "header"
                state["execution_backend"] = "internal_sandbox"
                state["selected_backend"] = "internal_sandbox"
                state["final_backend"] = "internal_sandbox"
                state["backend_selection_reason"] = f"provider_capability_route|gate_blocked:{gate_reason}"
                state["client_profile"] = "sandbox_http@odoo_inventory_adjust"
                state["confirm_backend"] = "none"
                state["parsed_result"] = {
                    "failure_layer": "gate_blocked",
                    "operation_result": "gate_blocked_noop",
                    "gate_reason": gate_reason,
                    "verify_passed": False,
                    "verify_reason": gate_reason,
                    "target_task_id": task_id,
                    "original_update_task_id": task_id,
                    "confirm_task_id": "",
                    "confirm_backend": "none",
                }
                return state
            result = execute_odoo_adjust_inventory_prepare(task_id=task_id, slots=slots)
            state["status"] = "awaiting_confirmation"
            state["result_summary"] = format_warehouse_adjust_inventory_confirmation(result)
            state["platform"] = result["platform"]
            state["provider_id"] = result["provider_id"]
            state["capability"] = result["capability"]
            state["readiness_status"] = result["readiness_status"]
            state["endpoint_profile"] = result["endpoint_profile"]
            state["session_injection_mode"] = result["session_injection_mode"]
            state["provider_profile"] = result["provider_profile"]
            state["auth_profile"] = result["auth_profile"]
            state["request_adapter"] = result["request_adapter"]
            state["response_mapper"] = result["response_mapper"]
            state["credential_profile"] = result["credential_profile"]
            state["execution_backend"] = "internal_sandbox"
            state["selected_backend"] = "internal_sandbox"
            state["final_backend"] = "internal_sandbox"
            state["backend_selection_reason"] = "provider_capability_route|high_risk_requires_confirm"
            state["client_profile"] = "sandbox_http@odoo_inventory_adjust"
            state["confirm_backend"] = "none"
            # Structured audit fields (avoid parsing summary on confirm).
            pr = {
                "operation_result": "risk_adjust_inventory_pending",
                "old_inventory": result.get("old_inventory"),
                "delta": result.get("delta"),
                "target_inventory": result.get("target_inventory"),
                "target_task_id": task_id,
                "original_update_task_id": task_id,
                "confirm_task_id": "",
                "confirm_backend": "none",
            }
            state["parsed_result"] = pr

        elif intent_code == "customer.list_recent_conversations":
            result = execute_chatwoot_list_recent_conversations(slots)
            state["status"] = "succeeded"
            state["result_summary"] = format_chatwoot_recent_conversations_result(result)
            state["platform"] = result["platform"]
            state["provider_id"] = result["provider_id"]
            state["capability"] = result["capability"]
            state["readiness_status"] = result["readiness_status"]
            state["endpoint_profile"] = result["endpoint_profile"]
            state["session_injection_mode"] = result["session_injection_mode"]
            state["provider_profile"] = result["provider_profile"]
            state["auth_profile"] = result["auth_profile"]
            state["request_adapter"] = result["request_adapter"]
            state["response_mapper"] = result["response_mapper"]
            state["credential_profile"] = result["credential_profile"]
            state["execution_backend"] = "internal_sandbox"
            state["selected_backend"] = "internal_sandbox"
            state["final_backend"] = "internal_sandbox"
            state["backend_selection_reason"] = "provider_capability_route"
            state["client_profile"] = "sandbox_http@chatwoot_recent"
            
        elif intent_code == "system.confirm_task":
            result = execute_task_confirmation(executor, state, slots)
            if result.get("status") == "success":
                rpa_meta = result.pop("_rpa_meta", None)
                result.pop("rpa_evidence_paths", None)
                pr = result.get("parsed_result")
                if isinstance(pr, dict):
                    state["parsed_result"] = pr

                state["result_summary"] = format_task_confirmation_result(result)
                state["status"] = "succeeded"
                # P6.1: If confirm executed a controlled provider write, reflect it in observable fields
                # so /steps action_executed.detail can be used as evidence.
                if result.get("provider_id"):
                    state["provider_id"] = result.get("provider_id")
                if result.get("capability"):
                    state["capability"] = result.get("capability")
                if result.get("platform"):
                    state["platform"] = result.get("platform")
                if result.get("confirm_backend"):
                    state["confirm_backend"] = result.get("confirm_backend")
                # Default Odoo confirm observable fields (safe no-op for Woo path).
                if state.get("capability") == "warehouse.adjust_inventory":
                    state["readiness_status"] = "ready"
                    state["endpoint_profile"] = "odoo_product_stock_v1"
                    state["session_injection_mode"] = "header"
                    state["execution_backend"] = "internal_sandbox"
                    state["selected_backend"] = "internal_sandbox"
                    state["final_backend"] = "internal_sandbox"
                    state["backend_selection_reason"] = "confirm_controlled_write"
                    state["confirm_backend"] = state.get("confirm_backend") or "internal_sandbox"
                if rpa_meta:
                    state["execution_mode"] = rpa_meta.get("execution_mode", "rpa")
                    state["execution_backend"] = rpa_meta.get("execution_backend", "rpa_local_fake")
                    state["selected_backend"] = rpa_meta.get("selected_backend", "rpa_local_fake")
                    state["final_backend"] = rpa_meta.get("final_backend", "rpa_local_fake")
                    state["client_profile"] = "rpa_runner"
                    state["rpa_runner"] = rpa_meta.get("rpa_runner", "none")
                    state["evidence_count"] = int(rpa_meta.get("evidence_count", 0))
                    state["verify_mode"] = str(rpa_meta.get("verify_mode", "none"))
                    state["platform"] = result.get("platform", state.get("platform", "mock"))
                    if rpa_meta.get("execution_mode") == "api_then_rpa_verify":
                        state["backend_selection_reason"] = "api_then_rpa_verify_ok"
                else:
                    # Keep legacy confirm defaults, but do not overwrite controlled write fields.
                    state.setdefault("execution_backend", "mock_repo")
                    state.setdefault("client_profile", "mock_repo")
                if "verify_passed" in result:
                    state["verify_passed"] = result.get("verify_passed")
                    state["verify_reason"] = str(result.get("verify_reason", ""))
                    if result.get("api_price_after_update") is not None:
                        state["api_price_after_update"] = result.get("api_price_after_update")
                if isinstance(state.get("parsed_result"), dict):
                    state["target_task_id"] = state["parsed_result"].get("target_task_id", "")
                    state["original_update_task_id"] = state["parsed_result"].get("original_update_task_id", "")
                    state["confirm_task_id"] = state["parsed_result"].get("confirm_task_id", "")
                    state["operation_result"] = str(state["parsed_result"].get("operation_result") or state.get("operation_result") or "")
                if state.get("capability") == "warehouse.adjust_inventory":
                    _apply_adjust_inventory_governance_baseline(state, result)
                state["response_mapper"] = "none"
                state["request_adapter"] = "none"
                state["auth_profile"] = "none"
                state["provider_profile"] = "none"
                state["credential_profile"] = "none"
                logger.info("Task confirmed and executed successfully: task_id=%s", slots.get('task_id'))
            else:
                rpa_meta_fail = result.pop("_rpa_meta", None)
                prf = result.get("parsed_result")
                if isinstance(prf, dict):
                    state["parsed_result"] = prf
                # Preserve observable fields on confirm failure when available (P6.1 negative cases).
                if result.get("provider_id"):
                    state["provider_id"] = result.get("provider_id")
                if result.get("capability"):
                    state["capability"] = result.get("capability")
                if result.get("platform"):
                    state["platform"] = result.get("platform")
                if result.get("confirm_backend"):
                    state["confirm_backend"] = result.get("confirm_backend")
                err_msg = str(result.get("error") or "确认失败")
                failure_layer = _extract_confirm_failure_layer(result)
                state["failure_layer"] = failure_layer
                if isinstance(state.get("parsed_result"), dict):
                    state["target_task_id"] = state["parsed_result"].get("target_task_id", "")
                    state["original_update_task_id"] = state["parsed_result"].get("original_update_task_id", "")
                    state["confirm_task_id"] = state["parsed_result"].get("confirm_task_id", "")
                    state["operation_result"] = str(state["parsed_result"].get("operation_result") or state.get("operation_result") or "")
                    state["verify_passed"] = state["parsed_result"].get("verify_passed", state.get("verify_passed"))
                    state["verify_reason"] = str(state["parsed_result"].get("verify_reason") or state.get("verify_reason") or "")
                display_err = _strip_error_prefix(err_msg)
                state["error_message"] = f"[{failure_layer}] {display_err}" if display_err else f"[{failure_layer}]"
                state["status"] = "failed"
                state["result_summary"] = f"确认失败：{state['error_message']}"
                if state.get("capability") == "warehouse.adjust_inventory" or (
                    isinstance(state.get("parsed_result"), dict)
                    and state["parsed_result"].get("target_task_id")
                ):
                    _apply_adjust_inventory_governance_baseline(state, result)
                if rpa_meta_fail:
                    state["execution_mode"] = rpa_meta_fail.get("execution_mode", "rpa")
                    state["execution_backend"] = rpa_meta_fail.get("execution_backend", "rpa_local_fake")
                    state["selected_backend"] = rpa_meta_fail.get("selected_backend", "rpa_local_fake")
                    state["final_backend"] = rpa_meta_fail.get("final_backend", "rpa_local_fake")
                    state["client_profile"] = "rpa_runner"
                    state["rpa_runner"] = rpa_meta_fail.get("rpa_runner", "none")
                    state["evidence_count"] = int(rpa_meta_fail.get("evidence_count", 0))
                    state["verify_mode"] = str(rpa_meta_fail.get("verify_mode", "none"))
                    state["platform"] = rpa_meta_fail.get("platform", "woo")
                    if rpa_meta_fail.get("rpa_readiness_failed"):
                        state["backend_selection_reason"] = "rpa_readiness_failed"
                        rd = rpa_meta_fail.get("readiness_details") or {}
                        state["verify_passed"] = False
                        state["verify_reason"] = str(
                            rd.get("not_ready_reason") or rpa_meta_fail.get("verify_reason", "")
                        )
                    elif rpa_meta_fail.get("execution_mode") == "api_then_rpa_verify":
                        state["backend_selection_reason"] = "api_then_rpa_verify_failed"
                        state["verify_passed"] = bool(rpa_meta_fail.get("verify_passed", False))
                        state["verify_reason"] = str(rpa_meta_fail.get("verify_reason", ""))
                    else:
                        state["backend_selection_reason"] = "rpa_confirm_failed"
                logger.warning("Task confirmation failed: task_id=%s, error=%s", slots.get('task_id'), err_msg)
            
        elif intent_code == "product.update_price":
            result = execute_product_update_price(executor, state, slots)
            if result.get("requires_confirmation"):
                state["result_summary"] = format_price_update_confirmation(result)
                state["status"] = "awaiting_confirmation"
                state["execution_backend"] = "mock_repo"
                state["client_profile"] = "mock_repo"
                state["response_mapper"] = "none"
                state["request_adapter"] = "none"
                state["auth_profile"] = "none"
                state["provider_profile"] = "none"
                state["credential_profile"] = "none"
                logger.info("Price update awaiting confirmation: sku=%s, task_id=%s", slots.get('sku'), task_id)
            elif result.get("status") == "success":
                state["result_summary"] = format_price_update_result(result)
                state["status"] = "succeeded"
                state["execution_backend"] = "mock_repo"
                state["client_profile"] = "mock_repo"
                state["response_mapper"] = "none"
                state["request_adapter"] = "none"
                state["auth_profile"] = "none"
                state["provider_profile"] = "none"
                state["credential_profile"] = "none"
                logger.info("Price update executed successfully: sku=%s", slots.get('sku'))
            else:
                state["error_message"] = result.get("error", "Unknown error")
                state["status"] = "failed"
                state["result_summary"] = f"改价失败：{result.get('error')}"
                logger.warning("Price update failed: sku=%s, error=%s", slots.get('sku'), result.get('error'))
        else:
            state["error_message"] = f"Intent not implemented: {intent_code}"
            state["status"] = "failed"
            state["result_summary"] = f"命令 {intent_code} 尚未实现"
            logger.warning("Intent not implemented: %s", intent_code)
            
    except Exception as e:
        if isinstance(e, BServiceError):
            state["error_message"] = str(e)
            state["status"] = "failed"
            if intent_code == "ecom_watch.add_monitor_by_url":
                state["result_summary"] = f"加入监控失败：{str(e)}"
            elif intent_code == "ecom_watch.add_from_candidates":
                state["result_summary"] = f"加入监控失败：{str(e)}"
            elif intent_code == "ecom_watch.discovery_search":
                state["result_summary"] = f"搜索失败：{str(e)}"
            elif intent_code == "ecom_watch.manage_monitor_target":
                state["result_summary"] = f"操作失败：{str(e)}"
            elif intent_code == "ecom_watch.refresh_monitor_prices":
                state["result_summary"] = f"刷新失败：{str(e)}"
            elif intent_code == "ecom_watch.replace_monitor_target_url":
                state["result_summary"] = f"替换URL失败：{str(e)}"
            elif intent_code == "ecom_watch.refresh_monitor_target_price":
                state["result_summary"] = f"重新采集失败：{str(e)}"
            elif intent_code in ("ecom_watch.retry_price_probe", "ecom_watch.retry_price_probes"):
                state["result_summary"] = f"重试失败：{str(e)}"
            elif intent_code == "ecom_watch.monitor_summary":
                state["result_summary"] = f"总结失败：{str(e)}"
            elif intent_code == "ecom_watch.anomaly_explanation":
                state["result_summary"] = f"解释失败：{str(e)}"
            else:
                state["result_summary"] = f"查询失败：{str(e)}"
            state["platform"] = "ecom_watch"
            state["provider_id"] = "ecom_watch"
            state["capability"] = intent_code
            state["execution_backend"] = "httpx_b_service"
            state["selected_backend"] = "httpx_b_service"
            state["final_backend"] = "httpx_b_service"
            state["backend_selection_reason"] = "p10_query_chain_error"
            return state
        if intent_code == "product.query_sku_status" and execution_mode == "api":
            state["execution_backend"] = getattr(executor, "get_selected_backend", lambda: state.get("execution_backend", "sandbox_http_client"))()
            state["selected_backend"] = state["execution_backend"]
            state["client_profile"] = getattr(executor, "get_backend_profile", lambda: state.get("client_profile", "sandbox_http_client"))()
            state["request_adapter"] = getattr(executor, "get_request_adapter_name", lambda: state.get("request_adapter", "unknown"))()
            state["auth_profile"] = getattr(executor, "get_auth_profile", lambda: state.get("auth_profile", "unknown"))()
            state["credential_profile"] = getattr(
                executor, "get_credential_profile", lambda: state.get("credential_profile", "unknown")
            )()
            state["production_config_ready"] = getattr(
                executor, "get_production_config_ready", lambda: state.get("production_config_ready", "n/a")
            )()
            state["dry_run_enabled"] = getattr(executor, "get_dry_run_enabled", lambda: state.get("dry_run_enabled", "false"))()
            state["backend_selection_reason"] = getattr(
                executor, "get_backend_selection_reason", lambda: state.get("backend_selection_reason", "unknown")
            )()
            state["fallback_enabled"] = getattr(
                executor, "get_fallback_enabled", lambda: state.get("fallback_enabled", "false")
            )()
            state["fallback_applied"] = getattr(
                executor, "get_fallback_applied", lambda: state.get("fallback_applied", "false")
            )()
            state["fallback_target"] = getattr(
                executor, "get_fallback_target", lambda: state.get("fallback_target", "none")
            )()
            state["final_backend"] = getattr(
                executor, "get_final_backend", lambda: state.get("execution_backend", "sandbox_http_client")
            )()
            state["dry_run_failure"] = getattr(
                executor, "get_dry_run_failure", lambda: state.get("dry_run_failure", "none")
            )()
            if "recommended_strategy" not in state or state.get("recommended_strategy") == "n/a":
                state["recommended_strategy"] = str(get_woo_rollout_policy(execution_mode, state.get("platform", "woo"))["recommended_strategy"])
            state["live_probe_enabled"] = "true" if bool(settings.WOO_ENABLE_READONLY_LIVE_PROBE) else "false"
        state["error_message"] = str(e)
        state["status"] = "failed"
        state["result_summary"] = f"执行失败：{str(e)}"
        logger.error(
            "Action execution failed: intent=%s, execution_mode=%s, platform=%s, backend=%s, client=%s, mapper=%s, request_adapter=%s, auth_profile=%s, provider_profile=%s, credential_profile=%s, error=%s",
            intent_code,
            execution_mode,
            state.get("platform", "mock"),
            state.get("execution_backend", "unknown"),
            state.get("client_profile", "unknown"),
            state.get("response_mapper", "none"),
            state.get("request_adapter", "none"),
            state.get("auth_profile", "none"),
            state.get("provider_profile", "none"),
            state.get("credential_profile", "none"),
            str(e),
        )
    
    return state


def format_b_today_summary_result(data: dict) -> str:
    if not data:
        return "今日监控摘要暂无数据。"
    total = int(data.get("total_monitored_products") or 0)
    changed = int(data.get("changed_products_count") or 0)
    high_priority = int(data.get("high_priority_count") or 0)
    lines = [
        "今日监控摘要：",
        f"- 今日监控商品数：{total}",
        f"- 今日变化商品数：{changed}",
        f"- 高优先级数量：{high_priority}",
    ]
    top_items = data.get("top_items") if isinstance(data.get("top_items"), list) else []
    suggested_actions = (
        data.get("suggested_actions")
        if isinstance(data.get("suggested_actions"), list)
        else []
    )
    if changed == 0 and high_priority == 0 and not top_items:
        lines.append("- 今日暂无异常变化。")
    else:
        if top_items:
            lines.append("- 今日重点变化：")
            for idx, item in enumerate(top_items[:3], start=1):
                if isinstance(item, dict):
                    name = item.get("product_name") or item.get("name") or item.get("title") or "未命名商品"
                    desc = item.get("change_summary") or item.get("summary") or item.get("status") or "有变化"
                    lines.append(f"  {idx}. {name}：{desc}")
                else:
                    lines.append(f"  {idx}. {item}")
        if suggested_actions:
            lines.append("- 建议动作：")
            for idx, action in enumerate(suggested_actions[:3], start=1):
                lines.append(f"  {idx}. {action}")
    return "\n".join(lines)


def format_b_monitor_targets_result(data: dict) -> str:
    targets = data.get("targets")
    if not isinstance(targets, list):
        targets = data.get("items") if isinstance(data.get("items"), list) else []
    if not targets:
        return "当前没有活跃监控对象。"
    lines = [f"当前监控对象（共 {len(targets)} 个）："]
    for idx, item in enumerate(targets[:10], start=1):
        if isinstance(item, dict):
            pid = item.get("id") or item.get("product_id") or item.get("target_id") or "N/A"
            name = item.get("name") or item.get("product_name") or "未命名"
            status = item.get("status") or ("active" if item.get("is_active", True) else "inactive")
            lines.append(f"- {idx}. {name}（{status}，ID={pid}）")
        else:
            lines.append(f"- {idx}. {item}")
    return "\n".join(lines)


def format_b_monitor_probe_query_result(data: dict, *, query_type: str) -> str:
    raw_targets = data.get("targets")
    if not isinstance(raw_targets, list):
        raw_targets = data.get("items") if isinstance(data.get("items"), list) else []

    def _is_failed(item: dict) -> bool:
        status = str(item.get("price_probe_status") or "unknown").strip().lower()
        return status in {"failed", "fallback_mock"}

    def _is_mock(item: dict) -> bool:
        status = str(item.get("price_probe_status") or "unknown").strip().lower()
        source = str(item.get("price_source") or "").strip().lower()
        return status == "fallback_mock" or source == "mock_price"

    def _is_real(item: dict) -> bool:
        status = str(item.get("price_probe_status") or "unknown").strip().lower()
        source = str(item.get("price_source") or "").strip().lower()
        return status == "success" or source == "html_extract_preview"

    query_type = query_type if query_type in {"failed", "mock", "real"} else "failed"
    if query_type == "mock":
        matched = [item for item in raw_targets if isinstance(item, dict) and _is_mock(item)]
        title = "mock价格对象"
    elif query_type == "real":
        matched = [item for item in raw_targets if isinstance(item, dict) and _is_real(item)]
        title = "真实价格对象"
    else:
        matched = [item for item in raw_targets if isinstance(item, dict) and _is_failed(item)]
        title = "价格采集失败对象"

    lines = [f"{title}（共 {len(matched)} 个）："]
    if not matched:
        lines.append("无")
        return "\n".join(lines)

    display = matched[:10]
    for idx, item in enumerate(display, start=1):
        name = str(item.get("name") or item.get("product_name") or "未命名对象")
        pid = item.get("id") or item.get("product_id") or item.get("target_id") or "-"
        current_price = item.get("current_price")
        source = str(item.get("price_source") or "unknown")
        probe_status = str(item.get("price_probe_status") or "unknown")
        probe_error = str(item.get("price_probe_error") or "unknown")
        lines.extend(
            [
                f"{idx}. {name}",
                f"   对象ID：{pid}",
                f"   当前价格：{current_price if current_price is not None else '-'}",
                f"   来源：{source}",
                f"   状态：{probe_status}",
                f"   原因：{probe_error}",
            ]
        )
    if len(matched) > 10:
        lines.append(f"还有 {len(matched) - 10} 个对象未展示。")
    return "\n".join(lines)


def format_b_monitor_diagnostics_query_result(data: dict, *, query_type: str) -> str:
    raw_targets = data.get("targets")
    if not isinstance(raw_targets, list):
        raw_targets = data.get("items") if isinstance(data.get("items"), list) else []
    targets = [item for item in raw_targets if isinstance(item, dict)]

    def _pid(item: dict):
        return item.get("id") or item.get("product_id") or item.get("target_id") or "-"

    def _name(item: dict) -> str:
        return str(item.get("name") or item.get("product_name") or "未命名对象")

    def _line_price(value) -> str:
        return "-" if value is None else str(value)

    safe_query_type = query_type if query_type in {
        "price_anomaly",
        "low_confidence",
        "monitor_status",
        "monitor_overview",
        "high_priority_actions",
        "manual_review_required",
        "alert_candidates",
        "price_action_suggestions",
    } else "monitor_status"

    if safe_query_type == "price_anomaly":
        matched = [t for t in targets if str(t.get("price_anomaly_status") or "unknown").strip().lower() == "suspected"]
        lines = [f"价格异常对象（共 {len(matched)} 个）："]
        if not matched:
            lines.append("无")
            return "\n".join(lines)
        for idx, item in enumerate(matched[:10], start=1):
            lines.extend(
                [
                    f"{idx}. {_name(item)}",
                    f"   对象ID：{_pid(item)}",
                    f"   当前价格：{_line_price(item.get('current_price'))}",
                    f"   上次价格：{_line_price(item.get('last_price'))}",
                    f"   异常状态：{str(item.get('price_anomaly_status') or 'unknown')}",
                    f"   异常原因：{str(item.get('price_anomaly_reason') or '-')}",
                    f"   建议：{str(item.get('price_action_suggestion') or '-')}",
                ]
            )
        if len(matched) > 10:
            lines.append(f"还有 {len(matched) - 10} 个对象未展示。")
        return "\n".join(lines)

    if safe_query_type == "low_confidence":
        matched = [
            t for t in targets
            if str(t.get("price_confidence") or "unknown").strip().lower() in {"low", "unknown"}
        ]
        lines = [f"低可信价格对象（共 {len(matched)} 个）："]
        if not matched:
            lines.append("无")
            return "\n".join(lines)
        for idx, item in enumerate(matched[:10], start=1):
            lines.extend(
                [
                    f"{idx}. {_name(item)}",
                    f"   对象ID：{_pid(item)}",
                    f"   来源：{str(item.get('price_source') or 'unknown')}",
                    f"   可信度：{str(item.get('price_confidence') or 'unknown')}",
                    f"   页面类型：{str(item.get('price_page_type') or 'unknown')}",
                    f"   建议：{str(item.get('price_action_suggestion') or '-')}",
                ]
            )
        if len(matched) > 10:
            lines.append(f"还有 {len(matched) - 10} 个对象未展示。")
        return "\n".join(lines)

    if safe_query_type == "high_priority_actions":
        matched = [
            t for t in targets
            if str(t.get("action_priority") or "unknown").strip().lower() == "high"
        ]
        lines = [f"高优先级处理对象（共 {len(matched)} 个）："]
        if not matched:
            lines.append("无")
            return "\n".join(lines)
        for idx, item in enumerate(matched[:10], start=1):
            lines.extend(
                [
                    f"{idx}. {_name(item)}",
                    f"   对象ID：{_pid(item)}",
                    f"   优先级：{str(item.get('action_priority') or 'unknown')}",
                    f"   类型：{str(item.get('action_category') or 'unknown')}",
                    f"   建议：{str(item.get('action_suggestion') or '-')}",
                ]
            )
        if len(matched) > 10:
            lines.append(f"还有 {len(matched) - 10} 个对象未展示。")
        return "\n".join(lines)

    if safe_query_type == "manual_review_required":
        matched = [t for t in targets if bool(t.get("manual_review_required", False))]
        lines = [f"人工接管对象（共 {len(matched)} 个）："]
        if not matched:
            lines.append("无")
            return "\n".join(lines)
        for idx, item in enumerate(matched[:10], start=1):
            lines.extend(
                [
                    f"{idx}. {_name(item)}",
                    f"   对象ID：{_pid(item)}",
                    f"   优先级：{str(item.get('action_priority') or 'unknown')}",
                    f"   类型：{str(item.get('action_category') or 'unknown')}",
                    f"   建议：{str(item.get('action_suggestion') or '-')}",
                ]
            )
        if len(matched) > 10:
            lines.append(f"还有 {len(matched) - 10} 个对象未展示。")
        return "\n".join(lines)

    if safe_query_type == "alert_candidates":
        matched = [t for t in targets if bool(t.get("alert_candidate", False))]
        lines = [f"提醒候选对象（共 {len(matched)} 个）："]
        if not matched:
            lines.append("无")
            return "\n".join(lines)
        for idx, item in enumerate(matched[:10], start=1):
            delta = item.get("price_delta")
            delta_percent = item.get("price_delta_percent")
            if delta is None:
                change_line = "-"
            else:
                trend = "上涨" if float(delta) > 0 else ("下降" if float(delta) < 0 else "持平")
                if delta_percent is None:
                    change_line = f"{trend} {abs(float(delta))}"
                else:
                    change_line = f"{trend} {abs(float(delta))}（{float(delta_percent):+.2f}%）"
            lines.extend(
                [
                    f"{idx}. {_name(item)}",
                    f"   对象ID：{_pid(item)}",
                    f"   当前价：{_line_price(item.get('current_price'))}",
                    f"   上次价：{_line_price(item.get('last_price'))}",
                    f"   变化：{change_line}",
                    f"   建议：{str(item.get('action_suggestion') or '-')}",
                ]
            )
        if len(matched) > 10:
            lines.append(f"还有 {len(matched) - 10} 个对象未展示。")
        return "\n".join(lines)

    if safe_query_type == "price_action_suggestions":
        lines = [f"价格处理建议（共 {len(targets)} 个，展示前 10 个）："]
        if not targets:
            lines.append("无")
            return "\n".join(lines)
        for idx, item in enumerate(targets[:10], start=1):
            lines.extend(
                [
                    f"{idx}. {_name(item)}",
                    f"   对象ID：{_pid(item)}",
                    f"   优先级：{str(item.get('action_priority') or 'unknown')}",
                    f"   类型：{str(item.get('action_category') or 'unknown')}",
                    f"   建议：{str(item.get('action_suggestion') or '-')}",
                ]
            )
        if len(targets) > 10:
            lines.append(f"还有 {len(targets) - 10} 个对象未展示。")
        return "\n".join(lines)

    high = sum(1 for t in targets if str(t.get("price_confidence") or "unknown").strip().lower() == "high")
    medium = sum(1 for t in targets if str(t.get("price_confidence") or "unknown").strip().lower() == "medium")
    low = sum(1 for t in targets if str(t.get("price_confidence") or "unknown").strip().lower() == "low")
    suspected = sum(1 for t in targets if str(t.get("price_anomaly_status") or "unknown").strip().lower() == "suspected")
    mock_or_fallback = sum(
        1
        for t in targets
        if str(t.get("price_source") or "").strip().lower() == "mock_price"
        or str(t.get("price_probe_status") or "").strip().lower() == "fallback_mock"
    )
    lines = [
        "价格监控状态",
        "",
        f"监控对象总数：{len(targets)}",
        f"高可信价格：{high}",
        f"中可信价格：{medium}",
        f"低可信价格：{low}",
        f"异常价格：{suspected}",
        f"mock/fallback：{mock_or_fallback}",
    ]
    if safe_query_type == "monitor_overview":
        lines.extend(
            [
                "",
                "建议：",
                f"- 优先复查 {suspected} 个异常价格对象",
                f"- 处理 {low} 个低可信对象",
                "- mock/fallback 对象不建议用于价格决策",
            ]
        )
    return "\n".join(lines)


def format_b_retry_price_probe_result(data: dict) -> str:
    target_id = data.get("product_id") or "-"
    probe_status = str(data.get("price_probe_status") or "unknown")
    probe_error = str(data.get("price_probe_error") or "unknown")
    price_source = str(data.get("price_source") or "unknown")
    current_price = data.get("current_price")
    eligible = bool(data.get("eligible", False))
    retried = bool(data.get("retried", False))

    if not eligible:
        return "\n".join(
            [
                "该对象当前不在重试范围内。",
                f"对象ID：{target_id}",
                f"状态：{probe_status}",
                f"来源：{price_source}",
            ]
        )

    if retried and probe_status == "success":
        return "\n".join(
            [
                "价格采集重试成功。",
                f"对象ID：{target_id}",
                f"当前价格：{current_price if current_price is not None else '-'}",
                f"来源：{price_source}",
            ]
        )

    return "\n".join(
        [
            "价格采集重试后仍未成功。",
            f"对象ID：{target_id}",
            f"状态：{probe_status}",
            f"原因：{probe_error}",
            f"来源：{price_source}",
        ]
    )


def format_b_retry_price_probes_result(data: dict) -> str:
    total = int(data.get("retried") or data.get("total_candidates") or 0)
    success = int(data.get("success") or 0)
    still_failed = int(data.get("still_failed") or 0)
    lines = [
        "价格采集重试完成。",
        "",
        f"重试对象：{total} 个",
        f"成功转真实价格：{success} 个",
        f"仍失败：{still_failed} 个",
    ]
    run_id = str(data.get("run_id") or "").strip()
    if run_id:
        lines.append(f"重试批次：{run_id}")
    return "\n".join(lines)


def format_b_refresh_monitor_prices_result(data: dict) -> str:
    run_id = str(data.get("run_id") or "").strip()
    status = str(data.get("status") or "unknown").strip()
    total = int(data.get("total") or 0)
    refreshed = int(data.get("refreshed") or 0)
    changed = int(data.get("changed") or 0)
    failed = int(data.get("failed") or 0)
    duration_ms = int(data.get("duration_ms") or 0)
    items = data.get("changed_items")
    if not isinstance(items, list):
        raw_items = data.get("items")
        if isinstance(raw_items, list):
            items = [item for item in raw_items if isinstance(item, dict) and item.get("price_changed") is True]
        else:
            items = []

    if changed <= 0:
        lines = ["监控价格已刷新。"]
        if run_id:
            lines.append(f"刷新批次：{run_id}")
        lines.extend(
            [
                f"状态：{status}",
                "本轮暂无价格变化。",
                f"总对象数：{total}",
                f"成功刷新：{refreshed}",
                f"失败：{failed}",
            ]
        )
        if duration_ms > 0:
            lines.append(f"耗时：{duration_ms}ms")
        return "\n".join(lines)

    def _format_delta_line(item: dict) -> str:
        delta_raw = item.get("price_delta")
        percent_raw = item.get("price_delta_percent")
        try:
            delta = float(delta_raw)
        except Exception:
            delta = 0.0

        if delta > 0:
            trend = "上涨"
        elif delta < 0:
            trend = "下降"
        else:
            trend = "持平"

        abs_delta = abs(delta)
        if percent_raw is None:
            return f"{trend} {abs_delta:g}"

        try:
            percent = float(percent_raw)
            return f"{trend} {abs_delta:g}（{percent:+.2f}%）"
        except Exception:
            return f"{trend} {abs_delta:g}"

    display_items = items[:5]
    unchanged = max(total - changed, 0)
    lines = ["监控价格已刷新。"]
    if run_id:
        lines.append(f"刷新批次：{run_id}")
    lines.extend(
        [
            f"状态：{status}",
            f"总对象数：{total}",
            f"成功刷新：{refreshed}",
            f"本轮价格变化：{changed}",
            f"失败：{failed}",
        ]
    )
    if duration_ms > 0:
        lines.append(f"耗时：{duration_ms}ms")
    lines.extend(["", "变化对象："])
    for idx, item in enumerate(display_items, start=1):
        name = str(item.get("product_name") or f"对象#{item.get('product_id') or idx}")
        current_price = item.get("current_price")
        last_price = item.get("last_price")
        lines.extend(
            [
                f"{idx}. {name}",
                f"   当前价：{current_price if current_price is not None else '-'}",
                f"   上次价：{last_price if last_price is not None else '-'}",
                f"   变化：{_format_delta_line(item)}",
                "",
            ]
        )
    if changed > len(display_items):
        lines.append(f"还有 {changed - len(display_items)} 个价格变化对象未展示。")
        lines.append("")
    lines.append(f"未变化：{unchanged} 个")
    return "\n".join(lines)


def format_b_price_refresh_run_detail_result(data: dict) -> str:
    run_id = str(data.get("run_id") or "").strip()
    status = str(data.get("status") or "unknown").strip()
    total = int(data.get("total") or 0)
    refreshed = int(data.get("refreshed") or 0)
    changed = int(data.get("changed") or 0)
    failed = int(data.get("failed") or 0)
    duration_ms = int(data.get("duration_ms") or 0)
    items = data.get("items") if isinstance(data.get("items"), list) else []
    changed_items = [item for item in items if isinstance(item, dict) and item.get("price_changed") is True]

    lines = [
        f"价格刷新结果：{run_id or '-'}",
        f"状态：{status}",
        f"总对象数：{total}",
        f"成功刷新：{refreshed}",
        f"价格变化：{changed}",
        f"失败：{failed}",
    ]
    if duration_ms > 0:
        lines.append(f"耗时：{duration_ms}ms")
    if not changed_items:
        lines.extend(["", "变化对象：", "无"])
        return "\n".join(lines)

    def _format_delta_line(item: dict) -> str:
        delta_raw = item.get("price_delta")
        percent_raw = item.get("price_delta_percent")
        try:
            delta = float(delta_raw)
        except Exception:
            delta = 0.0
        if delta > 0:
            trend = "上涨"
        elif delta < 0:
            trend = "下降"
        else:
            trend = "持平"
        abs_delta = abs(delta)
        if percent_raw is None:
            return f"{trend} {abs_delta:g}"
        try:
            percent = float(percent_raw)
            return f"{trend} {abs_delta:g}（{percent:+.2f}%）"
        except Exception:
            return f"{trend} {abs_delta:g}"

    lines.extend(["", "变化对象："])
    for idx, item in enumerate(changed_items[:5], start=1):
        name = str(item.get("product_name") or f"对象#{item.get('product_id') or idx}")
        current_price = item.get("current_price")
        last_price = item.get("last_price")
        lines.extend(
            [
                f"{idx}. {name}",
                f"   当前价：{current_price if current_price is not None else '-'}",
                f"   上次价：{last_price if last_price is not None else '-'}",
                f"   变化：{_format_delta_line(item)}",
            ]
        )
    if len(changed_items) > 5:
        lines.append(f"... 还有 {len(changed_items) - 5} 个变化对象未展示")
    return "\n".join(lines)


def format_b_monitor_price_history_result(
    data: dict,
    target_id: int,
    *,
    query_mode: str = "target_id",
    selected_index: int | None = None,
    ambiguous_input: bool = False,
) -> str:
    snapshots = data.get("snapshots")
    if not isinstance(snapshots, list):
        snapshots = []
    if not snapshots:
        return "该监控对象暂未产生价格历史。\n请先发送：刷新监控价格"

    display_rows = snapshots[:5]
    first = display_rows[0] if isinstance(display_rows[0], dict) else {}
    name = str(
        data.get("product_name")
        or data.get("name")
        or first.get("product_name")
        or first.get("name")
        or "监控对象"
    )
    title = f"价格历史：{name}（对象ID={target_id}）"
    lines = [title]
    if query_mode == "list_index" and selected_index is not None:
        lines.append(f"本次按列表序号查询：第 {selected_index} 个监控对象。")
    elif ambiguous_input:
        lines.append(f"本次按对象ID查询：{target_id}。")
        lines.append(f"如果你想按列表序号查询，请发送：查看第 {target_id} 个价格历史")
    lines.append("")
    for idx, item in enumerate(display_rows, start=1):
        if not isinstance(item, dict):
            continue
        checked_at = str(item.get("checked_at") or "-")
        checked_at = checked_at.replace("T", " ")[:16] if checked_at != "-" else checked_at
        price = item.get("price")
        price_line = str(price) if price is not None else "N/A"
        delta = item.get("price_delta")
        delta_percent = item.get("price_delta_percent")
        if delta is None:
            change_line = "首次记录"
        else:
            delta_value = float(delta)
            if delta_value > 0:
                trend = "上涨"
            elif delta_value < 0:
                trend = "下降"
            else:
                trend = "持平"
            abs_delta = abs(delta_value)
            if delta_percent is None:
                change_line = f"{trend} {abs_delta:g}"
            else:
                change_line = f"{trend} {abs_delta:g}（{float(delta_percent):+.2f}%）"
        source = str(item.get("price_source") or "mock_price")
        lines.extend(
            [
                f"{idx}. {checked_at}",
                f"   当前价：{price_line}",
                f"   变化：{change_line}",
                f"   来源：{source}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def format_b_product_detail_result(data: dict, product_id: int) -> str:
    if not data:
        return f"商品 {product_id} 暂无详情数据。"
    name = data.get("name") or data.get("product_name") or "未命名"
    status = data.get("status") or ("active" if data.get("is_active", True) else "inactive")
    price = data.get("price") if data.get("price") is not None else "N/A"
    summary = data.get("summary") or data.get("latest_summary") or ""
    lines = [
        f"商品详情 #{product_id}",
        f"- 名称：{name}",
        f"- 状态：{status}",
        f"- 价格：{price}",
    ]
    if summary:
        lines.append(f"- 摘要：{summary}")
    return "\n".join(lines)


def format_b_add_monitor_by_url_result(data: dict, url: str) -> str:
    target = None
    targets = data.get("targets")
    if isinstance(targets, list) and targets:
        target = targets[0] if isinstance(targets[0], dict) else None
    source = target if isinstance(target, dict) else data
    name = source.get("name") or source.get("product_name") or source.get("title")
    target_id = source.get("target_id") or source.get("id") or source.get("product_id")
    status = source.get("status") or ("active" if source.get("is_active", True) else "inactive")
    lines = ["已加入监控。", f"- URL：{url}"]
    if name:
        lines.append(f"- 名称：{name}")
    if target_id is not None:
        lines.append(f"- 对象ID：{target_id}")
    if status:
        lines.append(f"- 状态：{status}")
    return "\n".join(lines)


def format_b_replace_monitor_target_url_result(data: dict, *, target_id: int, product_url: str) -> str:
    target = data.get("target") if isinstance(data.get("target"), dict) else None
    source = target if isinstance(target, dict) else data
    confidence = str(source.get("price_confidence") or "unknown")
    page_type = str(source.get("price_page_type") or "unknown")
    lines = [
        "已更新监控对象 URL。",
        f"- 对象ID：{target_id}",
        f"- 新URL：{product_url}",
        "- 已重置采集诊断字段（status/error/confidence/page_type）",
        f"- 当前可信度：{confidence}",
        f"- 当前页面类型：{page_type}",
        f"- 建议下一步：重新采集对象 {target_id}",
    ]
    return "\n".join(lines)


def format_b_refresh_monitor_target_price_result(data: dict, target_id: int) -> str:
    source = data.get("target") if isinstance(data.get("target"), dict) else data
    probe_status = str(source.get("price_probe_status") or "unknown")
    confidence = str(source.get("price_confidence") or "unknown")
    page_type = str(source.get("price_page_type") or "unknown")
    lines = [
        "已触发重新采集。",
        f"- 对象ID：{target_id}",
        f"- 采集状态：{probe_status}",
        f"- 可信度：{confidence}",
        f"- 页面类型：{page_type}",
    ]
    return "\n".join(lines)


def format_b_add_from_candidates_result(data: dict, selected_index: int, selected_candidate: dict) -> str:
    target = None
    targets = data.get("targets")
    if isinstance(targets, list) and targets:
        target = targets[0] if isinstance(targets[0], dict) else None
    source = target if isinstance(target, dict) else data
    name = (
        source.get("name")
        or source.get("product_name")
        or source.get("title")
        or selected_candidate.get("title")
    )
    url = source.get("url") or source.get("product_url") or selected_candidate.get("url")
    target_id = source.get("target_id") or source.get("id") or source.get("product_id")
    status = source.get("status") or ("active" if source.get("is_active", True) else "inactive")
    lines = ["已加入监控。", f"- 选择编号：第 {selected_index} 个"]
    if name:
        lines.append(f"- 名称：{name}")
    if url:
        lines.append(f"- URL：{url}")
    if target_id is not None:
        lines.append(f"- 对象ID：{target_id}")
    if status:
        lines.append(f"- 状态：{status}")
    return "\n".join(lines)


def format_b_discovery_batch_result(data: dict, query: str) -> str:
    batch_id = data.get("batch_id")
    candidates = data.get("candidates")
    if not isinstance(candidates, list):
        candidates = []
    if not candidates:
        if batch_id is None:
            return f"搜索结果：{query}\n暂未找到候选结果。"
        return f"搜索结果：{query}\n批次：{batch_id}\n暂未找到候选结果。"
    display_candidates = candidates[:5]
    lines = [f"搜索结果：{query}"]
    if batch_id is not None:
        lines.append(f"批次：{batch_id}")
    lines.append(f"候选（展示前 {len(display_candidates)} 条）：")
    for idx, candidate in enumerate(display_candidates, start=1):
        if not isinstance(candidate, dict):
            lines.append(f"{idx}. {candidate}")
            continue
        title = str(candidate.get("title") or candidate.get("name") or "未命名候选")
        url = str(candidate.get("url") or candidate.get("product_url") or "N/A")
        source = str(
            candidate.get("domain")
            or candidate.get("site")
            or candidate.get("source")
            or candidate.get("source_type")
            or "未知"
        )
        lines.append(f"{idx}. {title}")
        lines.append(f"   URL: {url}")
        lines.append(f"   来源: {source}")
    return "\n".join(lines)


def execute_product_query_sku_status(executor, slots: dict, execution_mode: str) -> dict:
    """
    Execute product.query_sku_status action.
    
    Args:
        slots: Extracted slots (sku, platform)
        
    Returns:
        Product data
    """
    sku = slots.get('sku')
    platform = resolve_query_platform(execution_mode, slots.get("platform"))
    
    if not sku:
        raise ValueError("SKU is required")
    
    # Query mock repository
    product_data = executor.query_sku_status(sku, platform)
    
    if not product_data:
        return {
            'sku': sku,
            'product_name': '未找到',
            'status': 'not_found',
            'inventory': 0,
            'price': 0,
            'platform': platform
        }
    
    return product_data


def format_product_query_result(product_data: dict) -> str:
    """
    Format product query result as text message.
    
    Args:
        product_data: Product data dict
        
    Returns:
        Formatted text message
    """
    return (
        f"SKU: {product_data.get('sku', 'N/A')}\n"
        f"商品：{product_data.get('product_name', 'N/A')}\n"
        f"状态：{product_data.get('status', 'N/A')}\n"
        f"库存：{product_data.get('inventory', 0)}\n"
        f"价格：{product_data.get('price', 0)}\n"
        f"平台：{product_data.get('platform', 'mock')}"
    )


def execute_odoo_query_inventory(slots: dict) -> dict:
    sku = str(slots.get("sku") or "").strip().upper()
    if not sku:
        raise ValueError("SKU is required")
    provider = "odoo"
    capability = "warehouse.query_inventory"
    readiness = check_platform_provider_readiness(provider, capability=capability)
    if not readiness.ready:
        raise ValueError(f"[provider_readiness_failed] {readiness.reason}")
    profile = resolve_provider_profile(provider)
    # P6.0: make Odoo readonly use the same observable provider chain
    # (provider profile + request adapter + internal sandbox route + mapper)
    client = OdooInventoryClient(
        base_url=settings.PRODUCT_QUERY_SKU_API_BASE_URL or "internal://sandbox",
        timeout_seconds=max(int(settings.PRODUCT_QUERY_SKU_API_TIMEOUT_MS), 1) / 1000.0,
    )
    try:
        inv = client.query_inventory(sku)
    except OdooInventoryClientNotFound:
        inv = None
    except (OdooInventoryClientDisabled, OdooInventoryClientTimeout) as exc:
        raise ValueError(f"[provider_upstream_unavailable] {exc}") from exc
    except OdooInventoryClientRequestError as exc:
        raise ValueError(f"[provider_request_invalid] {exc}") from exc
    except OdooInventoryClientError as exc:
        raise ValueError(f"[provider_client_error] {exc}") from exc

    inventory = int(inv.inventory) if inv else 0
    status = str(inv.status) if inv else "not_found"
    return {
        "sku": sku,
        "inventory": inventory,
        "status": status,
        "product_name": (inv.product_name if inv else "未找到"),
        "platform": provider,
        "provider_id": provider,
        "capability": capability,
        "readiness_status": readiness.reason,
        "endpoint_profile": profile.endpoint_profile,
        "session_injection_mode": profile.session_injection_mode,
        "provider_profile": profile.provider_name,
        "auth_profile": profile.auth_profile_name,
        "request_adapter": client.last_request_adapter if "client" in locals() else profile.request_adapter_name,
        "response_mapper": client.last_mapper if "client" in locals() else profile.response_mapper_name,
        "credential_profile": readiness.credential_profile,
    }


def format_warehouse_query_inventory_result(result: dict) -> str:
    return (
        f"SKU: {result.get('sku')}\n"
        f"商品：{result.get('product_name', 'N/A')}\n"
        f"库存：{result.get('inventory')}\n"
        f"状态：{result.get('status')}\n"
        f"平台：{result.get('platform')}\n"
        f"provider_id：{result.get('provider_id')}\n"
        f"capability：{result.get('capability')}\n"
        f"readiness：{result.get('readiness_status')}"
    )


def execute_chatwoot_list_recent_conversations(slots: dict) -> dict:
    provider = "chatwoot"
    capability = "customer.list_recent_conversations"
    readiness = check_platform_provider_readiness(provider, capability=capability)
    if not readiness.ready:
        raise ValueError(f"[provider_readiness_failed] {readiness.reason}")
    profile = resolve_provider_profile(provider)
    limit = int(slots.get("limit") or 5)
    if limit <= 0:
        limit = 5
    conversations = [
        {"conversation_id": 123, "status": "open", "last_message": "您好，请问订单什么时候发货？"},
        {"conversation_id": 122, "status": "pending", "last_message": "可以帮我改收货地址吗？"},
        {"conversation_id": 121, "status": "resolved", "last_message": "收到，谢谢！"},
        {"conversation_id": 120, "status": "open", "last_message": "申请退款，商品有破损。"},
        {"conversation_id": 119, "status": "pending", "last_message": "物流单号查不到。"},
    ][:limit]
    return {
        "platform": provider,
        "provider_id": provider,
        "capability": capability,
        "readiness_status": readiness.reason,
        "endpoint_profile": profile.endpoint_profile,
        "session_injection_mode": profile.session_injection_mode,
        "provider_profile": profile.provider_name,
        "auth_profile": profile.auth_profile_name,
        "request_adapter": profile.request_adapter_name,
        "response_mapper": profile.response_mapper_name,
        "credential_profile": readiness.credential_profile,
        "limit": limit,
        "conversations": conversations,
    }


def format_chatwoot_recent_conversations_result(result: dict) -> str:
    conversations = result.get("conversations") or []
    first = conversations[0] if conversations else {}
    return (
        f"平台：{result.get('platform')}\n"
        f"最近会话数：{len(conversations)} (limit={result.get('limit')})\n"
        f"最新会话ID：{first.get('conversation_id', 'N/A')}\n"
        f"最新状态：{first.get('status', 'N/A')}\n"
        f"最新消息：{first.get('last_message', 'N/A')}\n"
        f"provider_id：{result.get('provider_id')}\n"
        f"capability：{result.get('capability')}\n"
        f"readiness：{result.get('readiness_status')}"
    )


def execute_task_confirmation(executor, state: dict, slots: dict) -> dict:
    """
    Execute task confirmation (for awaiting_confirmation tasks).
    
    Args:
        state: Current graph state
        slots: Extracted slots (task_id) - this is the ORIGINAL task_id to confirm
        
    Returns:
        Execution result dict
    """
    confirmed_task_id = slots.get('task_id')
    current_task_id = state.get('task_id', '')
    
    def _confirm_failure_parsed(
        failure_layer: str,
        *,
        target_task_id: str | None,
        verify_reason: str | None = None,
    ) -> dict:
        return {
            "confirm_task_id": current_task_id or None,
            "target_task_id": target_task_id,
            "original_update_task_id": target_task_id,
            "old_price": None,
            "new_price": None,
            "post_save_price": None,
            "verify_passed": False,
            "verify_reason": verify_reason or failure_layer,
            "operation_result": "confirm_blocked_noop",
            "failure_layer": failure_layer,
        }

    if not confirmed_task_id:
        return {
            "error": "[confirm_target_invalid] 缺少任务号",
            "error_code": "confirm_target_invalid",
            "target_task_id": None,
            "original_update_task_id": None,
            "confirm_task_id": current_task_id or None,
            "parsed_result": _confirm_failure_parsed("confirm_target_invalid", target_task_id=None),
        }
    
    # Query the task record to confirm (use the extracted task_id from text, NOT current task's id)
    db = SessionLocal()
    try:
        # First, update current confirmation task to point to the original task
        current_task = db.query(TaskRecord).filter(TaskRecord.task_id == current_task_id).first()
        if current_task:
            current_task.target_task_id = confirmed_task_id
            db.commit()
        
        task_record = db.query(TaskRecord).filter(TaskRecord.task_id == confirmed_task_id).first()
        if not task_record:
            return {
                "error": f"[confirm_target_invalid] 任务 {confirmed_task_id} 不存在",
                "error_code": "confirm_target_invalid",
                "target_task_id": confirmed_task_id,
                "original_update_task_id": confirmed_task_id,
                "confirm_task_id": current_task_id or None,
                "parsed_result": _confirm_failure_parsed("confirm_target_invalid", target_task_id=confirmed_task_id),
            }
        
        # Single source of truth for confirm idempotency:
        # only awaiting_confirmation can be consumed by confirm.
        if task_record.status != 'awaiting_confirmation':
            if task_record.status in {"succeeded", "failed", "processing"}:
                layer = "confirm_target_already_consumed"
                reason = f"already_consumed_status={task_record.status}"
            else:
                layer = "confirm_target_invalid"
                reason = f"invalid_target_status={task_record.status}"
            return {
                "error": f"[{layer}] 任务 {confirmed_task_id} 状态为 {task_record.status}，无需确认",
                "error_code": layer,
                "target_task_id": confirmed_task_id,
                "original_update_task_id": confirmed_task_id,
                "confirm_task_id": current_task_id or None,
                "parsed_result": _confirm_failure_parsed(
                    layer,
                    target_task_id=confirmed_task_id,
                    verify_reason=reason,
                ),
            }

        # P6.1: For Odoo adjust_inventory, confirm must read structured risk context from TaskSteps,
        # never parse natural language summary.
        risk_ctx = _load_risk_context_from_steps(db, target_task_id=confirmed_task_id)
        is_adjust_inventory = str(task_record.result_summary or "").startswith("[warehouse.adjust_inventory]")
        if is_adjust_inventory:
            ok, layer, missing = _validate_adjust_inventory_risk_context(risk_ctx)
            if not ok:
                reason = layer
                if missing:
                    reason = f"{layer}:missing={','.join(missing)}"
                return {
                    "error": f"[{layer}] 目标任务 risk_context 不可用，禁止回退到文案解析 ({reason})",
                    "error_code": layer,
                    "platform": "odoo",
                    "provider_id": "odoo",
                    "capability": "warehouse.adjust_inventory",
                    "confirm_backend": "none",
                    "target_task_id": confirmed_task_id,
                    "original_update_task_id": confirmed_task_id,
                    "confirm_task_id": current_task_id or None,
                    "parsed_result": {
                        "failure_layer": layer,
                        "operation_result": "confirm_blocked_noop",
                        "verify_passed": False,
                        "verify_reason": reason,
                        "old_inventory": None,
                        "delta": None,
                        "target_inventory": None,
                        "post_inventory": None,
                        "target_task_id": confirmed_task_id,
                        "original_update_task_id": confirmed_task_id,
                        "confirm_task_id": current_task_id or None,
                        "confirm_backend": "none",
                    },
                }
            return _confirm_execute_odoo_adjust_inventory(
                db,
                state=state,
                current_task_id=current_task_id,
                target_task_id=confirmed_task_id,
                ctx=risk_ctx if isinstance(risk_ctx, dict) else {},
                task_record=task_record,
            )
        
        # Parse the original intent from task record
        # The intent_text should contain the original price update command
        # We need to re-execute the price update
        
        # For now, we'll store the original slots in a simple way
        # In a more sophisticated implementation, we would store slots in the DB
        # For this mock, we'll extract from result_summary which contains SKU and price
        
        result_summary = task_record.result_summary or ''
        # Extract SKU and target_price from result_summary
        # Format: "[product.update_price] ⚠️ 检测到高风险操作：修改价格\nSKU: A001\n当前价格：59.9\n目标价格：59.9\n任务号：TASK-xxx"
        
        sku_match = re.search(r'SKU:\s*([A-Z0-9]+)', result_summary, re.IGNORECASE)
        price_match = re.search(r'目标价格：\s*(\d+(?:\.\d+)?)', result_summary)
        
        if not sku_match or not price_match:
            return {
                "error": "[confirm_target_invalid] 无法从原任务中提取 SKU 和价格信息",
                "error_code": "confirm_target_invalid",
                "target_task_id": confirmed_task_id,
                "original_update_task_id": confirmed_task_id,
                "confirm_task_id": current_task_id or None,
                "parsed_result": _confirm_failure_parsed("confirm_target_invalid", target_task_id=confirmed_task_id),
            }
        
        sku = sku_match.group(1)
        target_price = float(price_match.group(1))

        confirm_backend = (settings.PRODUCT_UPDATE_PRICE_CONFIRM_EXECUTION_BACKEND or "mock").lower().strip()

        if confirm_backend == "rpa":
            trace_id = (state.get("source_message_id") or "").strip() or current_task_id
            log_step(
                current_task_id,
                "rpa_execution_started",
                "processing",
                f"target_task_id={confirmed_task_id} sku={sku} trace_id={trace_id}",
            )
            legacy, rpa_err = run_confirm_update_price_rpa(
                confirm_task_id=current_task_id,
                trace_id=trace_id,
                sku=sku,
                target_price=target_price,
                platform="woo",
            )
            if rpa_err:
                ec = rpa_err.get("error_code") or "rpa_error"
                paths = rpa_err.get("evidence_paths") or []
                detail = f"error_code={ec} msg={rpa_err.get('error', '')}"[:900]
                log_step(current_task_id, "rpa_execution_failed", "failed", detail)
                if paths:
                    log_step(
                        current_task_id,
                        "evidence_collected",
                        "success",
                        f"count={len(paths)} sample={paths[0][:200] if paths else ''}",
                    )
                out_fail: dict = {"error": rpa_err.get("error", "RPA 执行失败")}
                out_fail["target_task_id"] = confirmed_task_id
                out_fail["original_update_task_id"] = confirmed_task_id
                out_fail["confirm_task_id"] = current_task_id or None
                if not isinstance(out_fail.get("parsed_result"), dict):
                    out_fail["parsed_result"] = _confirm_failure_parsed(
                        str(ec),
                        target_task_id=confirmed_task_id,
                        verify_reason=str(ec),
                    )
                if rpa_err.get("_rpa_meta"):
                    out_fail["_rpa_meta"] = rpa_err["_rpa_meta"]
                return out_fail

            result = legacy
            rpa_meta = result.pop("_rpa_meta", None)
            result.pop("rpa_evidence_paths", None)
            if not result:
                log_step(current_task_id, "rpa_execution_failed", "failed", "empty legacy result")
                return {
                    "error": "RPA 返回无效结果",
                    "error_code": "unknown_exception",
                    "target_task_id": confirmed_task_id,
                    "original_update_task_id": confirmed_task_id,
                    "confirm_task_id": current_task_id or None,
                    "parsed_result": _confirm_failure_parsed(
                        "unknown_exception",
                        target_task_id=confirmed_task_id,
                    ),
                }

            now_ts = get_shanghai_now()
            task_record.status = "succeeded"
            task_record.result_summary = format_task_confirmation_result(result)
            task_record.error_message = ""
            task_record.finished_at = now_ts
            task_record.updated_at = now_ts
            db.commit()

            result["confirmed_task_id"] = confirmed_task_id
            result["target_task_id"] = confirmed_task_id
            result["original_update_task_id"] = confirmed_task_id
            result["confirm_task_id"] = current_task_id or None
            pr_ok = result.get("parsed_result")
            if not isinstance(pr_ok, dict):
                pr_ok = {}
            pr_ok.setdefault("confirm_task_id", current_task_id or None)
            pr_ok.setdefault("target_task_id", confirmed_task_id)
            pr_ok.setdefault("original_update_task_id", confirmed_task_id)
            result["parsed_result"] = pr_ok
            if rpa_meta:
                result["_rpa_meta"] = rpa_meta
            log_step(
                current_task_id,
                "rpa_execution_succeeded",
                "success",
                f"evidence_count={rpa_meta.get('evidence_count', 0) if rpa_meta else 0}",
            )
            if rpa_meta and int(rpa_meta.get("evidence_count", 0)) > 0:
                log_step(
                    current_task_id,
                    "evidence_collected",
                    "success",
                    f"count={rpa_meta.get('evidence_count', 0)} dir={rpa_meta.get('evidence_dir', '')}"[:900],
                )
            return result

        if confirm_backend == "api_then_rpa_verify":
            trace_id = (state.get("source_message_id") or "").strip() or current_task_id
            legacy, av_err = run_confirm_update_price_api_then_rpa_verify(
                confirm_task_id=current_task_id,
                trace_id=trace_id,
                sku=sku,
                target_price=target_price,
                platform="woo",
            )
            if av_err:
                ec = av_err.get("error_code") or "api_then_rpa_verify_error"
                paths = av_err.get("evidence_paths") or []
                detail = f"error_code={ec} msg={av_err.get('error', '')}"[:900]
                log_step(current_task_id, "confirm_api_then_rpa_verify_failed", "failed", detail)
                if paths:
                    log_step(
                        current_task_id,
                        "evidence_collected",
                        "success",
                        f"count={len(paths)} sample={paths[0][:200] if paths else ''}",
                    )
                out_av: dict = {"error": av_err.get("error", "api_then_rpa_verify 失败")}
                out_av["target_task_id"] = confirmed_task_id
                out_av["original_update_task_id"] = confirmed_task_id
                out_av["confirm_task_id"] = current_task_id or None
                if not isinstance(out_av.get("parsed_result"), dict):
                    out_av["parsed_result"] = _confirm_failure_parsed(
                        str(ec),
                        target_task_id=confirmed_task_id,
                        verify_reason=str(ec),
                    )
                if av_err.get("_rpa_meta"):
                    out_av["_rpa_meta"] = av_err["_rpa_meta"]
                return out_av

            result = legacy
            rpa_meta = result.pop("_rpa_meta", None)
            result.pop("rpa_evidence_paths", None)
            if not result:
                log_step(current_task_id, "confirm_api_then_rpa_verify_failed", "failed", "empty legacy result")
                return {
                    "error": "api_then_rpa_verify 返回无效结果",
                    "error_code": "unknown_exception",
                    "target_task_id": confirmed_task_id,
                    "original_update_task_id": confirmed_task_id,
                    "confirm_task_id": current_task_id or None,
                    "parsed_result": _confirm_failure_parsed(
                        "unknown_exception",
                        target_task_id=confirmed_task_id,
                    ),
                }

            now_ts = get_shanghai_now()
            task_record.status = "succeeded"
            task_record.result_summary = format_task_confirmation_result(result)
            task_record.error_message = ""
            task_record.finished_at = now_ts
            task_record.updated_at = now_ts
            db.commit()

            result["confirmed_task_id"] = confirmed_task_id
            result["target_task_id"] = confirmed_task_id
            result["original_update_task_id"] = confirmed_task_id
            result["confirm_task_id"] = current_task_id or None
            pr_ok = result.get("parsed_result")
            if not isinstance(pr_ok, dict):
                pr_ok = {}
            pr_ok.setdefault("confirm_task_id", current_task_id or None)
            pr_ok.setdefault("target_task_id", confirmed_task_id)
            pr_ok.setdefault("original_update_task_id", confirmed_task_id)
            result["parsed_result"] = pr_ok
            if rpa_meta:
                result["_rpa_meta"] = rpa_meta
            log_step(
                current_task_id,
                "confirm_api_then_rpa_verify_succeeded",
                "success",
                f"verify_passed={result.get('verify_passed')} evidence_count={rpa_meta.get('evidence_count', 0) if rpa_meta else 0}",
            )
            return result

        # Default: mock repo executor (unchanged)
        result = executor.update_price(sku, target_price)
        if result:
            # Update the original task record to succeeded
            now_ts = get_shanghai_now()
            task_record.status = 'succeeded'
            task_record.result_summary = format_task_confirmation_result(result)
            task_record.error_message = ''
            task_record.finished_at = now_ts
            task_record.updated_at = now_ts
            db.commit()
            
            result['confirmed_task_id'] = confirmed_task_id
            result["target_task_id"] = confirmed_task_id
            result["original_update_task_id"] = confirmed_task_id
            result["confirm_task_id"] = current_task_id or None
            pr_ok = result.get("parsed_result")
            if not isinstance(pr_ok, dict):
                pr_ok = {}
            pr_ok.setdefault("confirm_task_id", current_task_id or None)
            pr_ok.setdefault("target_task_id", confirmed_task_id)
            pr_ok.setdefault("original_update_task_id", confirmed_task_id)
            result["parsed_result"] = pr_ok
            return result
        else:
            return {
                "error": f"SKU {sku} 不存在",
                "error_code": "sku_not_found",
                "target_task_id": confirmed_task_id,
                "original_update_task_id": confirmed_task_id,
                "confirm_task_id": current_task_id or None,
                "parsed_result": _confirm_failure_parsed("sku_not_found", target_task_id=confirmed_task_id),
            }
            
    except Exception as e:
        db.rollback()
        return {
            "error": f"确认执行失败：{str(e)}",
            "error_code": "unknown_exception",
            "target_task_id": confirmed_task_id,
            "original_update_task_id": confirmed_task_id,
            "confirm_task_id": current_task_id or None,
            "parsed_result": _confirm_failure_parsed("unknown_exception", target_task_id=confirmed_task_id),
        }
    finally:
        db.close()


def _load_risk_context_from_steps(db, *, target_task_id: str) -> dict | None:
    try:
        from app.db.models import TaskStep
    except Exception:
        return None
    rows = (
        db.query(TaskStep.detail)
        .filter(TaskStep.task_id == target_task_id, TaskStep.step_code == "risk_context")
        .order_by(TaskStep.created_at.desc())
        .limit(1)
        .all()
    )
    if not rows:
        return None
    raw = rows[0][0] if isinstance(rows[0], tuple) else getattr(rows[0], "detail", "")
    text = (raw or "").strip()
    if not text:
        return None
    try:
        obj = json.loads(text)
    except Exception:
        return {"_risk_context_error": "invalid_json", "_raw": text[:500]}
    if not isinstance(obj, dict):
        return {"_risk_context_error": "invalid_shape", "_raw": text[:200]}
    return obj


def _validate_adjust_inventory_risk_context(ctx: dict | None) -> tuple[bool, str, list[str]]:
    """Return (ok, failure_layer, missing_keys)."""
    if ctx is None:
        return False, "confirm_context_missing", []
    if not isinstance(ctx, dict):
        return False, "confirm_context_missing", []
    err = str(ctx.get("_risk_context_error") or "").strip()
    if err == "invalid_json":
        return False, "confirm_context_invalid_json", []
    if err == "invalid_shape":
        return False, "confirm_context_invalid_shape", []
    required = ("provider_id", "capability", "sku", "delta", "target_inventory")
    missing = [k for k in required if ctx.get(k) in (None, "", [])]
    if missing:
        return False, "confirm_context_incomplete", missing
    if str(ctx.get("capability") or "") != "warehouse.adjust_inventory":
        return False, "confirm_context_incomplete", ["capability"]
    return True, "", []


def _build_minimal_internal_sandbox_app():
    from fastapi import FastAPI
    from app.api.v1 import internal_sandbox

    a = FastAPI()
    a.include_router(internal_sandbox.router, prefix="/api/v1")
    return a


def _confirm_execute_odoo_adjust_inventory(
    db,
    *,
    state: dict,
    current_task_id: str,
    target_task_id: str,
    ctx: dict,
    task_record: TaskRecord,
) -> dict:
    from fastapi.testclient import TestClient

    sku = str(ctx.get("sku") or "").strip().upper()
    delta = int(ctx.get("delta") or 0)
    old_inv = int(ctx.get("old_inventory") or 0)
    target_inv = int(ctx.get("target_inventory") or (old_inv + delta))
    provider_id = str(ctx.get("provider_id") or "odoo")

    if not sku or delta == 0:
        layer = "confirm_context_invalid"
        return {
            "error": f"[{layer}] 风险上下文缺失 sku/delta",
            "error_code": layer,
            "target_task_id": target_task_id,
            "original_update_task_id": target_task_id,
            "confirm_task_id": current_task_id or None,
            "parsed_result": {
                "failure_layer": layer,
                "operation_result": "confirm_blocked_noop",
                "verify_passed": False,
                "verify_reason": layer,
                "old_inventory": old_inv,
                "delta": delta,
                "target_inventory": target_inv,
                "post_inventory": None,
                "target_task_id": target_task_id,
                "original_update_task_id": target_task_id,
                "confirm_task_id": current_task_id or None,
            },
        }

    confirm_exec_backend = str(
        settings.ODOO_ADJUST_INVENTORY_CONFIRM_EXECUTION_BACKEND or "internal_sandbox"
    ).strip().lower()

    log_step(
        current_task_id,
        "controlled_write_started",
        "processing",
        f"provider_id={provider_id} capability=warehouse.adjust_inventory target_task_id={target_task_id} sku={sku} delta={delta} backend={confirm_exec_backend}",
    )

    rpa_vendor = ""
    run_id = ""
    raw_result_path = ""
    evidence_paths: list[str] = []
    page_url = ""
    page_profile = ""
    page_steps: list[str] = []
    page_evidence_count = 0
    page_failure_code = ""
    screenshot_paths: list[str] = []

    if confirm_exec_backend == "yingdao_bridge":
        bridge_payload = {
            "task_id": target_task_id,
            "confirm_task_id": current_task_id,
            "provider_id": provider_id,
            "capability": "warehouse.adjust_inventory",
            # Stable run_id for file-exchange ↔ runtime ↔ DB evidence linkage.
            # Prefer confirm task id so repeated confirms remain idempotent by task id.
            "run_id": str(current_task_id or target_task_id),
            "sku": sku,
            "delta": delta,
            "old_inventory": old_inv,
            "target_inventory": target_inv,
            "environment": str(settings.YINGDAO_BRIDGE_ENVIRONMENT or "local_poc"),
            "force_verify_fail": bool(ctx.get("force_verify_fail", False)),
        }
        try:
            bridge_out = run_yingdao_adjust_inventory(bridge_payload)
        except YingdaoBridgeError as exc:
            layer = str(exc.failure_layer or "bridge_unavailable")
            op = str(exc.operation_result or "write_adjust_inventory_bridge_failed")
            msg = str(exc.verify_reason or f"yingdao_bridge_call_failed:{exc}")
            log_step(current_task_id, "controlled_write_failed", "failed", msg[:900])
            return {
                "error": f"[{layer}] {msg}",
                "error_code": layer,
                "target_task_id": target_task_id,
                "original_update_task_id": target_task_id,
                "confirm_task_id": current_task_id or None,
                "parsed_result": {
                    "failure_layer": layer,
                    "operation_result": op,
                    "verify_passed": False,
                    "verify_reason": msg,
                    "old_inventory": old_inv,
                    "delta": delta,
                    "target_inventory": target_inv,
                    "post_inventory": None,
                    "target_task_id": target_task_id,
                    "original_update_task_id": target_task_id,
                    "confirm_task_id": current_task_id or None,
                    "confirm_backend": "yingdao_bridge",
                    "rpa_vendor": "yingdao",
                    "raw_result_path": "",
                    "evidence_paths": [],
                },
            }
        rpa_vendor = str(bridge_out.get("rpa_vendor") or "yingdao")
        run_id = str(bridge_out.get("run_id") or bridge_payload.get("run_id") or "")
        raw_result_path = str(bridge_out.get("raw_result_path") or "")
        evidence_paths = [str(x) for x in (bridge_out.get("evidence_paths") or [])]
        page_url = str(bridge_out.get("page_url") or "")
        page_profile = str(bridge_out.get("page_profile") or "")
        page_steps = [str(x) for x in (bridge_out.get("page_steps") or [])]
        page_evidence_count = int(bridge_out.get("page_evidence_count") or len(evidence_paths))
        page_failure_code = str(bridge_out.get("page_failure_code") or "")
        screenshot_paths = [str(x) for x in (bridge_out.get("screenshot_paths") or []) if str(x)]
        verify_passed = bool(bridge_out.get("verify_passed", False))
        verify_reason = str(bridge_out.get("verify_reason") or "")
        operation_result = str(bridge_out.get("operation_result") or "")
        failure_layer = str(bridge_out.get("failure_layer") or "")
        post_inv = int(bridge_out.get("post_inventory") or (target_inv if verify_passed else old_inv))
    else:
        with TestClient(_build_minimal_internal_sandbox_app()) as client:
            resp = client.post(
                "/api/v1/internal/sandbox/provider/odoo/inventory/adjust",
                params={"sku": sku, "delta": delta},
            )
            if resp.status_code != 200:
                layer = "provider_upstream_unavailable"
                msg = f"sandbox_adjust_failed status={resp.status_code} body={(resp.text or '')[:200]}"
                log_step(current_task_id, "controlled_write_failed", "failed", msg[:900])
                return {
                    "error": f"[{layer}] {msg}",
                    "error_code": layer,
                    "target_task_id": target_task_id,
                    "original_update_task_id": target_task_id,
                    "confirm_task_id": current_task_id or None,
                    "parsed_result": {
                        "failure_layer": layer,
                        "operation_result": "write_adjust_inventory_failed",
                        "verify_passed": False,
                        "verify_reason": msg,
                        "old_inventory": old_inv,
                        "delta": delta,
                        "target_inventory": target_inv,
                        "post_inventory": None,
                        "target_task_id": target_task_id,
                        "original_update_task_id": target_task_id,
                        "confirm_task_id": current_task_id or None,
                    },
                }

    if confirm_exec_backend != "yingdao_bridge":
        # Post-check via existing readonly client path (internal sandbox).
        post = execute_odoo_query_inventory({"sku": sku, "platform": "odoo"})
        post_inv = int(post.get("inventory") or 0)
        force_verify_fail = bool(ctx.get("force_verify_fail", False))
        verify_passed = bool(post_inv == target_inv) and (not force_verify_fail)
        verify_reason = "ok" if verify_passed else f"post_inventory_mismatch expected={target_inv} got={post_inv}"
        if force_verify_fail:
            verify_reason = f"forced_verify_failure expected={target_inv} got={post_inv}"
        operation_result = "write_adjust_inventory" if verify_passed else "write_adjust_inventory_verify_failed"
        failure_layer = "" if verify_passed else "verify_failed"
    else:
        if not operation_result:
            operation_result = "write_adjust_inventory" if verify_passed else "write_adjust_inventory_verify_failed"
        if not verify_reason:
            verify_reason = "ok" if verify_passed else "bridge_verify_failed"
        if (not failure_layer) and (not verify_passed):
            failure_layer = "verify_failed"

    # Update original target task record as single source of truth for business action outcome.
    # Use an explicit UPDATE to avoid session identity-map surprises in shared-session tests.
    now_ts = get_shanghai_now()
    db.query(TaskRecord).filter(TaskRecord.task_id == target_task_id).update(
        {
            "status": "succeeded" if verify_passed else "failed",
            "error_message": "" if verify_passed else f"[verify_failed] {verify_reason}",
            "finished_at": now_ts,
            "updated_at": now_ts,
        }
    )
    db.commit()

    log_step(
        current_task_id,
        "controlled_write_succeeded",
        "success" if verify_passed else "failed",
        f"verify_passed={verify_passed} verify_reason={verify_reason} post_inventory={post_inv}",
    )

    result = {
        "status": "success" if verify_passed else "failed",
        "platform": "odoo",
        "provider_id": provider_id,
        "capability": "warehouse.adjust_inventory",
        "confirm_backend": "internal_sandbox",
        "rpa_vendor": rpa_vendor,
        "run_id": run_id if confirm_exec_backend == "yingdao_bridge" else "",
        "raw_result_path": raw_result_path,
        "evidence_paths": evidence_paths,
        "page_url": page_url,
        "page_profile": page_profile,
        "page_steps": page_steps,
        "page_evidence_count": page_evidence_count,
        "page_failure_code": page_failure_code,
        "screenshot_paths": screenshot_paths if confirm_exec_backend == "yingdao_bridge" else [],
        "sku": sku,
        "old_inventory": old_inv,
        "delta": delta,
        "target_inventory": target_inv,
        "post_inventory": post_inv,
        "verify_passed": verify_passed,
        "verify_reason": verify_reason,
        "operation_result": operation_result,
        "failure_layer": failure_layer,
        "target_task_id": target_task_id,
        "original_update_task_id": target_task_id,
        "confirm_task_id": current_task_id or None,
    }
    result["confirm_backend"] = "yingdao_bridge" if confirm_exec_backend == "yingdao_bridge" else "internal_sandbox"
    result["parsed_result"] = {
        "failure_layer": result["failure_layer"],
        "operation_result": operation_result,
        "verify_passed": verify_passed,
        "verify_reason": verify_reason,
        "old_inventory": old_inv,
        "delta": delta,
        "target_inventory": target_inv,
        "post_inventory": post_inv,
        "target_task_id": target_task_id,
        "original_update_task_id": target_task_id,
        "confirm_task_id": current_task_id or None,
        "confirm_backend": result["confirm_backend"],
        "rpa_vendor": rpa_vendor,
        "run_id": result.get("run_id") or "",
        "raw_result_path": raw_result_path,
        "evidence_paths": evidence_paths,
        "page_url": page_url,
        "page_profile": page_profile,
        "page_steps": page_steps,
        "page_evidence_count": page_evidence_count,
        "page_failure_code": page_failure_code,
        "screenshot_paths": result.get("screenshot_paths") or [],
    }
    return result


def execute_product_update_price(executor, state: dict, slots: dict) -> dict:
    """
    Execute product.update_price action with confirmation flow.
    
    Args:
        state: Current graph state
        slots: Extracted slots (sku, target_price)
        
    Returns:
        Update result dict
    """
    sku = slots.get('sku')
    target_price = slots.get('target_price')
    task_id = state.get('task_id', '')
    raw_text = state.get('raw_text', '')
    
    if not sku or not target_price:
        return {'error': '缺少必要参数（SKU 或价格）'}
    
    # Check if this is a confirmation message (fallback, should be handled by system.confirm_task)
    confirmation_pattern = r'确认执行\s*(TASK-\d+)'
    confirmation_match = re.match(confirmation_pattern, raw_text, re.IGNORECASE)
    
    if confirmation_match:
        confirmed_task_id = confirmation_match.group(1)
        if confirmed_task_id == task_id:
            # Execute the price update
            result = executor.update_price(sku, target_price)
            if result:
                return result
            else:
                return {'error': f'SKU {sku} 不存在'}
        else:
            return {'error': f'任务号不匹配：期望 {task_id}, 实际 {confirmed_task_id}'}
    
    # First time request - requires confirmation
    # Get current price for display
    product_data = executor.query_sku_status(sku)
    current_price = product_data['price'] if product_data else 0
    
    return {
        'requires_confirmation': True,
        'sku': sku,
        'target_price': target_price,
        'current_price': current_price,
        'task_id': task_id
    }


def format_price_update_confirmation(result: dict) -> str:
    """
    Format price update confirmation message.
    
    Args:
        result: Result dict with requires_confirmation=True
        
    Returns:
        Formatted confirmation text message
    """
    return (
        f"⚠️ 检测到高风险操作：修改价格\n"
        f"SKU: {result.get('sku')}\n"
        f"当前价格：{result.get('current_price', 0)}\n"
        f"目标价格：{result.get('target_price')}\n"
        f"任务号：{result.get('task_id')}\n"
        f"请回复：确认执行 {result.get('task_id')}"
    )


def format_price_update_result(result: dict) -> str:
    """
    Format price update execution result.
    
    Args:
        result: Result dict with status=success
        
    Returns:
        Formatted result text message
    """
    return (
        f"✅ 价格修改成功\n"
        f"SKU: {result.get('sku')}\n"
        f"原价：{result.get('old_price')}\n"
        f"新价格：{result.get('new_price')}\n"
        f"执行结果：{result.get('status')}\n"
        f"平台：{result.get('platform')}"
    )


def format_task_confirmation_result(result: dict) -> str:
    """
    Format task confirmation execution result.
    
    Args:
        result: Result dict with status=success
        
    Returns:
        Formatted result text message
    """
    # P6.1: Odoo adjust_inventory confirmation result
    if result.get("capability") == "warehouse.adjust_inventory" or "old_inventory" in result:
        lines = [
            "✅ 确认执行成功",
            f"SKU: {result.get('sku')}",
            f"写前库存：{result.get('old_inventory')}",
            f"调整量(delta)：{result.get('delta')}",
            f"目标库存：{result.get('target_inventory')}",
            f"写后库存：{result.get('post_inventory')}",
            f"平台：{result.get('platform', 'odoo')}",
        ]
    else:
        lines = [
            "✅ 确认执行成功",
            f"SKU: {result.get('sku')}",
            f"原价：{result.get('old_price')}",
            f"新价格：{result.get('new_price')}",
            f"执行结果：{result.get('status')}",
            f"平台：{result.get('platform')}",
        ]
    if "verify_passed" in result:
        vp = result.get("verify_passed")
        vr = result.get("verify_reason", "")
        lines.append(f"页面核验：{'通过' if vp else '未通过'} ({vr})")
        if result.get("api_price_after_update") is not None:
            lines.append(f"API 回读价：{result.get('api_price_after_update')}")
    return "\n".join(lines)


def execute_odoo_adjust_inventory_prepare(*, task_id: str, slots: dict) -> dict:
    sku = str(slots.get("sku") or "").strip().upper()
    if not sku:
        raise ValueError("SKU is required")
    delta_raw = slots.get("delta")
    target_inventory_raw = slots.get("target_inventory")
    delta = int(delta_raw) if delta_raw is not None else 0

    # Read-before-write to capture old value and compute target.
    #
    # P9-B: when running the real_nonprod_page Yingdao flow, the source-of-truth
    # for the baseline inventory is the nonprod_admin_stub SQLite, not the in-process
    # internal_sandbox defaults.
    old_inv: int
    before: dict
    if str(settings.YINGDAO_BRIDGE_EXECUTION_MODE or "").strip().lower() == "real_nonprod_page":
        try:
            import sqlite3
            from pathlib import Path

            stub_db = (
                Path(__file__).resolve().parents[3]
                / "tools/nonprod_admin_stub/data/nonprod_stub.db"
            )
            if stub_db.exists():
                con = sqlite3.connect(str(stub_db))
                try:
                    row = con.execute(
                        "select inventory from inventory_items where sku=?",
                        (sku,),
                    ).fetchone()
                finally:
                    con.close()
                old_inv = int(row[0]) if row else 0
            else:
                old_inv = 0
        except Exception:
            old_inv = 0
        before = {
            "sku": sku,
            "inventory": old_inv,
            "platform": "odoo",
            "provider_id": "odoo",
            "capability": "warehouse.query_inventory",
            "readiness_status": "ready",
            "endpoint_profile": "real_nonprod_stub_v1",
            "session_injection_mode": "cookie",
            "provider_profile": "odoo",
            "auth_profile": "nonprod_stub",
            "request_adapter": "nonprod_stub_sqlite",
            "response_mapper": "nonprod_stub_html",
            "credential_profile": "nonprod_stub",
        }
    else:
        before = execute_odoo_query_inventory({"sku": sku, "platform": "odoo"})
        old_inv = int(before.get("inventory") or 0)
    if target_inventory_raw is not None:
        target_inv = max(0, int(target_inventory_raw))
        delta = int(target_inv - old_inv)
    else:
        if delta == 0:
            raise ValueError("delta or target_inventory is required")
        target_inv = max(0, int(old_inv + delta))

    ctx = {
        "provider_id": "odoo",
        "capability": "warehouse.adjust_inventory",
        "sku": sku,
        "old_inventory": old_inv,
        "delta": delta,
        "target_inventory": target_inv,
        "target_task_id": task_id,
        "original_update_task_id": task_id,
    }
    # Persist structured confirm context as a TaskStep (single source for confirm; do not parse summary).
    log_step(task_id, "risk_context", "success", json.dumps(ctx, ensure_ascii=False, sort_keys=True))

    # Return shape for result_summary template and observable fields.
    return {
        "platform": "odoo",
        "provider_id": "odoo",
        "capability": "warehouse.adjust_inventory",
        "readiness_status": before.get("readiness_status", "ready"),
        "endpoint_profile": before.get("endpoint_profile", "odoo_product_stock_v1"),
        "session_injection_mode": before.get("session_injection_mode", "header"),
        "provider_profile": before.get("provider_profile", "odoo"),
        "auth_profile": before.get("auth_profile", "odoo_auth_profile"),
        "request_adapter": before.get("request_adapter", "odoo_request_adapter"),
        "response_mapper": before.get("response_mapper", "odoo_mapper"),
        "credential_profile": before.get("credential_profile", "odoo_credential_profile"),
        "sku": sku,
        "old_inventory": old_inv,
        "delta": delta,
        "target_inventory": target_inv,
        "task_id": task_id,
    }


def format_warehouse_adjust_inventory_confirmation(result: dict) -> str:
    return (
        f"⚠️ 检测到高风险操作：调整库存（Odoo）\n"
        f"SKU: {result.get('sku')}\n"
        f"写前库存：{result.get('old_inventory')}\n"
        f"调整量(delta)：{result.get('delta')}\n"
        f"目标库存：{result.get('target_inventory')}\n"
        f"任务号：{result.get('task_id')}\n"
        f"请回复：确认执行 {result.get('task_id')}"
    )
