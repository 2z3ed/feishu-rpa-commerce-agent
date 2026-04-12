"""
Execute Action Node

Executes the identified action based on intent.
"""
import re
from app.core.logging import logger
from app.db.session import SessionLocal
from app.db.models import TaskRecord
from app.core.time import get_shanghai_now
from app.executors import get_product_executor, resolve_execution_mode, resolve_query_platform
from app.clients.woo_readonly_prep import get_woo_rollout_policy
from app.core.config import settings
from app.rpa.confirm_update_price import (
    run_confirm_update_price_api_then_rpa_verify,
    run_confirm_update_price_rpa,
)
from app.utils.task_logger import log_step


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
            state["execution_backend"] = "sandbox_http_client" if execution_mode == "api" else "mock_repo"
            state["selected_backend"] = state["execution_backend"]
            if execution_mode == "api":
                state["client_profile"] = getattr(executor, "get_backend_profile", lambda: "sandbox_http_client")()
                resolved_platform = resolve_query_platform(execution_mode, slots.get("platform"))
                state["platform"] = resolved_platform
                state["response_mapper"] = getattr(executor, "get_mapper_name", lambda p: "sandbox_mapper")(resolved_platform)
                state["provider_profile"] = getattr(executor, "get_provider_profile_name", lambda p: "unknown")(resolved_platform)
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
            state["query_product_data"] = result
            state["result_summary"] = format_product_query_result(result)
            state["status"] = "succeeded"
            state["platform"] = result.get("platform", state.get("platform", "mock"))
            logger.info("Product query executed successfully: sku=%s", slots.get('sku'))
            
        elif intent_code == "system.confirm_task":
            result = execute_task_confirmation(executor, state, slots)
            if result.get("status") == "success":
                rpa_meta = result.pop("_rpa_meta", None)
                result.pop("rpa_evidence_paths", None)
                state["result_summary"] = format_task_confirmation_result(result)
                state["status"] = "succeeded"
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
                    state["execution_backend"] = "mock_repo"
                    state["client_profile"] = "mock_repo"
                if "verify_passed" in result:
                    state["verify_passed"] = result.get("verify_passed")
                    state["verify_reason"] = str(result.get("verify_reason", ""))
                    if result.get("api_price_after_update") is not None:
                        state["api_price_after_update"] = result.get("api_price_after_update")
                state["response_mapper"] = "none"
                state["request_adapter"] = "none"
                state["auth_profile"] = "none"
                state["provider_profile"] = "none"
                state["credential_profile"] = "none"
                logger.info("Task confirmed and executed successfully: task_id=%s", slots.get('task_id'))
            else:
                rpa_meta_fail = result.pop("_rpa_meta", None)
                err_msg = result.get("error", "确认失败")
                state["error_message"] = err_msg
                state["status"] = "failed"
                state["result_summary"] = f"确认失败：{err_msg}"
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
    
    if not confirmed_task_id:
        return {'error': '缺少任务号'}
    
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
            return {'error': f'任务 {confirmed_task_id} 不存在'}
        
        # Check if task is in awaiting_confirmation status
        if task_record.status != 'awaiting_confirmation':
            return {'error': f'任务 {confirmed_task_id} 状态为 {task_record.status}，无需确认'}
        
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
            return {'error': '无法从原任务中提取 SKU 和价格信息'}
        
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
                if rpa_err.get("_rpa_meta"):
                    out_fail["_rpa_meta"] = rpa_err["_rpa_meta"]
                return out_fail

            result = legacy
            rpa_meta = result.pop("_rpa_meta", None)
            result.pop("rpa_evidence_paths", None)
            if not result:
                log_step(current_task_id, "rpa_execution_failed", "failed", "empty legacy result")
                return {"error": "RPA 返回无效结果"}

            now_ts = get_shanghai_now()
            task_record.status = "succeeded"
            task_record.result_summary = format_task_confirmation_result(result)
            task_record.error_message = ""
            task_record.finished_at = now_ts
            task_record.updated_at = now_ts
            db.commit()

            result["confirmed_task_id"] = confirmed_task_id
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
                if av_err.get("_rpa_meta"):
                    out_av["_rpa_meta"] = av_err["_rpa_meta"]
                return out_av

            result = legacy
            rpa_meta = result.pop("_rpa_meta", None)
            result.pop("rpa_evidence_paths", None)
            if not result:
                log_step(current_task_id, "confirm_api_then_rpa_verify_failed", "failed", "empty legacy result")
                return {"error": "api_then_rpa_verify 返回无效结果"}

            now_ts = get_shanghai_now()
            task_record.status = "succeeded"
            task_record.result_summary = format_task_confirmation_result(result)
            task_record.error_message = ""
            task_record.finished_at = now_ts
            task_record.updated_at = now_ts
            db.commit()

            result["confirmed_task_id"] = confirmed_task_id
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
            return result
        else:
            return {'error': f'SKU {sku} 不存在'}
            
    except Exception as e:
        db.rollback()
        return {'error': f'确认执行失败：{str(e)}'}
    finally:
        db.close()


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
