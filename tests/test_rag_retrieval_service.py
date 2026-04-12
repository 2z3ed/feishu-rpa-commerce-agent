"""Minimal RAG retrieval and graph hook tests (no Milvus required)."""
from types import SimpleNamespace
import pytest

from app.rag.models import RetrievalHit, RetrievalResult
from app.rag.retrieval_service import (
    check_rag_readiness,
    format_rag_footer,
    retrieve,
)


def test_retrieve_rag_disabled(monkeypatch):
    monkeypatch.setattr("app.rag.retrieval_service.settings", SimpleNamespace(ENABLE_RAG=False))
    r = retrieve(use_case="command_interpretation", query="查价格")
    assert r.fallback is True
    assert r.error == "rag_disabled"
    assert r.hits == []


def test_retrieve_collection_missing(monkeypatch):
    monkeypatch.setattr(
        "app.rag.retrieval_service.settings",
        SimpleNamespace(
            ENABLE_RAG=True,
            MILVUS_COLLECTION_NAME="",
            RAG_EMBEDDING_DIM=128,
            MILVUS_HOST="localhost",
            MILVUS_PORT=19530,
            RAG_TOP_K=5,
            RAG_SCORE_THRESHOLD=0.0,
        ),
    )
    r = retrieve(use_case="command_interpretation", query="x")
    assert r.fallback is True
    assert r.error == "collection_not_configured"


def test_format_rag_footer_empty():
    assert format_rag_footer([]) == ""


def test_format_rag_footer_nonempty():
    hits = [
        RetrievalHit("1", "line one", 0.9, "command_interpretation", "faq", ""),
    ]
    s = format_rag_footer(hits)
    assert "line one" in s
    assert "知识库参考" in s


def test_check_rag_readiness_keys(monkeypatch):
    monkeypatch.setattr(
        "app.rag.retrieval_service.settings",
        SimpleNamespace(
            ENABLE_RAG=False,
            MILVUS_COLLECTION_NAME="kb",
            RAG_EMBEDDING_DIM=128,
            MILVUS_HOST="127.0.0.1",
            MILVUS_PORT=19530,
        ),
    )
    d = check_rag_readiness()
    assert set(d.keys()) >= {
        "rag_enabled",
        "milvus_config_ready",
        "milvus_retrieval_allowed",
        "rag_reason",
    }
    assert d["rag_enabled"] is False


@pytest.mark.parametrize(
    "hits,fallback,error",
    [
        (
            [
                RetrievalHit("1", "doc", 0.99, "command_interpretation", "rule", ""),
            ],
            False,
            None,
        ),
    ],
)
def test_rag_command_node_appends_footer(monkeypatch, hits, fallback, error):
    captured: dict = {}
    monkeypatch.setattr(
        "app.graph.nodes.rag_command_interpretation.log_step", lambda *a, **k: None
    )
    monkeypatch.setattr(
        "app.graph.nodes.rag_command_interpretation.settings",
        SimpleNamespace(
            ENABLE_RAG=True,
            RAG_USE_CASE_ENABLED_COMMAND_INTERPRETATION=True,
            RAG_TOP_K=5,
        ),
    )

    def _fake_retrieve(**kwargs):
        captured.update(kwargs)
        return RetrievalResult(
            use_case="command_interpretation",
            query=kwargs.get("query", "q"),
            hits=hits,
            fallback=fallback,
            error=error,
        )

    monkeypatch.setattr(
        "app.graph.nodes.rag_command_interpretation.retrieve", _fake_retrieve
    )

    from app.graph.nodes.rag_command_interpretation import rag_command_interpretation

    state = {
        "task_id": "TASK-test-rag",
        "intent_code": "product.query_sku_status",
        "normalized_text": "查询 SKU A001 状态",
    }
    out = rag_command_interpretation(state)
    assert "命令说明参考" in (out.get("rag_command_footer") or "")
    assert out.get("rag_command_hits") == 1
    assert out.get("rag_command_fallback") is False
    assert captured.get("intent_hints") == ["product.query_sku_status"]


