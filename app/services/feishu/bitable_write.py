"""
One-way append to Feishu Bitable (task ledger).

v1: product.query_sku_status success.
v2: append-only ledger — also update_price (awaiting + rare success), confirm_task success,
    and a follow-up row for the original task when confirm completes.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

import requests
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import logger
from app.core.time import format_shanghai_dt, get_shanghai_now
from app.db.models import TaskRecord, TaskStep
from app.executors import get_product_executor
from app.utils.task_logger import log_step

# Ledger columns (add matching fields in Bitable; v1 columns retained, v2 adds the rest)
BITABLE_FIELD_TASK_ID = "task_id"
BITABLE_FIELD_TARGET_TASK_ID = "target_task_id"
BITABLE_FIELD_INTENT_CODE = "intent_code"
BITABLE_FIELD_TASK_TYPE = "task_type"
BITABLE_FIELD_INTENT_TEXT = "intent_text"
BITABLE_FIELD_STATUS = "status"
BITABLE_FIELD_SKU = "sku"
BITABLE_FIELD_PRODUCT_NAME = "product_name"
BITABLE_FIELD_INVENTORY = "inventory"
BITABLE_FIELD_PRICE = "price"
BITABLE_FIELD_PLATFORM = "platform"
BITABLE_FIELD_REQUIRES_CONFIRMATION = "requires_confirmation"
BITABLE_FIELD_CONFIRMATION_STATUS = "confirmation_status"
BITABLE_FIELD_CREATED_AT = "created_at"
BITABLE_FIELD_UPDATED_AT = "updated_at"
BITABLE_FIELD_RESULT_SUMMARY = "result_summary"
BITABLE_FIELD_ERROR_MESSAGE = "error_message"

BITABLE_LEDGER_STRATEGY = "append"

# P9-C: RPA execution evidence ledger (fixed schema).
BITABLE_FIELD_LEDGER_TYPE_CN = "台账类型"
BITABLE_FIELD_RUN_ID = "run_id"
BITABLE_FIELD_PROVIDER_ID = "provider_id"
BITABLE_FIELD_CAPABILITY = "capability"
BITABLE_FIELD_EXECUTION_MODE = "execution_mode"
BITABLE_FIELD_RUNTIME_STATE = "runtime_state"
BITABLE_FIELD_OPERATION_RESULT = "operation_result"
BITABLE_FIELD_OLD_INVENTORY = "old_inventory"
BITABLE_FIELD_TARGET_INVENTORY = "target_inventory"
BITABLE_FIELD_NEW_INVENTORY = "new_inventory"
BITABLE_FIELD_VERIFY_PASSED = "verify_passed"
BITABLE_FIELD_VERIFY_REASON = "verify_reason"
BITABLE_FIELD_PAGE_FAILURE_CODE = "page_failure_code"
BITABLE_FIELD_FAILURE_LAYER = "failure_layer"
BITABLE_FIELD_PAGE_STEPS = "page_steps"
BITABLE_FIELD_PAGE_EVIDENCE_COUNT = "page_evidence_count"
BITABLE_FIELD_SCREENSHOT_PATHS = "screenshot_paths"
BITABLE_FIELD_LATEST_EVIDENCE_PATH = "latest_evidence_path"
BITABLE_FIELD_FINISHED_AT = "finished_at"


def _mask_id(value: str, head: int = 4, tail: int = 4) -> str:
    v = (value or "").strip()
    if not v:
        return "(empty)"
    if len(v) <= head + tail + 1:
        return f"len={len(v)}"
    return f"{v[:head]}...{v[-tail:]} len={len(v)}"


def _format_bitable_api_failure(task_id: str, app_token: str, table_id: str, response) -> str:
    parts = [
        f"code={response.code}",
        f"msg={getattr(response, 'msg', '') or ''}",
        f"app_token={_mask_id(app_token)}",
        f"table_id={_mask_id(table_id)}",
    ]
    hint = "api_error"
    err = getattr(response, "error", None)
    if err is not None:
        if getattr(err, "permission_violations", None):
            hint = "likely_permission_or_object_scope"
            for pv in (err.permission_violations or [])[:2]:
                ptype = getattr(pv, "type", "") or ""
                subj = getattr(pv, "subject", "") or ""
                desc = (getattr(pv, "description", "") or "")[:120]
                parts.append(f"perm_violation={ptype}:{subj}:{desc}")
        elif getattr(err, "troubleshooter", None):
            hint = "see_troubleshooter"
        ts = getattr(err, "troubleshooter", None)
        if ts:
            parts.append(f"troubleshooter={str(ts)[:180]}")
    parts.append(f"hint={hint}")
    log_id = response.get_log_id() if hasattr(response, "get_log_id") else None
    if log_id:
        parts.append(f"log_id={log_id}")
    detail = " | ".join(parts)
    logger.warning("Bitable create API error: task_id=%s %s", task_id, detail[:800])
    return detail[:500]


def check_bitable_readiness() -> dict[str, Any]:
    enabled = bool(settings.ENABLE_FEISHU_BITABLE_WRITE)
    app_token = (settings.FEISHU_BITABLE_APP_TOKEN or "").strip()
    table_id = (settings.FEISHU_BITABLE_TABLE_ID or "").strip()
    missing: list[str] = []
    if not app_token:
        missing.append("FEISHU_BITABLE_APP_TOKEN")
    if not table_id:
        missing.append("FEISHU_BITABLE_TABLE_ID")
    config_ready = len(missing) == 0
    write_allowed = enabled and config_ready
    if not enabled:
        reason = "bitable_write_disabled"
    elif not config_ready:
        reason = f"config_incomplete:{','.join(missing)}"
    else:
        reason = "ready"
    return {
        "bitable_write_enabled": enabled,
        "bitable_config_ready": config_ready,
        "bitable_write_allowed": write_allowed,
        "bitable_reason": reason,
        "bitable_missing": missing,
        "bitable_ledger_strategy": BITABLE_LEDGER_STRATEGY,
    }


def _fmt_dt(val: Any) -> str:
    if val is None:
        return ""
    return format_shanghai_dt(val)


def _to_bitable_datetime_ms(val: Any) -> int:
    dt_val = val
    if dt_val is None:
        dt_val = get_shanghai_now()
    if isinstance(dt_val, datetime):
        return int(dt_val.timestamp() * 1000)
    return int(get_shanghai_now().timestamp() * 1000)


def _to_bool(val: Any) -> bool:
    if isinstance(val, bool):
        return val
    s = str(val or "").strip().lower()
    return s in {"1", "true", "yes", "y", "on"}


def _to_int(val: Any, default: int = 0) -> int:
    try:
        if val is None or str(val).strip() == "":
            return default
        return int(float(str(val)))
    except Exception:
        return default


def _parse_action_detail_kv(detail: str) -> dict[str, str]:
    data: dict[str, str] = {}
    text = (detail or "").strip()
    if not text:
        return data
    for part in text.split(","):
        item = part.strip()
        if "=" not in item:
            continue
        k, v = item.split("=", 1)
        key = k.strip()
        if not key:
            continue
        data[key] = v.strip()
    return data


def _latest_step_detail(db: Session, task_id: str, step_code: str) -> str:
    row = (
        db.query(TaskStep.detail)
        .filter(TaskStep.task_id == task_id, TaskStep.step_code == step_code)
        .order_by(TaskStep.created_at.desc())
        .first()
    )
    if not row:
        return ""
    if isinstance(row, tuple):
        return str(row[0] or "")
    return str(getattr(row, "detail", "") or "")


def _base_ledger_fields(task_record: TaskRecord) -> dict[str, Any]:
    tt = getattr(task_record, "target_task_id", None) or ""
    return {
        BITABLE_FIELD_TASK_ID: task_record.task_id,
        BITABLE_FIELD_TARGET_TASK_ID: str(tt),
        BITABLE_FIELD_TASK_TYPE: str(getattr(task_record, "task_type", None) or "") or "ingress",
        BITABLE_FIELD_INTENT_TEXT: (task_record.intent_text or "")[:2000],
        BITABLE_FIELD_STATUS: str(task_record.status or ""),
        BITABLE_FIELD_CREATED_AT: _fmt_dt(getattr(task_record, "created_at", None)) or format_shanghai_dt(),
        BITABLE_FIELD_UPDATED_AT: _fmt_dt(getattr(task_record, "updated_at", None)) or format_shanghai_dt(),
        BITABLE_FIELD_RESULT_SUMMARY: (task_record.result_summary or "")[:2000],
        BITABLE_FIELD_ERROR_MESSAGE: (task_record.error_message or "")[:2000],
    }


def _build_ledger_query_success(
    task_record: TaskRecord, graph_result: dict[str, Any], product_data: dict[str, Any]
) -> dict[str, Any]:
    f = _base_ledger_fields(task_record)
    f.update(
        {
            BITABLE_FIELD_INTENT_CODE: "product.query_sku_status",
            BITABLE_FIELD_SKU: str(product_data.get("sku", "")),
            BITABLE_FIELD_PRODUCT_NAME: str(product_data.get("product_name", "")),
            BITABLE_FIELD_INVENTORY: str(product_data.get("inventory", "")),
            BITABLE_FIELD_PRICE: str(product_data.get("price", "")),
            BITABLE_FIELD_PLATFORM: str(product_data.get("platform", "")),
            BITABLE_FIELD_REQUIRES_CONFIRMATION: "false",
            BITABLE_FIELD_CONFIRMATION_STATUS: "none",
        }
    )
    if graph_result.get("result_summary"):
        f[BITABLE_FIELD_RESULT_SUMMARY] = str(graph_result["result_summary"])[:2000]
    return f


def _mock_product_snapshot(sku: str) -> dict[str, str]:
    if not sku:
        return {"product_name": "", "inventory": "", "price": ""}
    try:
        ex = get_product_executor("mock")
        pd = ex.query_sku_status(sku, "mock")
        if not pd:
            return {"product_name": "", "inventory": "", "price": ""}
        return {
            "product_name": str(pd.get("product_name", "")),
            "inventory": str(pd.get("inventory", "")),
            "price": str(pd.get("price", "")),
        }
    except Exception:
        return {"product_name": "", "inventory": "", "price": ""}


def _build_ledger_update_price_awaiting(task_record: TaskRecord, graph_result: dict[str, Any]) -> dict[str, Any]:
    slots = graph_result.get("slots") or {}
    sku = str(slots.get("sku") or "")
    target_price = slots.get("target_price")
    snap = _mock_product_snapshot(sku)
    f = _base_ledger_fields(task_record)
    f.update(
        {
            BITABLE_FIELD_INTENT_CODE: "product.update_price",
            BITABLE_FIELD_SKU: sku,
            BITABLE_FIELD_PRODUCT_NAME: snap["product_name"],
            BITABLE_FIELD_INVENTORY: snap["inventory"],
            BITABLE_FIELD_PRICE: str(target_price) if target_price is not None else "",
            BITABLE_FIELD_PLATFORM: "mock",
            BITABLE_FIELD_REQUIRES_CONFIRMATION: "true",
            BITABLE_FIELD_CONFIRMATION_STATUS: "awaiting_user",
        }
    )
    return f


def _build_ledger_update_price_succeeded(task_record: TaskRecord, graph_result: dict[str, Any]) -> dict[str, Any]:
    slots = graph_result.get("slots") or {}
    sku = str(slots.get("sku") or "")
    snap = _mock_product_snapshot(sku)
    f = _base_ledger_fields(task_record)
    f.update(
        {
            BITABLE_FIELD_INTENT_CODE: "product.update_price",
            BITABLE_FIELD_SKU: sku,
            BITABLE_FIELD_PRODUCT_NAME: snap["product_name"],
            BITABLE_FIELD_INVENTORY: snap["inventory"],
            BITABLE_FIELD_PRICE: snap["price"],
            BITABLE_FIELD_PLATFORM: "mock",
            BITABLE_FIELD_REQUIRES_CONFIRMATION: "false",
            BITABLE_FIELD_CONFIRMATION_STATUS: "none",
        }
    )
    return f


def _build_ledger_confirm_task(task_record: TaskRecord, graph_result: dict[str, Any]) -> dict[str, Any]:
    f = _base_ledger_fields(task_record)
    f.update(
        {
            BITABLE_FIELD_INTENT_CODE: "system.confirm_task",
            BITABLE_FIELD_SKU: "",
            BITABLE_FIELD_PRODUCT_NAME: "",
            BITABLE_FIELD_INVENTORY: "",
            BITABLE_FIELD_PRICE: "",
            BITABLE_FIELD_PLATFORM: "",
            BITABLE_FIELD_REQUIRES_CONFIRMATION: "false",
            BITABLE_FIELD_CONFIRMATION_STATUS: "confirmation_message_succeeded",
        }
    )
    if graph_result.get("result_summary"):
        f[BITABLE_FIELD_RESULT_SUMMARY] = str(graph_result["result_summary"])[:2000]
    return f


def _build_ledger_original_after_confirm(original: TaskRecord, graph_result: dict[str, Any]) -> dict[str, Any]:
    f = _base_ledger_fields(original)
    f[BITABLE_FIELD_INTENT_CODE] = "product.update_price"
    f[BITABLE_FIELD_TARGET_TASK_ID] = ""
    f[BITABLE_FIELD_REQUIRES_CONFIRMATION] = "false"
    f[BITABLE_FIELD_CONFIRMATION_STATUS] = "original_completed_via_confirm"
    return f


def _build_rpa_success_evidence_fields(
    task_record: TaskRecord,
    graph_result: dict[str, Any],
    db: Session,
) -> dict[str, Any]:
    pr = graph_result.get("parsed_result") if isinstance(graph_result.get("parsed_result"), dict) else {}
    action_kv = _parse_action_detail_kv(_latest_step_detail(db, task_record.task_id, "action_executed"))

    screenshots = pr.get("screenshot_paths")
    if isinstance(screenshots, list):
        screenshot_paths = [str(x) for x in screenshots if str(x).strip()]
    else:
        screenshot_paths = [x for x in str(action_kv.get("screenshot_paths", "")).split("|") if x]
    page_steps = pr.get("page_steps")
    if isinstance(page_steps, list):
        page_steps_text = ",".join([str(x).strip() for x in page_steps if str(x).strip()])
    else:
        page_steps_text = str(action_kv.get("page_steps", "")).replace("|", ",")

    run_id = str(pr.get("run_id") or action_kv.get("run_id") or task_record.task_id)
    verify_passed = _to_bool(pr.get("verify_passed", action_kv.get("verify_passed", False)))
    verify_reason = str(pr.get("verify_reason") or action_kv.get("verify_reason") or "")
    old_inventory = _to_int(pr.get("old_inventory", action_kv.get("old_inventory")))
    target_inventory = _to_int(pr.get("target_inventory", action_kv.get("target_inventory")))
    new_inventory = _to_int(pr.get("post_inventory", action_kv.get("post_inventory")))
    latest_evidence_path = str(pr.get("raw_result_path") or action_kv.get("raw_result_path") or "")
    result_summary = str(graph_result.get("result_summary") or task_record.result_summary or "")

    return {
        BITABLE_FIELD_LEDGER_TYPE_CN: "rpa_runtime_success",
        BITABLE_FIELD_TASK_ID: task_record.task_id,
        BITABLE_FIELD_TARGET_TASK_ID: str(getattr(task_record, "target_task_id", None) or pr.get("target_task_id") or ""),
        BITABLE_FIELD_RUN_ID: run_id,
        BITABLE_FIELD_PROVIDER_ID: str(pr.get("provider_id") or "yingdao_local"),
        BITABLE_FIELD_CAPABILITY: str(graph_result.get("capability") or "warehouse.adjust_inventory"),
        BITABLE_FIELD_EXECUTION_MODE: "rpa",
        BITABLE_FIELD_RUNTIME_STATE: "done",
        BITABLE_FIELD_OPERATION_RESULT: str(pr.get("operation_result") or action_kv.get("operation_result") or ""),
        BITABLE_FIELD_SKU: str(graph_result.get("slots", {}).get("sku") or pr.get("sku") or ""),
        BITABLE_FIELD_OLD_INVENTORY: old_inventory,
        BITABLE_FIELD_TARGET_INVENTORY: target_inventory,
        BITABLE_FIELD_NEW_INVENTORY: new_inventory,
        BITABLE_FIELD_VERIFY_PASSED: verify_passed,
        BITABLE_FIELD_VERIFY_REASON: verify_reason,
        BITABLE_FIELD_PAGE_FAILURE_CODE: str(pr.get("page_failure_code") or action_kv.get("page_failure_code") or ""),
        BITABLE_FIELD_FAILURE_LAYER: str(pr.get("failure_layer") or action_kv.get("failure_layer") or ""),
        BITABLE_FIELD_PAGE_STEPS: page_steps_text,
        BITABLE_FIELD_PAGE_EVIDENCE_COUNT: _to_int(pr.get("page_evidence_count", action_kv.get("page_evidence_count", 0))),
        BITABLE_FIELD_SCREENSHOT_PATHS: "|".join(screenshot_paths),
        BITABLE_FIELD_LATEST_EVIDENCE_PATH: latest_evidence_path,
        BITABLE_FIELD_RESULT_SUMMARY: result_summary[:2000],
        BITABLE_FIELD_CREATED_AT: _to_bitable_datetime_ms(getattr(task_record, "created_at", None)),
        BITABLE_FIELD_FINISHED_AT: _to_bitable_datetime_ms(
            getattr(task_record, "finished_at", None) or getattr(task_record, "updated_at", None)
        ),
    }


def _bitable_append_row(*, step_task_id: str, fields: dict[str, Any], kind: str, table_id_override: str = "") -> None:
    """Single create; logs bitable_write_* on step_task_id with kind + append in detail."""
    log_step(
        step_task_id,
        "bitable_write_started",
        "processing",
        f"kind={kind} strategy={BITABLE_LEDGER_STRATEGY}",
    )
    try:
        app_token = settings.FEISHU_BITABLE_APP_TOKEN.strip()
        table_id = (table_id_override or settings.FEISHU_BITABLE_TABLE_ID).strip()

        logger.info(
            "Bitable append: step_task_id=%s kind=%s app_token=%s table_id=%s",
            step_task_id,
            kind,
            _mask_id(app_token),
            _mask_id(table_id),
        )
        record_id = _append_bitable_record(app_token=app_token, table_id=table_id, fields=fields, step_task_id=step_task_id)
        log_step(
            step_task_id,
            "bitable_write_succeeded",
            "success",
            f"kind={kind} strategy={BITABLE_LEDGER_STRATEGY} record_id={record_id}",
        )
        logger.info("Bitable row appended: step_task_id=%s kind=%s record_id=%s", step_task_id, kind, record_id)
    except Exception as exc:  # pragma: no cover - network/SDK
        at = settings.FEISHU_BITABLE_APP_TOKEN.strip()
        tid = settings.FEISHU_BITABLE_TABLE_ID.strip()
        extra = f"app_token={_mask_id(at)} table_id={_mask_id(tid)}"
        log_step(
            step_task_id,
            "bitable_write_failed",
            "failed",
            f"kind={kind} strategy={BITABLE_LEDGER_STRATEGY} | {extra} | exc={str(exc)[:280]}",
        )
        logger.warning("Bitable append exception: step_task_id=%s kind=%s %s err=%s", step_task_id, kind, extra, exc)


def _append_bitable_record(app_token: str, table_id: str, fields: dict[str, Any], step_task_id: str) -> str:
    # Prefer SDK if available; fallback to HTTP API when local stub shadows SDK modules.
    try:
        from lark_oapi.api.bitable.v1.model.app_table_record import AppTableRecord
        from lark_oapi.api.bitable.v1.model.create_app_table_record_request import (
            CreateAppTableRecordRequest,
        )
        from app.services.feishu.client import FeishuClient

        client = FeishuClient().client
        body = AppTableRecord.builder().fields(fields).build()
        request = (
            CreateAppTableRecordRequest.builder()
            .app_token(app_token)
            .table_id(table_id)
            .request_body(body)
            .build()
        )
        response = client.bitable.v1.app_table_record.create(request)
        if not response.success():
            detail = _format_bitable_api_failure(step_task_id, app_token, table_id, response)
            raise RuntimeError(detail)
        if response.data and response.data.record:
            return getattr(response.data.record, "record_id", "") or ""
        return ""
    except ModuleNotFoundError:
        return _append_bitable_record_via_http(app_token=app_token, table_id=table_id, fields=fields)


def _append_bitable_record_via_http(app_token: str, table_id: str, fields: dict[str, Any]) -> str:
    tenant_access_token = _fetch_tenant_access_token()

    record_resp = requests.post(
        f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records",
        headers={"Authorization": f"Bearer {tenant_access_token}"},
        json={"fields": fields},
        timeout=10,
    )
    record_resp.raise_for_status()
    record_payload = record_resp.json() if record_resp.content else {}
    if int(record_payload.get("code", -1)) != 0:
        raise RuntimeError(f"bitable_api_failed:{record_payload.get('msg', 'unknown')}")
    data = record_payload.get("data") or {}
    record = data.get("record") or {}
    return str(record.get("record_id") or "")


def _fetch_tenant_access_token() -> str:
    app_id = (settings.FEISHU_APP_ID or "").strip()
    app_secret = (settings.FEISHU_APP_SECRET or "").strip()
    if not app_id or not app_secret:
        raise RuntimeError("feishu_app_auth_missing")
    token_resp = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": app_id, "app_secret": app_secret},
        timeout=10,
    )
    token_resp.raise_for_status()
    token_payload = token_resp.json() if token_resp.content else {}
    if int(token_payload.get("code", -1)) != 0:
        raise RuntimeError(f"tenant_token_failed:{token_payload.get('msg', 'unknown')}")
    tenant_access_token = str(token_payload.get("tenant_access_token") or "")
    if not tenant_access_token:
        raise RuntimeError("tenant_access_token_empty")
    return tenant_access_token


def _resolve_rpa_evidence_table_id(app_token: str) -> str:
    access_token = _fetch_tenant_access_token()
    resp = requests.get(
        f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    resp.raise_for_status()
    payload = resp.json() if resp.content else {}
    if int(payload.get("code", -1)) != 0:
        raise RuntimeError(f"bitable_list_tables_failed:{payload.get('msg', 'unknown')}")
    items = ((payload.get("data") or {}).get("items") or [])
    for item in items:
        if str(item.get("name") or "").strip() == "RPA执行证据台账":
            return str(item.get("table_id") or "")
    raise RuntimeError("rpa_evidence_table_not_found")


def try_write_bitable_ledger(
    *,
    task_id: str,
    graph_result: dict[str, Any],
    task_record: TaskRecord,
    db: Session,
) -> None:
    """
    After LangGraph + DB refresh: append ledger rows for supported intents.
    Never raises.
    """
    rd = check_bitable_readiness()
    if not rd["bitable_write_enabled"]:
        log_step(task_id, "bitable_write_skipped", "success", "reason=enable_false")
        return
    if not rd["bitable_config_ready"]:
        log_step(
            task_id,
            "bitable_write_failed",
            "failed",
            f"reason=config_incomplete missing={','.join(rd['bitable_missing'])}",
        )
        return

    intent = graph_result.get("intent_code")
    status = graph_result.get("status")

    capability = str(graph_result.get("capability") or "")

    if (intent == "warehouse.adjust_inventory" or capability == "warehouse.adjust_inventory") and status == "succeeded":
        fields = _build_rpa_success_evidence_fields(task_record, graph_result, db)
        app_token = settings.FEISHU_BITABLE_APP_TOKEN.strip()
        rpa_table_id = _resolve_rpa_evidence_table_id(app_token=app_token)
        _bitable_append_row(
            step_task_id=task_id,
            fields=fields,
            kind="adjust_inventory_rpa_success",
            table_id_override=rpa_table_id,
        )
        return

    if intent == "product.query_sku_status" and status == "succeeded":
        product_data = graph_result.get("query_product_data")
        if not isinstance(product_data, dict):
            logger.warning("bitable: missing query_product_data, task_id=%s", task_id)
            return
        fields = _build_ledger_query_success(task_record, graph_result, product_data)
        _bitable_append_row(step_task_id=task_id, fields=fields, kind="query_success")
        return

    if intent == "product.update_price" and status == "awaiting_confirmation":
        fields = _build_ledger_update_price_awaiting(task_record, graph_result)
        _bitable_append_row(step_task_id=task_id, fields=fields, kind="update_price_awaiting")
        return

    if intent == "product.update_price" and status == "succeeded":
        fields = _build_ledger_update_price_succeeded(task_record, graph_result)
        _bitable_append_row(step_task_id=task_id, fields=fields, kind="update_price_succeeded")
        return

    if intent == "system.confirm_task" and status == "succeeded":
        fields = _build_ledger_confirm_task(task_record, graph_result)
        _bitable_append_row(step_task_id=task_id, fields=fields, kind="confirm_task_success")
        orig_id = (getattr(task_record, "target_task_id", None) or "").strip()
        if orig_id:
            orig = db.query(TaskRecord).filter(TaskRecord.task_id == orig_id).first()
            if orig:
                db.refresh(orig)
                fields_o = _build_ledger_original_after_confirm(orig, graph_result)
                _bitable_append_row(
                    step_task_id=orig_id,
                    fields=fields_o,
                    kind="original_task_succeeded_after_confirm",
                )
        return


def try_write_query_sku_bitable(
    *,
    task_id: str,
    graph_result: dict[str, Any],
    intent_text: str = "",
) -> None:
    """Tests / callers that only have task_id + graph_result; loads TaskRecord from DB."""
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        tr = db.query(TaskRecord).filter(TaskRecord.task_id == task_id).first()
        if tr:
            try_write_bitable_ledger(task_id=task_id, graph_result=graph_result, task_record=tr, db=db)
    finally:
        db.close()
