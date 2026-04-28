from __future__ import annotations

from pydantic import BaseModel, Field


class ExtractedField(BaseModel):
    name: str = Field(default="", min_length=1)
    label: str = Field(default="", min_length=1)
    value: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    source: str = Field(default="rule", min_length=1)
    needs_review: bool = True
    warning: str = ""


class DocumentExtractionInput(BaseModel):
    document_id: str = Field(default="", min_length=1)
    document_type: str = Field(default="unknown", min_length=1)
    raw_text: str = ""
    ocr_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    ocr_provider: str = Field(default="mock", min_length=1)
    hint_document_type: str = Field(default="unknown", min_length=1)
    ocr_fallback_used: bool = False


class DocumentExtractionOutput(BaseModel):
    status: str = Field(default="succeeded", min_length=1)
    document_type: str = Field(default="unknown", min_length=1)
    fields: list[ExtractedField] = Field(default_factory=list)
    overall_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    missing_fields: list[str] = Field(default_factory=list)
    needs_manual_review: bool = True
    warnings: list[str] = Field(default_factory=list)
    fallback_used: bool = False
    error: str = ""
    extractor: str = Field(default="rule", min_length=1)
