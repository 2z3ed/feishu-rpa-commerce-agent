import time
import logging
import traceback

from app.workers.celery_app import celery_app
from app.core.constants import TaskStatus
from app.core.logging import logger
from app.db.session import SessionLocal
from app.db.models import TaskRecord
from app.graph.builder import graph as lang_graph
from app.services.feishu.client import FeishuClient
from app.services.feishu.bitable_write import try_write_bitable_ledger
from app.utils.task_logger import log_step
from app.core.time import get_shanghai_now


_ACTION_EXECUTED_REQUIRED_FIELDS: tuple[str, ...] = (
    "execution_mode",
    "provider_id",
    "capability",
    "readiness_status",
    "endpoint_profile",
    "session_injection_mode",
)


def _normalize_detail_value(key: str, value) -> str:
    v = "" if value is None else str(value)
    v = v.strip()
    # Keep values single-line and easy to parse.
    v = v.replace("\n", "\\n").replace("\r", "\\r")
    if not v or v.lower() in {"none", "null"}:
        # For required fields, never emit empty/none. Use explicit unknown placeholder.
        if key in _ACTION_EXECUTED_REQUIRED_FIELDS:
            return "unknown"
        return ""
    return v


def build_action_executed_detail(fields: dict) -> str:
    """Stable, parseable KV detail string for action_executed step.

    - Required fields always present and never empty/none.
    - Key order is stable (required keys first, then the rest sorted).
    """
    safe: dict[str, str] = {}
    for k, v in (fields or {}).items():
        if not k:
            continue
        key = str(k).strip()
        if not key:
            continue
        safe[key] = _normalize_detail_value(key, v)

    for req in _ACTION_EXECUTED_REQUIRED_FIELDS:
        safe.setdefault(req, "unknown")
        if not safe[req] or safe[req].lower() in {"none", "null"}:
            safe[req] = "unknown"

    ordered_keys = [*list(_ACTION_EXECUTED_REQUIRED_FIELDS)]
    ordered_keys.extend(sorted(k for k in safe.keys() if k not in _ACTION_EXECUTED_REQUIRED_FIELDS))

    parts: list[str] = []
    for k in ordered_keys:
        parts.append(f"{k}={safe.get(k, '')}")
    return ", ".join(parts)


