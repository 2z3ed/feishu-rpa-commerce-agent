from pydantic import BaseModel, Field


class LLMIntentFallbackOutput(BaseModel):
    intent: str = Field(default="unknown", min_length=1)
    slots: dict = Field(default_factory=dict)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    needs_confirmation: bool = False
    clarification_question: str = ""
    reason: str = ""
