from app.core.config import settings
from app.graph.nodes.execute_action import execute_action
from app.graph.nodes.resolve_intent import resolve_intent
from app.schemas.ocr_document import OCRDocumentInput
from app.services.ocr.document_ocr import run_document_ocr


def test_p15a_resolve_ocr_intent():
    out = resolve_intent(
        {
            "task_id": "TASK-P15A-INTENT",
            "normalized_text": "识别这张发票",
            "user_open_id": "ou_demo",
        }
    )
    assert out["intent_code"] == "document.ocr_recognize"
    assert out["slots"]["document_id"].startswith("mock-doc-")
    assert out["slots"]["mime_type"] == "image/png"
    assert out["slots"]["requested_by"] == "ou_demo"


def test_p15a_mock_ocr_service_returns_expected_fields(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_OCR_DOCUMENT_RECOGNIZE", True)
    monkeypatch.setattr(settings, "OCR_DOCUMENT_PROVIDER", "mock")

    result = run_document_ocr(
        OCRDocumentInput(
            document_id="mock-doc-001",
            file_name="invoice_sample.png",
            mime_type="image/png",
            file_path="mock://invoice_sample.png",
            source="mock",
            requested_by="feishu_user",
            hint_document_type="invoice",
        )
    )

    assert result.status == "succeeded"
    assert result.provider == "mock"
    assert result.document_type == "invoice"
    assert result.confidence > 0.8
    assert "发票号码" in result.raw_text
    assert result.needs_manual_review is True
    assert result.blocks


def test_p15a_unsupported_provider_falls_back_to_mock(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_OCR_DOCUMENT_RECOGNIZE", True)
    monkeypatch.setattr(settings, "OCR_DOCUMENT_PROVIDER", "unsupported")

    result = run_document_ocr(
        OCRDocumentInput(
            document_id="mock-doc-002",
            file_name="invoice_sample.png",
            mime_type="image/png",
            file_path="mock://invoice_sample.png",
            source="mock",
            requested_by="feishu_user",
            hint_document_type="invoice",
        )
    )

    assert result.status == "succeeded"
    assert result.provider == "mock"
    assert result.fallback_used is True
    assert "Unsupported OCR_DOCUMENT_PROVIDER" in result.error
    assert any("降级" in warning for warning in result.warnings)


def test_p15a_execute_action_logs_ocr_steps(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_OCR_DOCUMENT_RECOGNIZE", True)
    monkeypatch.setattr(settings, "OCR_DOCUMENT_PROVIDER", "mock")
    logs = []
    monkeypatch.setattr("app.graph.nodes.execute_action.log_step", lambda *args: logs.append(args))

    state = execute_action(
        {
            "task_id": "TASK-P15A-EXEC",
            "intent_code": "document.ocr_recognize",
            "slots": {
                "document_id": "mock-doc-003",
                "file_name": "invoice_sample.png",
                "mime_type": "image/png",
                "file_path": "mock://invoice_sample.png",
                "source": "mock",
                "requested_by": "feishu_user",
                "hint_document_type": "invoice",
            },
        }
    )

    assert state["status"] == "succeeded"
    assert state["capability"] == "document.ocr_recognize"
    assert state["execution_backend"] == "document_ocr_service"
    assert state["provider_id"] == "mock"
    assert "OCR 初步识别" in state["result_summary"]
    assert state["parsed_result"]["raw_text_length"] > 0
    assert state["parsed_result"]["blocks_count"] > 0
    assert "ocr_document_started" in [item[1] for item in logs]
    assert "ocr_document_succeeded" in [item[1] for item in logs]
    assert state.get("rpa_runner") == "none"
    assert "sku" not in state["parsed_result"]


def test_p15a_feature_disabled_fails_gracefully(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_OCR_DOCUMENT_RECOGNIZE", False)
    monkeypatch.setattr(settings, "OCR_DOCUMENT_PROVIDER", "mock")
    logs = []
    monkeypatch.setattr("app.graph.nodes.execute_action.log_step", lambda *args: logs.append(args))

    state = execute_action(
        {
            "task_id": "TASK-P15A-DISABLED",
            "intent_code": "document.ocr_recognize",
            "slots": {
                "document_id": "mock-doc-004",
                "file_name": "invoice_sample.png",
                "mime_type": "image/png",
                "file_path": "mock://invoice_sample.png",
                "source": "mock",
                "requested_by": "feishu_user",
                "hint_document_type": "invoice",
            },
        }
    )

    assert state["status"] == "failed"
    assert state["error_message"] == "feature_disabled"
    assert "OCR 识别暂时失败" in state["result_summary"]
    assert "ocr_document_failed" in [item[1] for item in logs]
