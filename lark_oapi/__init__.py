"""
Compatibility wrapper for `lark_oapi`.

Priority:
1) If real SDK exists in site-packages, load and re-export it.
2) Otherwise fallback to a lightweight local stub for tests.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_real_sdk() -> bool:
    current_file = Path(__file__).resolve()
    package_name = __name__
    for search_path in sys.path:
        if not search_path:
            continue
        candidate = Path(search_path) / package_name / "__init__.py"
        if not candidate.exists():
            continue
        # Skip current local stub path.
        if candidate.resolve() == current_file:
            continue
        spec = importlib.util.spec_from_file_location(
            package_name,
            str(candidate),
            submodule_search_locations=[str(candidate.parent)],
        )
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        # Ensure package-relative imports (e.g. lark_oapi.api.*) resolve correctly.
        sys.modules[package_name] = module
        spec.loader.exec_module(module)
        globals().update(module.__dict__)
        return True
    return False


if not _load_real_sdk():
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

