from __future__ import annotations

from pydantic import BaseModel, Field


class OCRDocumentInput(BaseModel):
    document_id: str = Field(default="", min_length=1)
    file_name: str = Field(default="", min_length=1)
    mime_type: str = Field(default="application/octet-stream", min_length=1)
    file_path: str = Field(default="", min_length=1)
    source: str = Field(default="mock", min_length=1)
    requested_by: str = Field(default="unknown", min_length=1)
    hint_document_type: str = Field(default="unknown", min_length=1)


class OCRTextBlock(BaseModel):
    text: str = Field(default="", min_length=1)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class OCRDocumentOutput(BaseModel):
    status: str = Field(default="succeeded", min_length=1)
    document_type: str = Field(default="unknown", min_length=1)
    raw_text: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    provider: str = Field(default="mock", min_length=1)
    blocks: list[OCRTextBlock] = Field(default_factory=list)
    needs_manual_review: bool = True
    warnings: list[str] = Field(default_factory=list)
    fallback_used: bool = False
    error: str = ""
