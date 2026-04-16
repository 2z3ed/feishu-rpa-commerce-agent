from __future__ import annotations

import json
import urllib.request
from typing import Any

from app.core.config import settings


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
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        body = resp.read().decode("utf-8")
    out = json.loads(body or "{}")
    if not isinstance(out, dict):
        raise ValueError("yingdao_bridge_invalid_response")
    return out
