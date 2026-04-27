from __future__ import annotations

from pydantic import BaseModel, Field


class MonitorSummaryStats(BaseModel):
    target_count: int = Field(default=0, ge=0)
    anomaly_count: int = Field(default=0, ge=0)
    low_confidence_count: int = Field(default=0, ge=0)
    manual_review_count: int = Field(default=0, ge=0)
    high_priority_count: int = Field(default=0, ge=0)


class MonitorSummaryInput(BaseModel):
    stats: MonitorSummaryStats = Field(default_factory=MonitorSummaryStats)
    targets: list[dict] = Field(default_factory=list)
    summary_focus: str = Field(default="overview", min_length=1)


class MonitorSummaryOutput(BaseModel):
    summary_text: str = Field(default="", min_length=1)
    provider: str = Field(default="mock", min_length=1)
    summary_focus: str = Field(default="overview", min_length=1)
    fallback_used: bool = False
    error: str = ""
