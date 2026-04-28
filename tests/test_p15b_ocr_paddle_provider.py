from app.core.config import settings
from app.schemas.ocr_document import OCRDocumentInput
from app.services.ocr.document_ocr import run_document_ocr
from app.services.ocr.providers import PaddleOCRProviderError


def _build_input() -> OCRDocumentInput:
    return OCRDocumentInput(
        document_id="mock-doc-p15b",
        file_name="invoice_sample.png",
        mime_type="image/png",
        file_path="mock://invoice_sample.png",
        source="mock",
        requested_by="feishu_user",
        hint_document_type="invoice",
    )


def test_p15b_mock_provider_keeps_p15a_behavior(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_OCR_DOCUMENT_RECOGNIZE", True)
    monkeypatch.setattr(settings, "OCR_DOCUMENT_PROVIDER", "mock")

    result = run_document_ocr(_build_input())

    assert result.status == "succeeded"
    assert result.provider == "mock"
    assert result.fallback_used is False
    assert result.fallback_reason == ""
    assert result.blocks


def test_p15b_paddle_disabled_fallbacks_to_mock(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_OCR_DOCUMENT_RECOGNIZE", True)
    monkeypatch.setattr(settings, "OCR_DOCUMENT_PROVIDER", "paddle")
    monkeypatch.setattr(settings, "OCR_PADDLE_ENABLED", False)

    result = run_document_ocr(_build_input())

    assert result.status == "succeeded"
    assert result.provider == "mock"
    assert result.fallback_used is True
    assert result.fallback_reason == "paddle_disabled"
    assert "paddle_provider_disabled" in result.error


def test_p15b_paddle_not_installed_fallbacks_to_mock(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "ENABLE_OCR_DOCUMENT_RECOGNIZE", True)
    monkeypatch.setattr(settings, "OCR_DOCUMENT_PROVIDER", "paddle")
    monkeypatch.setattr(settings, "OCR_PADDLE_ENABLED", True)
    monkeypatch.setattr(
        "app.services.ocr.providers.paddle_provider._load_paddle_ocr_class",
        lambda: (_ for _ in ()).throw(PaddleOCRProviderError("paddleocr_not_installed", "paddleocr_not_installed")),
    )

    sample = _build_input()
    sample.file_path = str(tmp_path / "sample.png")
    (tmp_path / "sample.png").write_bytes(b"fake")
    result = run_document_ocr(sample)

    assert result.status == "succeeded"
    assert result.provider == "mock"
    assert result.fallback_used is True
    assert result.fallback_reason == "paddleocr_not_installed"
    assert result.error == "paddleocr_not_installed"


def test_p15b_unsupported_provider_fallbacks_to_mock(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_OCR_DOCUMENT_RECOGNIZE", True)
    monkeypatch.setattr(settings, "OCR_DOCUMENT_PROVIDER", "unsupported")

    result = run_document_ocr(_build_input())

    assert result.status == "succeeded"
    assert result.provider == "mock"
    assert result.fallback_used is True
    assert result.fallback_reason == "unsupported_provider"
    assert "Unsupported OCR_DOCUMENT_PROVIDER" in result.error


def test_p15b_output_still_matches_ocr_document_output_shape(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_OCR_DOCUMENT_RECOGNIZE", True)
    monkeypatch.setattr(settings, "OCR_DOCUMENT_PROVIDER", "paddle")
    monkeypatch.setattr(settings, "OCR_PADDLE_ENABLED", False)

    result = run_document_ocr(_build_input())

    assert result.status
    assert result.document_type
    assert isinstance(result.raw_text, str)
    assert isinstance(result.confidence, float)
    assert result.provider
    assert isinstance(result.blocks, list)
    assert isinstance(result.needs_manual_review, bool)
    assert isinstance(result.warnings, list)
    assert isinstance(result.fallback_used, bool)
    assert isinstance(result.error, str)
