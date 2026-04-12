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
        "text": "【RAG原始改价规则命中测试】当用户发起修改 SKU A001 价格到 48.8 这类改价请求时，应在确认前追加价格规则与风险提示，但不改变当前 mock 执行结果。",
        "use_case": "rule_augment",
        "category": "rule",
        "intent_hint": "product.update_price",
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