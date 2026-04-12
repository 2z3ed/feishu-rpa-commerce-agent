import sys
from pathlib import Path

from pymilvus import connections, utility, FieldSchema, CollectionSchema, DataType, Collection

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings
from app.rag.embedding import embed_text


COL = settings.MILVUS_COLLECTION_NAME
DIM = settings.RAG_EMBEDDING_DIM


def main() -> None:
    print("seed script start")
    print("COL =", COL)
    print("DIM =", DIM)
    print("MILVUS =", settings.MILVUS_HOST, settings.MILVUS_PORT)

    connections.connect(
        alias="default",
        host=settings.MILVUS_HOST,
        port=str(settings.MILVUS_PORT),
    )
    print("milvus connected")

    if not utility.has_collection(COL):
        print("collection not exists, creating...")
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=4096),
            FieldSchema(name="use_case", dtype=DataType.VARCHAR, max_length=128),
            FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=128),
            FieldSchema(name="intent_hint", dtype=DataType.VARCHAR, max_length=128),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=DIM),
        ]
        schema = CollectionSchema(fields=fields, description="feishu rag manual validation")
        collection = Collection(name=COL, schema=schema)
        index_params = {
            "index_type": "FLAT",
            "metric_type": "IP",
            "params": {},
        }
        collection.create_index(field_name="embedding", index_params=index_params)
    else:
        print("collection exists, loading...")
        collection = Collection(COL)

    docs = [
        {
            "text": "【RAG命令解释测试】当用户查询 SKU 状态时，可结合 SOP 或 FAQ 补充解释，但不改变原有 intent 解析结果。",
            "use_case": "command_interpretation",
            "category": "faq",
            "intent_hint": "product.query_sku_status",
        },
        {
            "text": "【RAG规则增强测试】改价前应检查价格规则、确认前置条件，并追加规则说明，但不改变当前 mock 执行结果。",
            "use_case": "rule_augment",
            "category": "rule",
            "intent_hint": "product.update_price",
        },
        {
            "text": "【RAG失败解释测试】当系统失败或 unknown intent 时，应返回失败原因、SOP、FAQ 或 error_resolution 参考信息。",
            "use_case": "failure_explanation",
            "category": "error_resolution",
            "intent_hint": "unknown",
        },
    ]

    rows = [
        [d["text"] for d in docs],
        [d["use_case"] for d in docs],
        [d["category"] for d in docs],
        [d["intent_hint"] for d in docs],
        [embed_text(d["text"], DIM) for d in docs],
    ]

    print("inserting rows...")
    collection.insert(rows)
    collection.flush()
    collection.load()

    print("collection =", COL)
    print("inserted =", len(docs))


if __name__ == "__main__":
    main()