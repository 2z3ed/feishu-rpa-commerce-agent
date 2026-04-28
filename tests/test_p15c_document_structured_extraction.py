from app.core.config import settings
from app.graph.nodes.execute_action import execute_action
from app.graph.nodes.resolve_intent import resolve_intent
from app.schemas.document_extraction import DocumentExtractionInput
from app.services.ocr.structured_extraction import run_document_extraction


def test_p15c_resolve_structured_extract_intent():
    out = resolve_intent(
        {
            "task_id": "TASK-P15C-INTENT",
            "normalized_text": "提取这张发票字段",
            "user_open_id": "ou_demo",
        }
    )
    assert out["intent_code"] == "document.structured_extract"
    assert out["slots"]["document_id"].startswith("mock-doc-")
    assert out["slots"]["hint_document_type"] == "invoice"


def test_p15c_invoice_rule_extraction_fields(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_DOCUMENT_STRUCTURED_EXTRACTION", True)
    monkeypatch.setattr(settings, "DOCUMENT_EXTRACTION_PROVIDER", "rule")
    result = run_document_extraction(
        DocumentExtractionInput(
            document_id="mock-doc-001",
            document_type="invoice",
            raw_text=(
                "发票号码：12345678\n"
                "开票日期：2026-04-27\n"
                "购买方：测试公司\n"
                "金额：128.50"
            ),
            ocr_confidence=0.92,
            ocr_provider="mock",
            hint_document_type="invoice",
            ocr_fallback_used=False,
        )
    )
    values = {field.name: field.value for field in result.fields}
    assert result.status == "succeeded"
    assert values.get("invoice_number") == "12345678"
    assert values.get("invoice_date") == "2026-04-27"
    assert values.get("buyer_name") == "测试公司"
    assert values.get("total_amount") == "128.50"
    assert result.needs_manual_review is True


def test_p15c_missing_fields_and_confidence(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_DOCUMENT_STRUCTURED_EXTRACTION", True)
    monkeypatch.setattr(settings, "DOCUMENT_EXTRACTION_PROVIDER", "rule")
    result = run_document_extraction(
        DocumentExtractionInput(
            document_id="mock-doc-002",
            document_type="invoice",
            raw_text="发票号码：12345678",
            ocr_confidence=0.92,
            ocr_provider="mock",
            hint_document_type="invoice",
            ocr_fallback_used=True,
        )
    )
    assert "invoice_date" in result.missing_fields
    assert "buyer_name" in result.missing_fields
    assert "total_amount" in result.missing_fields
    assert result.overall_confidence <= 0.9
    assert result.needs_manual_review is True


def test_p15c_receipt_rule_extraction(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_DOCUMENT_STRUCTURED_EXTRACTION", True)
    monkeypatch.setattr(settings, "DOCUMENT_EXTRACTION_PROVIDER", "rule")
    result = run_document_extraction(
        DocumentExtractionInput(
            document_id="mock-doc-004",
            document_type="receipt",
            raw_text="商户：便利店\n日期：2026-04-27\n总金额：32.80",
            ocr_confidence=0.9,
            ocr_provider="mock",
            hint_document_type="receipt",
            ocr_fallback_used=False,
        )
    )
    values = {field.name: field.value for field in result.fields}
    assert result.status == "succeeded"
    assert values.get("merchant_name") == "便利店"
    assert values.get("receipt_date") == "2026-04-27"
    assert values.get("total_amount") == "32.80"
    assert values.get("currency") == "CNY"


def test_p15c_execute_action_summary_and_steps(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_OCR_DOCUMENT_RECOGNIZE", True)
    monkeypatch.setattr(settings, "OCR_DOCUMENT_PROVIDER", "mock")
    monkeypatch.setattr(settings, "ENABLE_DOCUMENT_STRUCTURED_EXTRACTION", True)
    monkeypatch.setattr(settings, "DOCUMENT_EXTRACTION_PROVIDER", "rule")
    logs = []
    monkeypatch.setattr("app.graph.nodes.execute_action.log_step", lambda *args: logs.append(args))

    state = execute_action(
        {
            "task_id": "TASK-P15C-EXEC",
            "intent_code": "document.structured_extract",
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

    codes = [item[1] for item in logs]
    assert state["status"] == "succeeded"
    assert state["capability"] == "document.structured_extract"
    assert state["execution_backend"] == "document_extraction_service"
    assert "document_extraction_started" in codes
    assert "document_extraction_succeeded" in codes
    assert state["parsed_result"]["formal_write"] is False
    assert state.get("rpa_runner") == "none"
    assert "{" not in state["result_summary"]
    assert "文档类型" in state["result_summary"]
    assert "人工确认" in state["result_summary"]

