from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from typing import Any

from app.core.config import settings


class YingdaoBridgeError(RuntimeError):
    def __init__(self, *, failure_layer: str, operation_result: str, verify_reason: str):
        super().__init__(verify_reason)
        self.failure_layer = failure_layer
        self.operation_result = operation_result
        self.verify_reason = verify_reason


_BRIDGE_REQUIRED_KEYS = (
    "task_id",
    "confirm_task_id",
    "provider_id",
    "capability",
    "rpa_vendor",
    "operation_result",
    "verify_passed",
    "verify_reason",
    "failure_layer",
    "status",
    "raw_result_path",
    "evidence_paths",
)


def run_yingdao_adjust_inventory(payload: dict[str, Any]) -> dict[str, Any]:
    """Call local Yingdao bridge and return normalized result."""
    base_url = str(settings.YINGDAO_BRIDGE_BASE_URL or "http://127.0.0.1:17891").rstrip("/")
    req = urllib.request.Request(
        f"{base_url}/run",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    timeout_s = max(int(settings.YINGDAO_BRIDGE_TIMEOUT_S or 30), 1)
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        reason = f"bridge_http_error:{exc.code}"
        try:
            err_body = (exc.read() or b"").decode("utf-8")
            obj = json.loads(err_body or "{}")
            detail = str(obj.get("detail") or "").strip()
            if detail:
                reason = detail
        except Exception:
            pass
        raise YingdaoBridgeError(
            failure_layer="bridge_http_error",
            operation_result="write_adjust_inventory_bridge_failed",
            verify_reason=reason,
        ) from exc
    except (TimeoutError, socket.timeout) as exc:
        raise YingdaoBridgeError(
            failure_layer="bridge_timeout",
            operation_result="write_adjust_inventory_bridge_timeout",
            verify_reason="bridge_request_timeout",
        ) from exc
    except urllib.error.URLError as exc:
        raise YingdaoBridgeError(
            failure_layer="bridge_unreachable",
            operation_result="write_adjust_inventory_bridge_unreachable",
            verify_reason=f"bridge_unreachable:{exc.reason}",
        ) from exc

    try:
        out = json.loads(body or "{}")
    except Exception as exc:
        raise YingdaoBridgeError(
            failure_layer="bridge_result_invalid_json",
            operation_result="write_adjust_inventory_bridge_invalid_result",
            verify_reason="bridge_response_invalid_json",
        ) from exc
    if not isinstance(out, dict):
        raise YingdaoBridgeError(
            failure_layer="bridge_result_invalid_shape",
            operation_result="write_adjust_inventory_bridge_invalid_result",
            verify_reason="bridge_response_not_object",
        )
    missing = [k for k in _BRIDGE_REQUIRED_KEYS if k not in out]
    if missing:
        raise YingdaoBridgeError(
            failure_layer="bridge_result_missing_fields",
            operation_result="write_adjust_inventory_bridge_invalid_result",
            verify_reason=f"bridge_response_missing_fields:{','.join(missing)}",
        )
    return out