def test_command_interpretation_update_price_filters_intent_hint_no_cross_query_doc(
    monkeypatch,
):
    """update_price command_interpretation must not use query_sku intent_hint."""
    captured: dict = {}
    monkeypatch.setattr(
        "app.graph.nodes.rag_command_interpretation.log_step", lambda *a, **k: None
    )
    monkeypatch.setattr(
        "app.graph.nodes.rag_command_interpretation.settings",
        SimpleNamespace(
            ENABLE_RAG=True,
            RAG_USE_CASE_ENABLED_COMMAND_INTERPRETATION=True,
            RAG_TOP_K=5,
        ),
    )

    def _fake_retrieve(**kwargs):
        captured.update(kwargs)
        return RetrievalResult(
            use_case="command_interpretation",
            query=kwargs.get("query", ""),
            hits=[
                RetrievalHit(
                    "1",
                    "改价说明",
                    0.9,
                    "command_interpretation",
                    "faq",
                    "product.update_price",
                )
            ],
            fallback=False,
            error=None,
        )

    monkeypatch.setattr(
        "app.graph.nodes.rag_command_interpretation.retrieve", _fake_retrieve
    )

    from app.graph.nodes.rag_command_interpretation import rag_command_interpretation

    state = {
        "task_id": "TASK-up-cmd",
        "intent_code": "product.update_price",
        "normalized_text": "改价 A001 到 48.8",
        "slots": {"sku": "A001", "target_price": 48.8},
    }
    out = rag_command_interpretation(state)
    assert captured.get("intent_hints") == ["product.update_price"]
    assert "查询 SKU 状态" not in captured.get("query", "")
    assert "改价" in captured.get("query", "")
    assert "A001" in captured.get("query", "")
    assert "命令说明参考" in (out.get("rag_command_footer") or "")


def test_command_interpretation_unknown_skipped_for_failure_rag(monkeypatch):
    called: list = []
    monkeypatch.setattr(
        "app.graph.nodes.rag_command_interpretation.log_step", lambda *a, **k: None
    )
    monkeypatch.setattr(
        "app.graph.nodes.rag_command_interpretation.settings",
        SimpleNamespace(
            ENABLE_RAG=True,
            RAG_USE_CASE_ENABLED_COMMAND_INTERPRETATION=True,
            RAG_TOP_K=5,
        ),
    )

    def _fake_retrieve(**kwargs):
        called.append(kwargs)
        return RetrievalResult(
            use_case="command_interpretation",
            query=kwargs.get("query", ""),
            hits=[],
            fallback=False,
            error=None,
        )

    monkeypatch.setattr(
        "app.graph.nodes.rag_command_interpretation.retrieve", _fake_retrieve
    )

    from app.graph.nodes.rag_command_interpretation import rag_command_interpretation

    out = rag_command_interpretation(
        {
            "task_id": "TASK-unk",
            "intent_code": "unknown",
            "normalized_text": "随便聊聊",
        }
    )
    assert called == []
    assert (out.get("rag_command_footer") or "") == ""


def test_retrieve_intent_hint_expr(monkeypatch):
    """Milvus expr includes intent_hint in [...] when intent_hints passed."""
    captured: list[dict] = []

    class _Ad:
        def search(self, **kwargs):
            captured.append(kwargs)
            return []

    monkeypatch.setattr("app.rag.retrieval_service._ADAPTER", _Ad())
    monkeypatch.setattr(
        "app.rag.retrieval_service.settings",
        SimpleNamespace(
            ENABLE_RAG=True,
            MILVUS_COLLECTION_NAME="c1",
            RAG_EMBEDDING_DIM=8,
            MILVUS_HOST="localhost",
            MILVUS_PORT=19530,
            RAG_TOP_K=3,
            RAG_SCORE_THRESHOLD=0.0,
        ),
    )
    retrieve(
        use_case="rule_augment",
        query="q",
        categories=["rule"],
        intent_hints=["product.update_price"],
    )
    assert len(captured) == 1
    expr = captured[0]["expr"]
    assert "intent_hint" in expr
    assert "product.update_price" in expr


