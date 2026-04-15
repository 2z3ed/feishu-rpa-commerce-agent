"""
Execute Action Node

Executes the identified action based on intent.
"""
import json
import re
from app.core.logging import logger
from app.db.session import SessionLocal
from app.db.models import TaskRecord
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
from app.utils.task_logger import log_step


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
        state["error_message"] = "Unknown intent"
        state["status"] = "failed"
        state["result_summary"] = "未识别到已知命令，请尝试其他表述方式"
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
                display_err = _strip_error_prefix(err_msg)
                state["error_message"] = f"[{failure_layer}] {display_err}" if display_err else f"[{failure_layer}]"
                state["status"] = "failed"
                state["result_summary"] = f"确认失败：{state['error_message']}"
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
            if not (isinstance(risk_ctx, dict) and risk_ctx.get("capability") == "warehouse.adjust_inventory"):
                layer = "confirm_context_missing"
                return {
                    "error": f"[{layer}] 目标任务缺少 risk_context，禁止回退到文案解析",
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
                        "verify_reason": layer,
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
                ctx=risk_ctx,
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
        return None
    return obj if isinstance(obj, dict) else None


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

    log_step(
        current_task_id,
        "controlled_write_started",
        "processing",
        f"provider_id={provider_id} capability=warehouse.adjust_inventory target_task_id={target_task_id} sku={sku} delta={delta}",
    )

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

    # Post-check via existing readonly client path (internal sandbox).
    post = execute_odoo_query_inventory({"sku": sku, "platform": "odoo"})
    post_inv = int(post.get("inventory") or 0)
    verify_passed = bool(post_inv == target_inv)
    verify_reason = "ok" if verify_passed else f"post_inventory_mismatch expected={target_inv} got={post_inv}"
    operation_result = "write_adjust_inventory" if verify_passed else "write_adjust_inventory_verify_failed"

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
        "sku": sku,
        "old_inventory": old_inv,
        "delta": delta,
        "target_inventory": target_inv,
        "post_inventory": post_inv,
        "verify_passed": verify_passed,
        "verify_reason": verify_reason,
        "operation_result": operation_result,
        "failure_layer": "" if verify_passed else "verify_failed",
        "target_task_id": target_task_id,
        "original_update_task_id": target_task_id,
        "confirm_task_id": current_task_id or None,
    }
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
        "confirm_backend": "internal_sandbox",
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
    delta = int(slots.get("delta") or 0)
    if delta == 0:
        raise ValueError("delta is required")

    # Read-before-write (readonly chain) to capture old value and compute target.
    before = execute_odoo_query_inventory({"sku": sku, "platform": "odoo"})
    old_inv = int(before.get("inventory") or 0)
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
