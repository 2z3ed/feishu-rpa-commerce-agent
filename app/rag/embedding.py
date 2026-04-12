"""Deterministic embedding for RAG (no external model; replace with real embedder later)."""
from __future__ import annotations

import hashlib


def embed_text(text: str, dim: int) -> list[float]:
    """L2-normalized pseudo-vector from text (stable for the same string)."""
    if dim <= 0:
        return []
    t = (text or "").strip()
    seed = t.encode("utf-8")
    out: list[float] = []
    block = hashlib.sha256(seed).digest()
    for i in range(dim):
        b = block[i % len(block)]
        out.append((b / 127.5) - 1.0)
        if i % 32 == 31:
            block = hashlib.sha256(block + str(i).encode()).digest()
    norm = sum(x * x for x in out) ** 0.5 or 1.0
    return [x / norm for x in out]
