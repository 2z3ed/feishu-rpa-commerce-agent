from __future__ import annotations

from pydantic import BaseModel, Field


class AnomalyExplanationStats(BaseModel):
    target_count: int = Field(default=0, ge=0)
    anomaly_count: int = Field(default=0, ge=0)
    low_confidence_count: int = Field(default=0, ge=0)
    failed_probe_count: int = Field(default=0, ge=0)
    manual_review_count: int = Field(default=0, ge=0)


class AnomalyExplanationInput(BaseModel):
    stats: AnomalyExplanationStats = Field(default_factory=AnomalyExplanationStats)
    targets: list[dict] = Field(default_factory=list)
    explanation_focus: str = Field(default="overview", min_length=1)


class AnomalyExplanationOutput(BaseModel):
    explanation_text: str = Field(default="", min_length=1)
    provider: str = Field(default="mock", min_length=1)
    explanation_focus: str = Field(default="overview", min_length=1)
    fallback_used: bool = False
    error: str = ""
