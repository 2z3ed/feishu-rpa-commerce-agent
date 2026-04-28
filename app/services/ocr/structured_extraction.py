from __future__ import annotations

import re

from app.core.config import settings
from app.schemas.document_extraction import (
    DocumentExtractionInput,
    DocumentExtractionOutput,
    ExtractedField,
)

_MANUAL_REVIEW_NOTICE = "当前结果来自 OCR 识别与规则抽取，仅供初步整理，正式使用前请人工确认。"
_EXTRACTOR_NAME = "rule"
_HIGH_CONFIDENCE = 0.90
_LOW_CONFIDENCE = 0.70


def _pick_document_type(extraction_input: DocumentExtractionInput) -> str:
    doc_type = str(extraction_input.document_type or "").strip().lower()
    if doc_type in {"invoice", "receipt"}:
        return doc_type
    hint = str(extraction_input.hint_document_type or "").strip().lower()
    if hint in {"invoice", "receipt"}:
        return hint
    return "unknown"


def _normalized_text(raw_text: str) -> str:
    return str(raw_text or "").strip()


def _extract_with_patterns(
    *,
    text: str,
    patterns: tuple[str, ...],
    label: str,
    name: str,
    fallback_patterns: tuple[str, ...] = (),
) -> ExtractedField | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = str(match.group(1) or "").strip()
            if value:
                return ExtractedField(
                    name=name,
                    label=label,
                    value=value,
                    confidence=_HIGH_CONFIDENCE,
                    source=_EXTRACTOR_NAME,
                    needs_review=False,
                    warning="",
                )
    for pattern in fallback_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = str(match.group(1) or "").strip()
            if value:
                return ExtractedField(
                    name=name,
                    label=label,
                    value=value,
                    confidence=_LOW_CONFIDENCE,
                    source=_EXTRACTOR_NAME,
                    needs_review=True,
                    warning="字段由模糊规则提取，建议人工复核。",
                )
    return None


def _extract_invoice_fields(text: str) -> tuple[list[ExtractedField], list[str]]:
    specs = (
        (
            "invoice_number",
            "发票号码",
            (r"(?:发票号码|发票号)[:：]\s*([A-Za-z0-9-]+)",),
            (r"号码[:：]?\s*([A-Za-z0-9-]+)",),
        ),
        (
            "invoice_date",
            "开票日期",
            (r"(?:开票日期|日期)[:：]\s*([0-9]{4}[-/.][0-9]{1,2}[-/.][0-9]{1,2})",),
            (r"([0-9]{4}[-/.][0-9]{1,2}[-/.][0-9]{1,2})",),
        ),
        (
            "buyer_name",
            "购买方",
            (r"(?:购买方|购方名称|购买方名称)[:：]\s*([^\n]+)",),
            (),
        ),
        (
            "total_amount",
            "金额",
            (r"(?:价税合计|合计|总金额|金额)[:：]?\s*([0-9]+(?:\.[0-9]{1,2})?)",),
            (r"([0-9]+(?:\.[0-9]{1,2}))",),
        ),
        (
            "currency",
            "币种",
            (r"(?:币种|currency)[:：]\s*([A-Za-z]{3})",),
            (),
        ),
    )
    fields: list[ExtractedField] = []
    missing_fields: list[str] = []
    for name, label, strict_patterns, fuzzy_patterns in specs:
        field = _extract_with_patterns(
            text=text,
            patterns=strict_patterns,
            fallback_patterns=fuzzy_patterns,
            name=name,
            label=label,
        )
        if field is None:
            if name == "currency":
                fields.append(
                    ExtractedField(
                        name="currency",
                        label="币种",
                        value="CNY",
                        confidence=_LOW_CONFIDENCE,
                        source=_EXTRACTOR_NAME,
                        needs_review=True,
                        warning="未识别到明确币种，默认按 CNY 处理，请人工确认。",
                    )
                )
                continue
            missing_fields.append(name)
            continue
        fields.append(field)
    return fields, missing_fields


