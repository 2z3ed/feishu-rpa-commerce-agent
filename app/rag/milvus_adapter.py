"""Minimal Milvus vector search adapter for RAG."""
from __future__ import annotations

from typing import Any

from app.core.logging import logger


class MilvusRagAdapter:
    """Thin wrapper: connect, search with expr filter, swallow errors → empty hits."""

    def __init__(self, host: str, port: int, alias: str = "rag_milvus") -> None:
        self.host = host
        self.port = int(port)
        self.alias = alias
        self._connected = False

    def _ensure_connect(self) -> bool:
        if self._connected:
            return True
        try:
            from pymilvus import connections

            connections.connect(alias=self.alias, host=self.host, port=str(self.port))
            self._connected = True
            return True
        except Exception as exc:
            logger.warning("Milvus connect failed: %s", exc)
            return False

    def search(
        self,
        *,
        collection_name: str,
        query_vector: list[float],
        expr: str,
        top_k: int,
        output_fields: list[str],
        metric_type: str = "IP",
    ) -> list[dict[str, Any]]:
        if not collection_name or not query_vector:
            return []
        if not self._ensure_connect():
            return []
        try:
            from pymilvus import Collection, utility

            if not utility.has_collection(collection_name, using=self.alias):
                logger.info("Milvus collection missing: %s", collection_name)
                return []
            col = Collection(collection_name, using=self.alias)
            col.load()
            res = col.search(
                data=[query_vector],
                anns_field="embedding",
                param={"metric_type": metric_type, "params": {"nprobe": 16}},
                limit=top_k,
                expr=expr if expr.strip() else None,
                output_fields=output_fields,
            )
            rows: list[dict[str, Any]] = []
            for hits in res:
                for hit in hits:
                    ent = hit.entity
                    row: dict[str, Any] = {
                        "id": hit.id,
                        "score": float(hit.distance),
                    }
                    for f in output_fields:
                        row[f] = ent.get(f) if hasattr(ent, "get") else getattr(ent, f, "")
                    rows.append(row)
            return rows
        except Exception as exc:
            logger.warning("Milvus search failed: %s", exc)
            return []
