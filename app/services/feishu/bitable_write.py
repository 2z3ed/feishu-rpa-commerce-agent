"""
Minimal one-way write to Feishu Bitable (multidimensional table).

First version: product.query_sku_status success only. Table columns must match field names below.
"""
from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.core.logging import logger
from app.core.time import format_shanghai_dt, get_shanghai_now
from app.services.feishu.client import FeishuClient
from app.utils.task_logger import log_step

# Column names in the Bitable table (文本 / 数字等需与多维表列名一致)
BITABLE_FIELD_TASK_ID = "task_id"
BITABLE_FIELD_STATUS = "status"
BITABLE_FIELD_INTENT_TEXT = "intent_text"
BITABLE_FIELD_SKU = "sku"
BITABLE_FIELD_PRODUCT_NAME = "product_name"
BITABLE_FIELD_INVENTORY = "inventory"
BITABLE_FIELD_PRICE = "price"
BITABLE_FIELD_PLATFORM = "platform"
BITABLE_FIELD_CREATED_AT = "created_at"
BITABLE_FIELD_RESULT_SUMMARY = "result_summary"


def _mask_id(value: str, head: int = 4, tail: int = 4) -> str:
    """Log-safe preview of app_token / table_id (not a secret hash)."""
    v = (value or "").strip()
    if not v:
        return "(empty)"
    if len(v) <= head + tail + 1:
        return f"len={len(v)}"
    return f"{v[:head]}...{v[-tail:]} len={len(v)}"


def _format_bitable_api_failure(task_id: str, app_token: str, table_id: str, response) -> str:
    """Build a concise detail for task_steps + logs (permission vs generic)."""
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
    logger.warning(
        "Bitable create API error: task_id=%s %s",
        task_id,
        detail[:800],
    )
    return detail[:500]


def check_bitable_readiness() -> dict[str, Any]:
    """Config-only check: whether Bitable write is allowed and what is missing."""
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
    }


def _build_query_sku_fields(
    *,
    task_id: str,
    task_status: str,
    intent_text: str,
    product_data: dict[str, Any],
    result_summary: str,
) -> dict[str, Any]:
    created = format_shanghai_dt(get_shanghai_now())
    return {
        BITABLE_FIELD_TASK_ID: task_id,
        BITABLE_FIELD_STATUS: task_status,
        BITABLE_FIELD_INTENT_TEXT: (intent_text or "")[:2000],
        BITABLE_FIELD_SKU: str(product_data.get("sku", "")),
        BITABLE_FIELD_PRODUCT_NAME: str(product_data.get("product_name", "")),
        BITABLE_FIELD_INVENTORY: str(product_data.get("inventory", "")),
        BITABLE_FIELD_PRICE: str(product_data.get("price", "")),
        BITABLE_FIELD_PLATFORM: str(product_data.get("platform", "")),
        BITABLE_FIELD_CREATED_AT: created,
        BITABLE_FIELD_RESULT_SUMMARY: (result_summary or "")[:2000],
    }


def try_write_query_sku_bitable(
    *,
    task_id: str,
    graph_result: dict[str, Any],
    intent_text: str,
) -> None:
    """
    After a successful product.query_sku_status, optionally append one Bitable row.
    Never raises; failures are logged and recorded in task_steps only.
    """
    if graph_result.get("intent_code") != "product.query_sku_status":
        return
    if graph_result.get("status") != "succeeded":
        return
    product_data = graph_result.get("query_product_data")
    if not isinstance(product_data, dict):
        logger.warning("bitable: missing query_product_data, task_id=%s", task_id)
        return

    rd = check_bitable_readiness()
    if not rd["bitable_write_enabled"]:
        log_step(
            task_id,
            "bitable_write_skipped",
            "success",
            "reason=enable_false",
        )
        return
    if not rd["bitable_config_ready"]:
        log_step(
            task_id,
            "bitable_write_failed",
            "failed",
            f"reason=config_incomplete missing={','.join(rd['bitable_missing'])}",
        )
        return

    fields = _build_query_sku_fields(
        task_id=task_id,
        task_status="succeeded",
        intent_text=intent_text,
        product_data=product_data,
        result_summary=graph_result.get("result_summary") or "",
    )

    log_step(task_id, "bitable_write_started", "processing", "")

    try:
        from lark_oapi.api.bitable.v1.model.app_table_record import AppTableRecord
        from lark_oapi.api.bitable.v1.model.create_app_table_record_request import (
            CreateAppTableRecordRequest,
        )

        client = FeishuClient().client
        app_token = settings.FEISHU_BITABLE_APP_TOKEN.strip()
        table_id = settings.FEISHU_BITABLE_TABLE_ID.strip()

        logger.info(
            "Bitable create will use: task_id=%s app_token=%s table_id=%s",
            task_id,
            _mask_id(app_token),
            _mask_id(table_id),
        )

        body = AppTableRecord.builder().fields(fields).build()
        request = (
            CreateAppTableRecordRequest.builder()
            .app_token(app_token)
            .table_id(table_id)
            .request_body(body)
            .build()
        )
        response = client.bitable.v1.app_table_record.create(request)
        if response.success():
            record_id = ""
            if response.data and response.data.record:
                record_id = getattr(response.data.record, "record_id", "") or ""
            log_step(
                task_id,
                "bitable_write_succeeded",
                "success",
                f"record_id={record_id}" if record_id else "record_id=",
            )
            logger.info("Bitable row created: task_id=%s record_id=%s", task_id, record_id)
        else:
            detail = _format_bitable_api_failure(task_id, app_token, table_id, response)
            log_step(task_id, "bitable_write_failed", "failed", detail)
    except Exception as exc:  # pragma: no cover - network/SDK
        at = settings.FEISHU_BITABLE_APP_TOKEN.strip()
        tid = settings.FEISHU_BITABLE_TABLE_ID.strip()
        extra = f"app_token={_mask_id(at)} table_id={_mask_id(tid)}"
        log_step(task_id, "bitable_write_failed", "failed", f"{extra} | exc={str(exc)[:320]}")
        logger.warning("Bitable create exception: task_id=%s %s err=%s", task_id, extra, exc)