def test_rule_augment_update_price_enriches_query_and_filters_intent_hint(monkeypatch):
    captured: dict = {}

    monkeypatch.setattr("app.graph.nodes.rag_rule_augment.log_step", lambda *a, **k: None)
    monkeypatch.setattr(
        "app.graph.nodes.rag_rule_augment.settings",
        SimpleNamespace(
            ENABLE_RAG=True,
            RAG_USE_CASE_ENABLED_RULE_AUGMENT=True,
            RAG_TOP_K=5,
        ),
    )

    def _fake_retrieve(**kw):
        captured.update(kw)
        return RetrievalResult(
            use_case="rule_augment",
            query=kw.get("query", ""),
            hits=[
                RetrievalHit("1", "rule text", 0.5, "rule_augment", "rule", "product.update_price")
            ],
            fallback=False,
            error=None,
        )

    monkeypatch.setattr("app.graph.nodes.rag_rule_augment.retrieve", _fake_retrieve)

    from app.graph.nodes.rag_rule_augment import rag_rule_augment

    state = {
        "task_id": "TASK-rag-up",
        "intent_code": "product.update_price",
        "normalized_text": "改价 A001 到 48.8",
        "slots": {"sku": "A001", "target_price": 48.8},
    }
    out = rag_rule_augment(state)
    q = captured.get("query", "")
    assert "A001" in q and "48.8" in q
    assert "当用户发起修改 SKU A001 价格到 48.8" in q
    assert captured.get("intent_hints") == ["product.update_price"]
    assert "规则与确认说明" in (out.get("rag_rule_footer") or "")


def test_rule_augment_update_price_broad_fallback_drops_confirm_hint(monkeypatch):
    """Strict intent_hint Milvus filter yields 0 rows; broad retrieve + Python filter restores 改价 hits."""
    calls: list = []
    monkeypatch.setattr("app.graph.nodes.rag_rule_augment.log_step", lambda *a, **k: None)
    monkeypatch.setattr(
        "app.graph.nodes.rag_rule_augment.settings",
        SimpleNamespace(
            ENABLE_RAG=True,
            RAG_USE_CASE_ENABLED_RULE_AUGMENT=True,
            RAG_TOP_K=5,
        ),
    )

    def _fake_retrieve(**kw):
        calls.append(kw.get("intent_hints"))
        if len(calls) == 1:
            return RetrievalResult(
                use_case="rule_augment",
                query=kw.get("query", ""),
                hits=[],
                fallback=False,
                error=None,
            )
        return RetrievalResult(
            use_case="rule_augment",
            query=kw.get("query", ""),
            hits=[
                RetrievalHit(
                    "1",
                    "confirm-only",
                    0.99,
                    "rule_augment",
                    "rule",
                    "system.confirm_task",
                ),
                RetrievalHit(
                    "2",
                    "改价规则正文",
                    0.5,
                    "rule_augment",
                    "rule",
                    "product.update_price",
                ),
            ],
            fallback=False,
            error=None,
        )

    monkeypatch.setattr("app.graph.nodes.rag_rule_augment.retrieve", _fake_retrieve)

    from app.graph.nodes.rag_rule_augment import rag_rule_augment

    out = rag_rule_augment(
        {
            "task_id": "TASK-rag-fb",
            "intent_code": "product.update_price",
            "normalized_text": "改价 A001 到 48.8",
            "slots": {"sku": "A001", "target_price": 48.8},
        }
    )
    assert len(calls) == 2
    assert calls[0] == ["product.update_price"]
    assert calls[1] is None
    footer = out.get("rag_rule_footer") or ""
    assert "改价规则正文" in footer
    assert "confirm-only" not in footer


