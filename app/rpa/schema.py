"""Frozen JSON contract for RPA runners (dev-stage local fake + future backends)."""
from __future__ import annotations

from typing import Any, Literal, Optional, Protocol

from pydantic import BaseModel, Field

VerifyMode = Literal["none", "basic", "strict"]


class RpaExecutionInput(BaseModel):
    """Unified input for RPA runners."""

    task_id: str
    trace_id: str
    intent: str
    platform: str = "woo"
    params: dict[str, Any] = Field(default_factory=dict)
    timeout_s: int = 180
    evidence_dir: str
    verify_mode: VerifyMode = "basic"
    dry_run: bool = False

    model_config = {"extra": "forbid"}


class RpaExecutionOutput(BaseModel):
    """Unified output from RPA runners — no ad-hoc shapes per runner."""

    success: bool
    result_summary: str = ""
    parsed_result: dict[str, Any] = Field(default_factory=dict)
    evidence_paths: list[str] = Field(default_factory=list)
    error_code: Optional[str] = None
    error_message: Optional[str] = None

    model_config = {"extra": "forbid"}


class RpaRunner(Protocol):
    """Implementations: local fake (dev), future Playwright/production adapters."""

    def run(self, inp: RpaExecutionInput) -> RpaExecutionOutput:
        ...