@celery_app.task(bind=True, name="ingress.process_message")
def process_ingress_message(self, task_id: str, intent_text: str, user_open_id: str | None = None, 
                           source_message_id: str = "", chat_id: str = ""):
    logger.info("=== CELERY TASK RECEIVED === task_id=%s, intent_text=%s, chat_id=%s", 
                task_id, intent_text[:50] if intent_text else "", chat_id)

    db = SessionLocal()
    task_record = None
    try:
        task_record = db.query(TaskRecord).filter(TaskRecord.task_id == task_id).first()
        if not task_record:
            logger.error("Task record not found: task_id=%s", task_id)
            return {"status": "error", "message": "Task record not found"}

        logger.info("=== TASK RECORD LOADED === task_id=%s, status=%s, intent_text=%s", 
                    task_id, task_record.status, task_record.intent_text[:50] if task_record.intent_text else "")
        
        now_ts = get_shanghai_now()
        task_record.status = TaskStatus.PROCESSING.value
        task_record.started_at = now_ts
        task_record.updated_at = now_ts
        db.commit()

        logger.info("=== TASK STATUS UPDATED === task_id=%s, status=processing", task_id)
        
        # Log graph started step
        log_step(task_id, "graph_started", "processing", "")

        # Execute LangGraph workflow
        initial_state = {
            "task_id": task_id,
            "source_message_id": source_message_id,
            "source_chat_id": chat_id,
            "user_open_id": user_open_id or "",
            "raw_text": intent_text or "",
        }
        
        logger.info("=== LANGGRAPH EXECUTION START === task_id=%s, initial_state=%s", task_id, initial_state)
        result = lang_graph.invoke(initial_state)
        logger.info("=== LANGGRAPH EXECUTION END === task_id=%s, result=%s", task_id, result)
        
        # Log intent resolved and action executed steps (will be updated in finalize_result)
        intent_code = result.get("intent_code", "unknown")
        execution_mode = result.get("execution_mode", "mock")
        platform = result.get("platform", "mock")
        execution_backend = result.get("execution_backend", "unknown")
        client_profile = result.get("client_profile", "unknown")
        response_mapper = result.get("response_mapper", "none")
        request_adapter = result.get("request_adapter", "none")
        auth_profile = result.get("auth_profile", "none")
        provider_profile = result.get("provider_profile", "none")
        credential_profile = result.get("credential_profile", "none")
        production_config_ready = result.get("production_config_ready", "n/a")
        dry_run_enabled = result.get("dry_run_enabled", "false")
        selected_backend = result.get("selected_backend", execution_backend)
        backend_selection_reason = result.get("backend_selection_reason", "unknown")
        fallback_enabled = result.get("fallback_enabled", "false")
        fallback_applied = result.get("fallback_applied", "false")
        fallback_target = result.get("fallback_target", "none")
        final_backend = result.get("final_backend", execution_backend)
        dry_run_failure = result.get("dry_run_failure", "none")
        recommended_strategy = result.get("recommended_strategy", "n/a")
        environment_ready = result.get("environment_ready", "unknown")
        live_probe_enabled = result.get("live_probe_enabled", "false")
        provider_id = result.get("provider_id", "unknown")
        capability = result.get("capability", "unknown")
        readiness_status = result.get("readiness_status", "unknown")
        endpoint_profile = result.get("endpoint_profile", "none")
        session_injection_mode = result.get("session_injection_mode", "none")
        evidence_count = result.get("evidence_count", 0)
        rpa_runner = result.get("rpa_runner", "none")
        verify_mode = result.get("verify_mode", "none")
        pr = result.get("parsed_result") or {}
        if not isinstance(pr, dict):
            pr = {}
        verify_passed = result.get("verify_passed", pr.get("verify_passed", None))
        verify_reason = result.get("verify_reason", pr.get("verify_reason", ""))
        operation_result = result.get("operation_result", pr.get("operation_result", ""))
        failure_layer = pr.get("failure_layer", "")
        old_price = pr.get("old_price", None)
        new_price = pr.get("new_price", None)
        post_save_price = pr.get("post_save_price", None)
        # P6.1: Odoo adjust_inventory audit fields (optional, only present on that flow)
        old_inventory = pr.get("old_inventory", None)
        delta = pr.get("delta", None)
        target_inventory = pr.get("target_inventory", None)
        post_inventory = pr.get("post_inventory", None)
        target_task_id = pr.get("target_task_id", "")
        original_update_task_id = pr.get("original_update_task_id", "")
        confirm_task_id = pr.get("confirm_task_id", "")
        log_step(task_id, "intent_resolved", "success", f"intent={intent_code}")
        detail = build_action_executed_detail(
            {
                "intent": intent_code,
                "execution_mode": execution_mode,
                "platform": platform,
                "backend": execution_backend,
                "client": client_profile,
                "mapper": response_mapper,
                "request_adapter": request_adapter,
                "auth_profile": auth_profile,
                "provider_profile": provider_profile,
                "credential_profile": credential_profile,
                "production_config_ready": production_config_ready,
                "dry_run_enabled": dry_run_enabled,
                "selected_backend": selected_backend,
                "backend_selection_reason": backend_selection_reason,
                "fallback_enabled": fallback_enabled,
                "fallback_applied": fallback_applied,
                "fallback_target": fallback_target,
                "final_backend": final_backend,
                "dry_run_failure": dry_run_failure,
                "recommended_strategy": recommended_strategy,
                "environment_ready": environment_ready,
                "live_probe_enabled": live_probe_enabled,
                "provider_id": provider_id,
                "capability": capability,
                "readiness_status": readiness_status,
                "endpoint_profile": endpoint_profile,
                "session_injection_mode": session_injection_mode,
                "evidence_count": evidence_count,
                "rpa_runner": rpa_runner,
                "verify_mode": verify_mode,
                "verify_passed": verify_passed,
                "verify_reason": verify_reason,
                "operation_result": operation_result,
                "failure_layer": failure_layer,
                "old_price": old_price,
                "new_price": new_price,
                "post_save_price": post_save_price,
                "old_inventory": old_inventory,
                "delta": delta,
                "target_inventory": target_inventory,
                "post_inventory": post_inventory,
                "target_task_id": target_task_id,
                "original_update_task_id": original_update_task_id,
                "confirm_task_id": confirm_task_id,
            }
        )
        log_step(
            task_id,
            "action_executed",
            "success",
            detail,
        )
        
        # Refresh task record to get updated values
        db.refresh(task_record)
        logger.info("=== TASK RECORD AFTER LANGGRAPH === task_id=%s, status=%s, intent_text=%s, result_summary=%s", 
                    task_id, task_record.status, 
                    task_record.intent_text[:50] if task_record.intent_text else "",
                    task_record.result_summary[:100] if task_record.result_summary else "")
        
        # Send result back to Feishu using reply to the original message
        if result and source_message_id:
            try:
                client = FeishuClient()
                result_text = result.get("result_summary", "任务执行完成")
                logger.info("=== SENDING FEISHU RESULT MESSAGE === message_id=%s, result_text=%s", 
                           source_message_id, result_text[:100])
                success = client.send_text_reply(source_message_id, result_text)
                if success:
                    logger.info("=== FEISHU RESULT MESSAGE SENT === task_id=%s, message_id=%s", task_id, source_message_id)
                    log_step(task_id, "result_replied", "success", f"message_id={source_message_id}")
                else:
                    logger.error("=== FEISHU RESULT MESSAGE FAILED === task_id=%s, message_id=%s, code=%s, msg=%s", 
                                task_id, source_message_id, "unknown", "send_text_reply returned False")
                    log_step(task_id, "result_replied", "failed", f"message_id={source_message_id}, code=unknown")
            except Exception as e:
                logger.error("=== FEISHU RESULT MESSAGE FAILED === task_id=%s, message_id=%s, error=%s, traceback=%s", 
                            task_id, source_message_id, str(e), traceback.format_exc())

        # Bitable append ledger after IM reply (failures do not affect user-visible result)
        try:
            db.refresh(task_record)
            try_write_bitable_ledger(
                task_id=task_id,
                graph_result=result,
                task_record=task_record,
                db=db,
            )
        except Exception as bitable_exc:
            logger.warning(
                "Bitable write wrapper failed (ignored): task_id=%s err=%s",
                task_id,
                bitable_exc,
            )

        logger.info("=== CELERY TASK COMPLETED === task_id=%s, status=%s", task_id, task_record.status)
        return {"status": "success", "task_id": task_id, "result": task_record.result_summary}

    except Exception as e:
        logger.error("=== CELERY TASK FAILED === task_id=%s, error=%s, traceback=%s", 
                     task_id, str(e), traceback.format_exc())
        if task_record:
            now_ts = get_shanghai_now()
            task_record.status = TaskStatus.FAILED.value
            task_record.error_message = str(e)
            task_record.finished_at = now_ts
            task_record.updated_at = now_ts
            db.commit()
        log_step(task_id, "failed", "failed", str(e)[:200])
        raise
    finally:
        db.close()