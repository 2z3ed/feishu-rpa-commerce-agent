from __future__ import annotations

from pydantic import BaseModel, Field


class ActionPlanStats(BaseModel):
    target_count: int = Field(default=0, ge=0)
    high_priority_count: int = Field(default=0, ge=0)
    manual_review_count: int = Field(default=0, ge=0)
    url_fix_count: int = Field(default=0, ge=0)
    retry_count: int = Field(default=0, ge=0)
    observe_count: int = Field(default=0, ge=0)


class ActionPlanInput(BaseModel):
    stats: ActionPlanStats = Field(default_factory=ActionPlanStats)
    targets: list[dict] = Field(default_factory=list)
    plan_focus: str = Field(default="overview", min_length=1)


class ActionPlanOutput(BaseModel):
    plan_text: str = Field(default="", min_length=1)
    provider: str = Field(default="mock", min_length=1)
    plan_focus: str = Field(default="overview", min_length=1)
    fallback_used: bool = False
    error: str = ""