def test_rule_augment_confirm_task_query_unchanged(monkeypatch):
    captured: dict = {}
    monkeypatch.setattr("app.graph.nodes.rag_rule_augment.log_step", lambda *a, **k: None)
    monkeypatch.setattr(
        "app.graph.nodes.rag_rule_augment.settings",
        SimpleNamespace(
            ENABLE_RAG=True,
            RAG_USE_CASE_ENABLED_RULE_AUGMENT=True,
            RAG_TOP_K=5,
        ),
    )

    def _fake_retrieve(**kw):
        captured.update(kw)
        return RetrievalResult(
            use_case="rule_augment",
            query=kw.get("query", ""),
            hits=[
                RetrievalHit("2", "confirm rule", 0.5, "rule_augment", "rule", "")
            ],
            fallback=False,
            error=None,
        )

    monkeypatch.setattr("app.graph.nodes.rag_rule_augment.retrieve", _fake_retrieve)

    from app.graph.nodes.rag_rule_augment import rag_rule_augment

    msg = "确认执行 TASK-20260411-ABCDEF"
    state = {
        "task_id": "TASK-rag-cf",
        "intent_code": "system.confirm_task",
        "normalized_text": msg,
        "slots": {"task_id": "TASK-20260411-ABCDEF"},
    }
    rag_rule_augment(state)
    assert captured.get("query") == msg
    assert captured.get("intent_hints") is None


def test_build_failure_explanation_query_contains_seed_context():
    from app.graph.nodes.finalize_result import _build_failure_explanation_query

    q = _build_failure_explanation_query(
        {
            "intent_code": "unknown",
            "error_message": "Unknown intent",
            "normalized_text": "你好",
        }
    )
    assert "任务执行失败" in q
    assert "命令无法处理" in q
    assert "unknown intent" in q
    assert "你好" in q
    assert "FAQ" in q


def test_retrieve_failure_explanation_strict_then_broad(monkeypatch):
    calls: list = []
    monkeypatch.setattr(
        "app.rag.retrieval_service.settings",
        SimpleNamespace(
            ENABLE_RAG=True,
            MILVUS_COLLECTION_NAME="c",
            RAG_EMBEDDING_DIM=8,
            MILVUS_HOST="localhost",
            MILVUS_PORT=19530,
            RAG_TOP_K=5,
            RAG_SCORE_THRESHOLD=0.0,
        ),
    )

    class _Ad:
        def search(self, **kwargs):
            return []

    monkeypatch.setattr("app.rag.retrieval_service._ADAPTER", _Ad())

    def fake_retrieve(**kw):
        calls.append(kw.get("intent_hints"))
        if len(calls) == 1:
            return RetrievalResult(
                use_case="failure_explanation",
                query=kw.get("query", ""),
                hits=[],
                fallback=False,
                error=None,
            )
        return RetrievalResult(
            use_case="failure_explanation",
            query=kw.get("query", ""),
            hits=[
                RetrievalHit(
                    "1",
                    "【RAG失败解释测试】",
                    0.9,
                    "failure_explanation",
                    "error_resolution",
                    "unknown",
                )
            ],
            fallback=False,
            error=None,
        )

    monkeypatch.setattr("app.graph.nodes.finalize_result.retrieve", fake_retrieve)

    from app.graph.nodes.finalize_result import _retrieve_failure_explanation

    r = _retrieve_failure_explanation(query="q")
    assert len(r.hits) == 1
    assert len(calls) == 2
    assert calls[0] == ["unknown"]
    assert calls[1] is None


def test_environment_readiness_includes_rag():
    """GET /internal/readiness/environment includes RAG keys."""
    from fastapi.testclient import TestClient

    from app.main import app

    c = TestClient(app)
    r = c.get("/api/v1/internal/readiness/environment")
    assert r.status_code == 200
    body = r.json()
    assert "rag_enabled" in body
    assert "milvus_retrieval_allowed" in body
    assert "rag_reason" in body
