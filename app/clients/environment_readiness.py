"""Minimal environment readiness checks for local integration."""
from __future__ import annotations

import os
import socket
import ssl
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urlparse

from app.core.config import settings

FEISHU_TARGET_HOST = "open.feishu.cn"
FEISHU_TARGET_PORT = 443

PROXY_ENV_KEYS = (
    "http_proxy",
    "https_proxy",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "all_proxy",
    "NO_PROXY",
    "no_proxy",
)


@dataclass
class EnvironmentReadinessResult:
    redis_ready: bool
    redis_reason: str
    feishu_network_ready: bool
    feishu_reason: str
    environment_ready: bool
    dns_ready: bool
    dns_reason: str
    tcp_ready: bool
    tcp_reason: str
    tls_ready: bool
    tls_reason: str
    target_host: str
    feishu_resolved: list[str]
    broker_host: str
    proxy_enabled: bool
    proxy_source: str
    proxy_env: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _check_tcp(host: str, port: int, timeout_seconds: float = 1.0) -> tuple[bool, str]:
    try:
        with socket.create_connection((host, int(port)), timeout=timeout_seconds):
            return True, "ready"
    except OSError as exc:
        return False, str(exc)


def _collect_proxy_env() -> tuple[bool, str, dict[str, str]]:
    snap: dict[str, str] = {}
    for key in PROXY_ENV_KEYS:
        val = os.environ.get(key)
        if val:
            snap[key] = val
    enabled = bool(snap)
    source = ",".join(sorted(snap.keys())) if snap else "none"
    return enabled, source, snap


def _check_dns(host: str) -> tuple[bool, str, list[str]]:
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
        uniq: list[str] = []
        seen: set[str] = set()
        for info in infos:
            ip = info[4][0]
            if ip not in seen:
                seen.add(ip)
                uniq.append(ip)
            if len(uniq) >= 8:
                break
        return True, "resolved", uniq
    except OSError as exc:
        return False, str(exc), []


def _check_tls(host: str, port: int, timeout_seconds: float = 3.0) -> tuple[bool, str]:
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=timeout_seconds) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as tls_sock:
                return True, f"ready:{tls_sock.version()}"
    except OSError as exc:
        return False, str(exc)


def check_environment_readiness() -> EnvironmentReadinessResult:
    parsed = urlparse(settings.CELERY_BROKER_URL)
    redis_host = parsed.hostname or settings.REDIS_HOST or "localhost"
    redis_port = int(parsed.port or settings.REDIS_PORT or 6379)
    redis_ready, redis_reason = _check_tcp(redis_host, redis_port, timeout_seconds=1.0)

    proxy_enabled, proxy_source, proxy_env = _collect_proxy_env()
    target_host = f"{FEISHU_TARGET_HOST}:{FEISHU_TARGET_PORT}"
    broker_host = f"{redis_host}:{redis_port}"

    dns_ready, dns_reason, feishu_resolved = _check_dns(FEISHU_TARGET_HOST)
    if not dns_ready:
        tcp_ready, tcp_reason = False, f"skipped:{dns_reason}"
        tls_ready, tls_reason = False, "skipped:dns_not_ready"
        feishu_reason = dns_reason
    else:
        tcp_ready, tcp_reason = _check_tcp(FEISHU_TARGET_HOST, FEISHU_TARGET_PORT, timeout_seconds=2.0)
        if not tcp_ready:
            tls_ready, tls_reason = False, f"skipped:{tcp_reason}"
            feishu_reason = tcp_reason
        else:
            tls_ready, tls_reason = _check_tls(FEISHU_TARGET_HOST, FEISHU_TARGET_PORT, timeout_seconds=3.0)
            feishu_reason = tcp_reason

    feishu_network_ready = bool(tcp_ready)
    overall = bool(redis_ready and feishu_network_ready)

    return EnvironmentReadinessResult(
        redis_ready=redis_ready,
        redis_reason=redis_reason,
        feishu_network_ready=feishu_network_ready,
        feishu_reason=feishu_reason,
        environment_ready=overall,
        dns_ready=dns_ready,
        dns_reason=dns_reason,
        tcp_ready=tcp_ready,
        tcp_reason=tcp_reason,
        tls_ready=tls_ready,
        tls_reason=tls_reason,
        target_host=target_host,
        feishu_resolved=feishu_resolved,
        broker_host=broker_host,
        proxy_enabled=proxy_enabled,
        proxy_source=proxy_source,
        proxy_env=proxy_env,
    )
