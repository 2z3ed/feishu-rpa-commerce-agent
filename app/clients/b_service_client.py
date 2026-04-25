from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings


class BServiceError(RuntimeError):
    """B service integration error with user-readable message."""


@dataclass
class EnvelopeError:
    message: str
    code: str
    status_code: int
    request_id: str
    timestamp: str


class BServiceClient:
    def __init__(self, base_url: str | None = None, timeout_seconds: float = 5.0):
        self.base_url = (base_url or settings.B_SERVICE_BASE_URL).rstrip("/")
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout_seconds)

    def get_today_summary(self) -> dict[str, Any]:
        return self._get_envelope_data("/internal/summary/today")

    def get_monitor_targets(self) -> dict[str, Any]:
        return self._get_envelope_data("/internal/monitor/targets")

    def refresh_monitor_target_price(self, target_id: int | str) -> dict[str, Any]:
        return self._post_envelope_data(f"/internal/monitor/{int(target_id)}/refresh-price", {})

    def refresh_monitor_prices(self) -> dict[str, Any]:
        return self._post_envelope_data("/internal/monitor/refresh-prices", {})

    def get_monitor_target_price_history(self, target_id: int | str, limit: int = 5) -> dict[str, Any]:
        safe_limit = int(limit) if int(limit) > 0 else 5
        return self._get_envelope_data(
            f"/internal/monitor/{int(target_id)}/price-history?limit={safe_limit}"
        )

    def get_product_detail(self, product_id: int) -> dict[str, Any]:
        return self._get_envelope_data(f"/internal/products/{product_id}/detail")

    def add_monitor_by_url(self, url: str) -> dict[str, Any]:
        return self._post_envelope_data("/internal/monitor/add-by-url", {"url": url})

    def discovery_search(self, query: str) -> dict[str, Any]:
        return self._post_envelope_data("/internal/discovery/search", {"query": query})

    def get_discovery_batch(self, batch_id: int | str) -> dict[str, Any]:
        return self._get_envelope_data(f"/internal/discovery/batches/{batch_id}")

    def add_from_candidates(
        self,
        *,
        batch_id: int,
        candidate_ids: list[int],
        source_type: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "batch_id": int(batch_id),
            "candidate_ids": [int(candidate_id) for candidate_id in candidate_ids],
        }
        if source_type:
            payload["source_type"] = source_type
        return self._post_envelope_data("/internal/monitor/add-from-candidates", payload)

    def pause_monitor_target(self, target_id: int | str) -> dict[str, Any]:
        return self._post_envelope_data(f"/internal/monitor/{int(target_id)}/pause", {})

    def resume_monitor_target(self, target_id: int | str) -> dict[str, Any]:
        return self._post_envelope_data(f"/internal/monitor/{int(target_id)}/resume", {})

    def delete_monitor_target(self, target_id: int | str) -> dict[str, Any]:
        return self._delete_envelope_data(f"/internal/monitor/{int(target_id)}")

    def delete_monitor_target_raw_response(self, target_id: int | str) -> dict[str, Any]:
        path = f"/internal/monitor/{int(target_id)}"
        try:
            response = self._client.request(method="DELETE", url=path)
        except httpx.HTTPError as exc:
            raise BServiceError(f"B 服务不可达，请确认 {self.base_url} 已启动：{exc}") from exc
        try:
            payload = response.json()
        except ValueError as exc:
            raise BServiceError("B 服务返回了无法解析的 JSON 响应") from exc
        if not isinstance(payload, dict):
            raise BServiceError("B 服务返回格式错误：不是 Envelope 对象")
        return payload

    def _get_envelope_data(self, path: str) -> dict[str, Any]:
        return self._request_envelope_data(method="GET", path=path)

    def _post_envelope_data(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request_envelope_data(method="POST", path=path, json_payload=payload)

    def _delete_envelope_data(self, path: str) -> dict[str, Any]:
        return self._request_envelope_data(method="DELETE", path=path)

    def _request_envelope_data(
        self,
        *,
        method: str,
        path: str,
        json_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            response = self._client.request(method=method, url=path, json=json_payload)
        except httpx.HTTPError as exc:
            raise BServiceError(f"B 服务不可达，请确认 {self.base_url} 已启动：{exc}") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise BServiceError("B 服务返回了无法解析的 JSON 响应") from exc

        if not isinstance(payload, dict):
            raise BServiceError("B 服务返回格式错误：不是 Envelope 对象")

        ok = bool(payload.get("ok"))
        if ok:
            data = payload.get("data")
            if data is None:
                return {}
            if not isinstance(data, dict):
                raise BServiceError("B 服务返回格式错误：data 不是对象")
            return data

        err = payload.get("error")
        if isinstance(err, dict):
            envelope_error = EnvelopeError(
                message=str(err.get("message") or "未知错误"),
                code=str(err.get("code") or "unknown_error"),
                status_code=int(err.get("status_code") or response.status_code or 500),
                request_id=str(err.get("request_id") or ""),
                timestamp=str(err.get("timestamp") or ""),
            )
            raise BServiceError(
                f"B 服务错误：{envelope_error.message} "
                f"(code={envelope_error.code}, status={envelope_error.status_code})"
            )

        raise BServiceError(f"B 服务错误：HTTP {response.status_code}")

