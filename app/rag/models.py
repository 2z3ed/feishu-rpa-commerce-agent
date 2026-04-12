"""RAG retrieval result models (minimal)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RetrievalHit:
    """One Milvus hit (mapped from search result)."""

    hit_id: str
    text: str
    score: float
    use_case: str
    category: str
    intent_hint: str = ""


@dataclass
class RetrievalResult:
    """Outcome of a single retrieval call."""

    use_case: str
    query: str
    hits: list[RetrievalHit] = field(default_factory=list)
    fallback: bool = False
    error: str | None = None
