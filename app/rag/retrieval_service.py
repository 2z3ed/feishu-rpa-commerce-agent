"""RAG retrieval: use_case + optional category filter; never raises from callers."""
from __future__ import annotations

from app.core.config import settings
from app.core.logging import logger
from app.rag.embedding import embed_text
from app.rag.milvus_adapter import MilvusRagAdapter
from app.rag.models import RetrievalHit, RetrievalResult

# Milvus collection dynamic fields (ingest accordingly)
OUTPUT_FIELDS = ["text", "use_case", "category", "intent_hint"]

_ADAPTER: MilvusRagAdapter | None = None

# Stored in Milvus varchar field `use_case`
USE_CASE_COMMAND_INTERPRETATION = "command_interpretation"
USE_CASE_RULE_AUGMENT = "rule_augment"
USE_CASE_FAILURE_EXPLANATION = "failure_explanation"


def _adapter() -> MilvusRagAdapter:
    global _ADAPTER
    if _ADAPTER is None:
        _ADAPTER = MilvusRagAdapter(settings.MILVUS_HOST, settings.MILVUS_PORT)
    return _ADAPTER


def _escape_str(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _category_expr(categories: list[str] | None) -> str:
    if not categories:
        return ""
    esc = [_escape_str(c) for c in categories if c and c.replace("_", "").isalnum()]
    if not esc:
        return ""
    inner = ", ".join(f'"{c}"' for c in esc)
    return f"category in [{inner}]"


def retrieve(
    *,
    use_case: str,
    query: str,
    categories: list[str] | None = None,
    intent_hints: list[str] | None = None,
) -> RetrievalResult:
    """
    Vector search filtered by use_case (+ optional category in Milvus expr).

    category values: sop | faq | case | error_resolution | rule
    intent_hints: when set, adds expr intent_hint in ["..."] (varchar field)
    """
    q = (query or "").strip()
    try:
        if not settings.ENABLE_RAG:
            return RetrievalResult(
                use_case=use_case, query=q, fallback=True, error="rag_disabled"
            )
        coll = (settings.MILVUS_COLLECTION_NAME or "").strip()
        if not coll:
            return RetrievalResult(
                use_case=use_case, query=q, fallback=True, error="collection_not_configured"
            )

        dim = int(settings.RAG_EMBEDDING_DIM)
        if dim <= 0:
            return RetrievalResult(
                use_case=use_case, query=q, fallback=True, error="invalid_embedding_dim"
            )

        vec = embed_text(q, dim)
        uc_esc = _escape_str(use_case)
        parts = [f'use_case == "{uc_esc}"']
        cat_ex = _category_expr(categories)
        if cat_ex:
            parts.append(cat_ex)
        if intent_hints:
            ih_esc = [_escape_str(h) for h in intent_hints if h]
            if ih_esc:
                inner = ", ".join(f'"{h}"' for h in ih_esc)
                parts.append(f"intent_hint in [{inner}]")
        expr = " && ".join(parts)

        rows = _adapter().search(
            collection_name=coll,
            query_vector=vec,
            expr=expr,
            top_k=max(1, int(settings.RAG_TOP_K)),
            output_fields=OUTPUT_FIELDS,
        )

        hits: list[RetrievalHit] = []
        th = float(settings.RAG_SCORE_THRESHOLD)
        for i, row in enumerate(rows):
            sc = float(row.get("score", 0))
            if th > 0 and sc < th:
                continue
            hid = row.get("id", i)
            hits.append(
                RetrievalHit(
                    hit_id=str(hid),
                    text=str(row.get("text", ""))[:4000],
                    score=sc,
                    use_case=str(row.get("use_case", "")),
                    category=str(row.get("category", "")),
                    intent_hint=str(row.get("intent_hint", ""))[:256],
                )
            )

        return RetrievalResult(use_case=use_case, query=q, hits=hits, fallback=False, error=None)
    except Exception as exc:
        logger.warning("RAG retrieve failed: use_case=%s err=%s", use_case, exc)
        return RetrievalResult(
            use_case=use_case, query=q, fallback=True, error=f"exception:{exc}"
        )


def format_rag_footer(hits: list[RetrievalHit], title: str = "知识库参考", max_items: int = 3) -> str:
    if not hits:
        return ""
    lines: list[str] = []
    for h in hits[:max_items]:
        t = h.text.strip().replace("\n", " ")
        if t:
            lines.append(f"· {t[:280]}")
    if not lines:
        return ""
    return f"\n\n—— {title} ——\n" + "\n".join(lines)


def check_rag_readiness() -> dict:
    """Config + Milvus TCP; collection existence is checked at search time."""
    enabled = bool(settings.ENABLE_RAG)
    coll = (settings.MILVUS_COLLECTION_NAME or "").strip()
    dim_ok = int(settings.RAG_EMBEDDING_DIM) > 0
    config_ready = bool(coll) and dim_ok

    milvus_tcp_ok = False
    tcp_reason = "skipped"
    if enabled and config_ready:
        try:
            import socket

            with socket.create_connection(
                (settings.MILVUS_HOST, int(settings.MILVUS_PORT)), timeout=1.5
            ):
                milvus_tcp_ok = True
                tcp_reason = "tcp_ok"
        except OSError as exc:
            tcp_reason = str(exc)
    elif not enabled:
        tcp_reason = "rag_disabled"
    elif not coll:
        tcp_reason = "MILVUS_COLLECTION_NAME_missing"
    elif not dim_ok:
        tcp_reason = "RAG_EMBEDDING_DIM_invalid"

    retrieval_allowed = enabled and config_ready and milvus_tcp_ok

    if not enabled:
        rag_reason = "rag_disabled"
    elif not config_ready:
        rag_reason = "config_incomplete"
    elif not milvus_tcp_ok:
        rag_reason = f"milvus_unreachable:{tcp_reason}"
    else:
        rag_reason = "ready"

    return {
        "rag_enabled": enabled,
        "milvus_config_ready": config_ready,
        "milvus_retrieval_allowed": retrieval_allowed,
        "rag_reason": rag_reason,
    }
