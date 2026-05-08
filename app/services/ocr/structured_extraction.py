from __future__ import annotations

import re

from app.core.config import settings
from app.schemas.document_extraction import (
    DocumentExtractionInput,
    DocumentExtractionOutput,
    ExtractedField,
)
from app.services.ocr.invoice_field_extractor import (
    extract_amount_candidates,
    extract_invoice_date,
    extract_invoice_number,
    extract_named_party,
    normalize_ocr_text,
    select_best_total_amount,
)

_MANUAL_REVIEW_NOTICE = "当前结果来自 OCR 识别与规则抽取，仅供初步整理，正式使用前请人工确认。"
_EXTRACTOR_NAME = "rule_v2"
_EXTRACTION_PROFILE_INVOICE = "cn_vat_invoice"
_SUPPORTED_EXTRACTORS = {"rule", "rule_v2"}
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
    return normalize_ocr_text(raw_text)


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


def _extract_invoice_fields(
    text: str,
) -> tuple[list[ExtractedField], list[str], dict[str, str], int, int]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    fields: list[ExtractedField] = []
    missing_fields: list[str] = []
    missing_reasons: dict[str, str] = {}

    invoice_number, number_conf = extract_invoice_number(lines)
    if invoice_number:
        fields.append(
            ExtractedField(
                name="invoice_number",
                label="发票号码",
                value=invoice_number,
                confidence=number_conf,
                source=f"{_EXTRACTOR_NAME}:invoice_number",
                needs_review=number_conf < 0.85,
                warning="" if number_conf >= 0.85 else "发票号码置信度偏低，建议人工复核。",
            )
        )
    else:
        missing_fields.append("invoice_number")
        missing_reasons["invoice_number"] = "未找到稳定的发票号码模式"

    invoice_date, date_conf = extract_invoice_date(lines)
    if invoice_date:
        fields.append(
            ExtractedField(
                name="invoice_date",
                label="开票日期",
                value=invoice_date,
                confidence=date_conf,
                source=f"{_EXTRACTOR_NAME}:invoice_date",
                needs_review=date_conf < 0.85,
                warning="" if date_conf >= 0.85 else "开票日期由弱规则提取，建议人工复核。",
            )
        )
    else:
        missing_fields.append("invoice_date")
        missing_reasons["invoice_date"] = "未找到开票日期或日期文本 OCR 不完整"

    buyer_name, buyer_conf = extract_named_party(lines, party="buyer")
    if buyer_name:
        fields.append(
            ExtractedField(
                name="buyer_name",
                label="购买方",
                value=buyer_name,
                confidence=buyer_conf,
                source=f"{_EXTRACTOR_NAME}:buyer_name",
                needs_review=buyer_conf < 0.82,
                warning="" if buyer_conf >= 0.82 else "购买方名称识别不稳定，建议人工复核。",
            )
        )
    else:
        missing_fields.append("buyer_name")
        missing_reasons["buyer_name"] = "未找到购买方名称或名称行 OCR 不完整"

    seller_name, seller_conf = extract_named_party(lines, party="seller")
    if seller_name:
        fields.append(
            ExtractedField(
                name="seller_name",
                label="销售方",
                value=seller_name,
                confidence=seller_conf,
                source=f"{_EXTRACTOR_NAME}:seller_name",
                needs_review=seller_conf < 0.82,
                warning="" if seller_conf >= 0.82 else "销售方名称识别不稳定，建议人工复核。",
            )
        )
    else:
        missing_fields.append("seller_name")
        missing_reasons["seller_name"] = "未找到销售方名称或名称行 OCR 不完整"

    amount_candidates = extract_amount_candidates(lines)
    total_amount, amount_conf, amount_review, amount_warning = select_best_total_amount(amount_candidates)
    if total_amount:
        fields.append(
            ExtractedField(
                name="total_amount",
                label="价税合计",
                value=total_amount,
                confidence=amount_conf,
                source=f"{_EXTRACTOR_NAME}:amount_candidate_scoring",
                needs_review=amount_review,
                warning=amount_warning,
            )
        )
    else:
        missing_fields.append("total_amount")
        missing_reasons["total_amount"] = "未找到可用金额候选"

    amount_without_tax = _extract_with_patterns(
        text=text,
        patterns=(
            r"(?:不含税金额|金额合计)\s*:?\s*([0-9]+(?:\.[0-9]{1,2})?)",
            r"金额\s*([0-9]+(?:\.[0-9]{1,2})?)\s*税率",
            r"金额\s*([0-9]+(?:\.[0-9]{1,2})?)\s*税额",
        ),
        label="不含税金额",
        name="amount_without_tax",
    )
    if amount_without_tax:
        fields.append(amount_without_tax)

    tax_amount = _extract_with_patterns(
        text=text,
        patterns=(r"(?:税额|税)\s*:?\s*([0-9]+(?:\.[0-9]{1,2})?)",),
        label="税额",
        name="tax_amount",
    )
    if tax_amount:
        fields.append(tax_amount)

    fields.append(
        ExtractedField(
            name="currency",
            label="币种",
            value="CNY",
            confidence=0.8,
            source=f"{_EXTRACTOR_NAME}:currency_default",
            needs_review=False,
            warning="",
        )
    )
    return fields, missing_fields, missing_reasons, len(lines), len(amount_candidates)


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
    if provider not in _SUPPORTED_EXTRACTORS:
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
    missing_reasons: dict[str, str] = {}
    extraction_profile = ""
    candidate_fields_count = 0
    amount_candidates_count = 0

    if document_type == "invoice":
        (
            fields,
            missing_fields,
            missing_reasons,
            candidate_fields_count,
            amount_candidates_count,
        ) = _extract_invoice_fields(text)
        extraction_profile = _EXTRACTION_PROFILE_INVOICE
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
        missing_reasons=missing_reasons,
        needs_manual_review=needs_manual_review,
        warnings=warnings,
        fallback_used=bool(extraction_input.ocr_fallback_used),
        error="",
        extractor=_EXTRACTOR_NAME,
        extraction_profile=extraction_profile,
        candidate_fields_count=candidate_fields_count,
        amount_candidates_count=amount_candidates_count,
    )