def _extract_receipt_fields(text: str) -> tuple[list[ExtractedField], list[str]]:
    specs = (
        (
            "merchant_name",
            "商户名称",
            (r"(?:商户|商家|店铺|门店)[:：]\s*([^\n]+)",),
            (),
        ),
        (
            "receipt_date",
            "小票日期",
            (r"(?:日期|交易时间|时间)[:：]\s*([0-9]{4}[-/.][0-9]{1,2}[-/.][0-9]{1,2})",),
            (r"([0-9]{4}[-/.][0-9]{1,2}[-/.][0-9]{1,2})",),
        ),
        (
            "total_amount",
            "总金额",
            (r"(?:应付|合计|总计|总金额|金额)[:：]?\s*([0-9]+(?:\.[0-9]{1,2})?)",),
            (r"([0-9]+(?:\.[0-9]{1,2}))",),
        ),
        (
            "currency",
            "币种",
            (r"(?:币种|currency)[:：]\s*([A-Za-z]{3})",),
            (),
        ),
    )
    fields: list[ExtractedField] = []
    missing_fields: list[str] = []
    for name, label, strict_patterns, fuzzy_patterns in specs:
        field = _extract_with_patterns(
            text=text,
            patterns=strict_patterns,
            fallback_patterns=fuzzy_patterns,
            name=name,
            label=label,
        )
        if field is None:
            if name == "currency":
                fields.append(
                    ExtractedField(
                        name="currency",
                        label="币种",
                        value="CNY",
                        confidence=_LOW_CONFIDENCE,
                        source=_EXTRACTOR_NAME,
                        needs_review=True,
                        warning="未识别到明确币种，默认按 CNY 处理，请人工确认。",
                    )
                )
                continue
            missing_fields.append(name)
            continue
        fields.append(field)
    return fields, missing_fields


def _compute_overall_confidence(ocr_confidence: float, fields: list[ExtractedField]) -> float:
    if not fields:
        return 0.0
    avg = sum(float(item.confidence) for item in fields) / len(fields)
    return max(0.0, min(1.0, min(float(ocr_confidence), avg)))


def run_document_extraction(extraction_input: DocumentExtractionInput) -> DocumentExtractionOutput:
    provider = str(settings.DOCUMENT_EXTRACTION_PROVIDER or "rule").strip().lower()
    if not settings.ENABLE_DOCUMENT_STRUCTURED_EXTRACTION:
        return DocumentExtractionOutput(
            status="failed",
            document_type=_pick_document_type(extraction_input),
            fields=[],
            overall_confidence=0.0,
            missing_fields=[],
            needs_manual_review=True,
            warnings=["结构化提取功能未开启，请人工确认。", _MANUAL_REVIEW_NOTICE],
            fallback_used=False,
            error="feature_disabled",
            extractor=provider or _EXTRACTOR_NAME,
        )
    if provider != _EXTRACTOR_NAME:
        return DocumentExtractionOutput(
            status="failed",
            document_type=_pick_document_type(extraction_input),
            fields=[],
            overall_confidence=0.0,
            missing_fields=[],
            needs_manual_review=True,
            warnings=["当前仅支持 rule extractor。", _MANUAL_REVIEW_NOTICE],
            fallback_used=False,
            error=f"unsupported_extractor:{provider}",
            extractor=provider,
        )

    text = _normalized_text(extraction_input.raw_text)
    document_type = _pick_document_type(extraction_input)
    warnings: list[str] = []
    fields: list[ExtractedField] = []
    missing_fields: list[str] = []

    if document_type == "invoice":
        fields, missing_fields = _extract_invoice_fields(text)
    elif document_type == "receipt":
        fields, missing_fields = _extract_receipt_fields(text)
    else:
        warnings.append("文档类型未知，未执行完整字段提取。")

    overall_confidence = _compute_overall_confidence(extraction_input.ocr_confidence, fields)
    has_total_amount = any(f.name == "total_amount" and str(f.value or "").strip() for f in fields)
    needs_manual_review = any(
        [
            bool(missing_fields),
            overall_confidence < 0.85,
            document_type == "unknown",
            not has_total_amount,
            str(extraction_input.ocr_provider or "").strip().lower() == "mock",
            bool(extraction_input.ocr_fallback_used),
        ]
    )
    if missing_fields:
        warnings.append("部分关键字段缺失，需要人工确认。")
    if bool(extraction_input.ocr_fallback_used):
        warnings.append("OCR 发生降级，结构化结果需要人工确认。")
    warnings.append(_MANUAL_REVIEW_NOTICE)

    return DocumentExtractionOutput(
        status="succeeded",
        document_type=document_type,
        fields=fields,
        overall_confidence=overall_confidence,
        missing_fields=missing_fields,
        needs_manual_review=needs_manual_review,
        warnings=warnings,
        fallback_used=bool(extraction_input.ocr_fallback_used),
        error="",
        extractor=_EXTRACTOR_NAME,
    )
