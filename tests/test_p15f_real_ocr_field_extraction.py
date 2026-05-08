from pathlib import Path

from app.core.config import settings
from app.graph.nodes.execute_action import execute_action, format_document_extraction_result
from app.schemas.document_extraction import DocumentExtractionInput
from app.services.ocr.structured_extraction import run_document_extraction


def _load_fixture_text() -> str:
    fixture = Path(__file__).parent / "fixtures" / "ocr" / "p15e_real_invoice_raw_text.txt"
    return fixture.read_text(encoding="utf-8")


def test_p15f_invoice_fields_from_real_ocr_text(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_DOCUMENT_STRUCTURED_EXTRACTION", True)
    monkeypatch.setattr(settings, "DOCUMENT_EXTRACTION_PROVIDER", "rule")
    result = run_document_extraction(
        DocumentExtractionInput(
            document_id="p15f-doc-001",
            document_type="invoice",
            raw_text=_load_fixture_text(),
            ocr_confidence=0.93,
            ocr_provider="paddle",
            hint_document_type="invoice",
            ocr_fallback_used=False,
        )
    )
    values = {field.name: field.value for field in result.fields}
    total_amount_field = next(field for field in result.fields if field.name == "total_amount")
    assert result.status == "succeeded"
    assert result.extractor == "rule_v2"
    assert result.extraction_profile == "cn_vat_invoice"
    assert values.get("invoice_number") == "24412000000050936591"
    assert values.get("invoice_date") == "2024-04-07"
    assert values.get("buyer_name") == "深圳市星河贸易有限公司"
    assert values.get("seller_name") == "广州市示例供应链有限公司"
    assert values.get("total_amount") == "105.00"
    assert values.get("amount_without_tax") == "100.00"
    assert values.get("tax_amount") == "5.00"
    assert values.get("currency") == "CNY"
    assert total_amount_field.needs_review is False
    assert result.amount_candidates_count > 1
    assert result.candidate_fields_count > 0


def test_p15f_date_normalization_variants(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_DOCUMENT_STRUCTURED_EXTRACTION", True)
    monkeypatch.setattr(settings, "DOCUMENT_EXTRACTION_PROVIDER", "rule")
    result = run_document_extraction(
        DocumentExtractionInput(
            document_id="p15f-doc-002",
            document_type="invoice",
            raw_text="发票号码: 223344556677\n开票日期: 2024/04/07\n购买方名称: 深圳测试采购有限公司\n价税合计(小写) ￥1,205.10",
            ocr_confidence=0.95,
            ocr_provider="paddle",
            hint_document_type="invoice",
            ocr_fallback_used=False,
        )
    )
    values = {field.name: field.value for field in result.fields}
    assert values.get("invoice_date") == "2024-04-07"
    assert values.get("total_amount") == "1205.10"


def test_p15f_missing_fields_and_reasons(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_DOCUMENT_STRUCTURED_EXTRACTION", True)
    monkeypatch.setattr(settings, "DOCUMENT_EXTRACTION_PROVIDER", "rule")
    result = run_document_extraction(
        DocumentExtractionInput(
            document_id="p15f-doc-003",
            document_type="invoice",
            raw_text="增值税电子普通发票\n发票号码: ABC123456789\n价税合计(小写) ￥88.00",
            ocr_confidence=0.9,
            ocr_provider="paddle",
            hint_document_type="invoice",
            ocr_fallback_used=False,
        )
    )
    assert "invoice_date" in result.missing_fields
    assert "buyer_name" in result.missing_fields
    assert result.missing_reasons.get("invoice_date")
    assert result.missing_reasons.get("buyer_name")
    assert result.needs_manual_review is True


def test_p15f_amount_candidate_ambiguity_sets_review(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_DOCUMENT_STRUCTURED_EXTRACTION", True)
    monkeypatch.setattr(settings, "DOCUMENT_EXTRACTION_PROVIDER", "rule")
    raw_text = (
        "增值税电子普通发票\n"
        "发票号码: 123456789012\n"
        "开票日期: 2024年04月07日\n"
        "购买方名称: 测试买方有限公司\n"
        "合计金额 100.00\n"
        "金额 100.00\n"
        "税额 5.00\n"
    )
    result = run_document_extraction(
        DocumentExtractionInput(
            document_id="p15f-doc-004",
            document_type="invoice",
            raw_text=raw_text,
            ocr_confidence=0.95,
            ocr_provider="paddle",
            hint_document_type="invoice",
            ocr_fallback_used=False,
        )
    )
    total_field = next(field for field in result.fields if field.name == "total_amount")
    assert total_field.needs_review is True
    assert "金额候选不唯一" in total_field.warning
    assert result.needs_manual_review is True


def test_p15f_result_summary_is_human_readable(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_DOCUMENT_STRUCTURED_EXTRACTION", True)
    monkeypatch.setattr(settings, "DOCUMENT_EXTRACTION_PROVIDER", "rule")
    result = run_document_extraction(
        DocumentExtractionInput(
            document_id="p15f-doc-005",
            document_type="invoice",
            raw_text=_load_fixture_text(),
            ocr_confidence=0.93,
            ocr_provider="paddle",
            hint_document_type="invoice",
            ocr_fallback_used=False,
        )
    )
    summary = format_document_extraction_result(result)
    assert "文档类型：发票" in summary
    assert "整体置信度：" in summary
    assert "是否需要人工复核：" in summary
    assert "缺失原因：" in summary
    assert "{" not in summary


def test_p15f_execute_action_summary_and_safe_detail(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_OCR_DOCUMENT_RECOGNIZE", True)
    monkeypatch.setattr(settings, "OCR_DOCUMENT_PROVIDER", "mock")
    monkeypatch.setattr(settings, "ENABLE_DOCUMENT_STRUCTURED_EXTRACTION", True)
    monkeypatch.setattr(settings, "DOCUMENT_EXTRACTION_PROVIDER", "rule")
    logs = []
    monkeypatch.setattr("app.graph.nodes.execute_action.log_step", lambda *args: logs.append(args))

    state = execute_action(
        {
            "task_id": "TASK-P15F-EXEC",
            "intent_code": "document.structured_extract",
            "slots": {
                "document_id": "mock-doc-p15f",
                "file_name": "invoice_sample.png",
                "mime_type": "image/png",
                "file_path": "mock://invoice_sample.png",
                "source": "mock",
                "requested_by": "feishu_user",
                "hint_document_type": "invoice",
            },
        }
    )
    step_details = [item[3] for item in logs if len(item) >= 4 and item[1] == "document_extraction_succeeded"]
    assert state["status"] == "succeeded"
    assert state["parsed_result"]["formal_write"] is False
    assert state.get("rpa_runner") == "none"
    assert "{" not in state["result_summary"]
    assert "文档类型" in state["result_summary"]
    assert "缺失字段" in state["result_summary"]
    assert "提醒" in state["result_summary"]
    assert step_details
    assert "extractor=rule_v2" in step_details[-1]
    assert "extraction_profile=" in step_details[-1]
    assert "raw_text" not in step_details[-1]
