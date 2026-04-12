import sys
from pathlib import Path

from pymilvus import connections, Collection

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings
from app.rag.embedding import embed_text

COL = settings.MILVUS_COLLECTION_NAME
DIM = settings.RAG_EMBEDDING_DIM

connections.connect(
    alias="default",
    host=settings.MILVUS_HOST,
    port=str(settings.MILVUS_PORT),
)

collection = Collection(COL)

docs = [
    {
        "text": "【RAG失败解释测试】当任务执行失败、确认目标不存在或命令无法处理时，应补充失败原因、排查建议和 FAQ 参考。",
        "use_case": "failure_explanation",
        "category": "error_resolution",
        "intent_hint": "unknown",
    }
]

rows = [
    [d["text"] for d in docs],
    [d["use_case"] for d in docs],
    [d["category"] for d in docs],
    [d["intent_hint"] for d in docs],
    [embed_text(d["text"], DIM) for d in docs],
]

collection.insert(rows)
collection.flush()
collection.load()

print("inserted =", len(docs))