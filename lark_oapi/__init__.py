"""
Local lightweight stub for `lark_oapi`.

This repo's unit tests and local scripts may run without the real Feishu SDK
installed. The production environment can still use the real `lark_oapi`
package; this stub only provides the minimal surface to satisfy imports.
"""

from __future__ import annotations


class LogLevel:
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40


class Client:
    def builder(self):
        return _Builder()


class _Builder:
    def app_id(self, *_args, **_kwargs):
        return self

    def with_app_id(self, *_args, **_kwargs):
        return self

    def app_secret(self, *_args, **_kwargs):
        return self

    def with_app_secret(self, *_args, **_kwargs):
        return self

    def log_level(self, *_args, **_kwargs):
        return self

    def with_log_level(self, *_args, **_kwargs):
        return self

    def build(self):
        return Client()


class _ImV1:
    class P2ImMessageReceiveV1:  # pragma: no cover
        pass


class _Im:
    v1 = _ImV1()


im = _Im()

