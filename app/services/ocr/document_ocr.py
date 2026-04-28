from __future__ import annotations

from app.core.config import settings
from app.schemas.ocr_document import OCRDocumentInput, OCRDocumentOutput, OCRTextBlock

_MANUAL_REVIEW_WARNING = "当前结果仅为 OCR 初步识别，需人工确认。"


def _build_mock_output(ocr_input: OCRDocumentInput) -> OCRDocumentOutput:
    raw_text = (
        "发票号码：12345678\n"
        "开票日期：2026-04-27\n"
        "购买方：测试公司\n"
        "金额：128.50"
    )
    return OCRDocumentOutput(
        status="succeeded",
        document_type=ocr_input.hint_document_type if ocr_input.hint_document_type in {"invoice", "receipt"} else "invoice",
        raw_text=raw_text,
        confidence=0.92,
        provider="mock",
        blocks=[
            OCRTextBlock(text="发票号码：12345678", confidence=0.95),
            OCRTextBlock(text="开票日期：2026-04-27", confidence=0.94),
            OCRTextBlock(text="购买方：测试公司", confidence=0.91),
            OCRTextBlock(text="金额：128.50", confidence=0.90),
        ],
        needs_manual_review=True,
        warnings=[_MANUAL_REVIEW_WARNING],
        fallback_used=False,
        error="",
    )


def _build_failed_output(provider: str, error: str) -> OCRDocumentOutput:
    return OCRDocumentOutput(
        status="failed",
        document_type="unknown",
        raw_text="",
        confidence=0.0,
        provider=provider or "mock",
        blocks=[],
        needs_manual_review=True,
        warnings=["OCR 识别失败，请人工确认文件内容。"],
        fallback_used=False,
        error=error[:200],
    )


def run_document_ocr(ocr_input: OCRDocumentInput) -> OCRDocumentOutput:
    provider = (settings.OCR_DOCUMENT_PROVIDER or "mock").strip().lower()
    if not settings.ENABLE_OCR_DOCUMENT_RECOGNIZE:
        return _build_failed_output(provider or "mock", "feature_disabled")

    try:
        if provider == "mock":
            return _build_mock_output(ocr_input)
        raise ValueError(f"Unsupported OCR_DOCUMENT_PROVIDER: {provider}")
    except Exception as exc:
        if provider != "mock":
            fallback = _build_mock_output(ocr_input)
            fallback.fallback_used = True
            fallback.warnings.append(
                f"OCR provider {provider or 'unknown'} 不可用，已降级为 mock 结果，请人工确认。"
            )
            fallback.error = str(exc)[:200]
            return fallback
        return _build_failed_output(provider or "mock", str(exc))
