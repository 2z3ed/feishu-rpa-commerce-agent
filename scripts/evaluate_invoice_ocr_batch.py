from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings
from app.schemas.document_extraction import DocumentExtractionInput
from app.schemas.ocr_document import OCRDocumentInput
from app.services.ocr.document_ocr import run_document_ocr
from app.services.ocr.structured_extraction import run_document_extraction

DEFAULT_INPUT_DIR = "data/ocr_samples/hf_chinese_invoice_20"
DEFAULT_OUTPUT_ROOT = "data/ocr_eval_runs"
DEFAULT_PROVIDER = "paddle"
DEFAULT_SNIPPET_LIMIT = 200
_IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp")
_KEY_FIELDS = [
    "invoice_number",
    "invoice_date",
    "buyer_name",
    "seller_name",
    "total_amount",
    "tax_amount",
    "amount_without_tax",
]
_DETAIL_HEADERS = [
    "index",
    "image_file",
    "status",
    "provider_actual",
    "fallback_used",
    "fallback_reason",
    "raw_text_length",
    "blocks_count",
    "ocr_confidence",
    "extraction_status",
    "document_type",
    "overall_confidence",
    "needs_manual_review",
    "missing_fields",
    "invoice_number",
    "invoice_date",
    "buyer_name",
    "seller_name",
    "total_amount",
    "tax_amount",
    "amount_without_tax",
    "currency",
    "warnings",
    "error",
    "raw_text_snippet",
    "manual_invoice_number_correct",
    "manual_invoice_date_correct",
    "manual_buyer_name_correct",
    "manual_seller_name_correct",
    "manual_total_amount_correct",
    "manual_note",
]


def discover_images(input_dir: Path, limit: int | None = None) -> list[Path]:
    files = [
        path
        for path in sorted(input_dir.iterdir())
        if path.is_file() and path.suffix.lower() in _IMAGE_SUFFIXES
    ]
    if limit is not None and limit > 0:
        return files[:limit]
    return files


def _field_map(extraction_result) -> dict[str, str]:
    out: dict[str, str] = {}
    for field in extraction_result.fields:
        out[field.name] = str(field.value or "").strip()
    return out


def _raw_text_snippet(raw_text: str, snippet_limit: int = DEFAULT_SNIPPET_LIMIT) -> str:
    clean = " ".join(str(raw_text or "").split())
    return clean[:snippet_limit]


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


def evaluate_batch(
    *,
    image_paths: list[Path],
    provider: str,
    save_raw_text: bool,
    labels_csv: str | None = None,
) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, object]]:
    del labels_csv  # Reserved for future extension.

    settings.ENABLE_OCR_DOCUMENT_RECOGNIZE = True
    settings.OCR_DOCUMENT_PROVIDER = provider
    settings.ENABLE_DOCUMENT_STRUCTURED_EXTRACTION = True
    settings.DOCUMENT_EXTRACTION_PROVIDER = "rule"

    details: list[dict[str, object]] = []
    failed_cases: list[dict[str, object]] = []
    fallback_reason_distribution: Counter[str] = Counter()
    missing_fields_distribution: Counter[str] = Counter()
    error_distribution: Counter[str] = Counter()

    ocr_success_count = 0
    ocr_failed_count = 0
    fallback_used_count = 0
    raw_text_empty_count = 0
    total_raw_text_length = 0
    total_blocks_count = 0
    extraction_success_count = 0
    extraction_failed_count = 0
    needs_review_count = 0
    non_empty_field_count = {key: 0 for key in _KEY_FIELDS}

    for index, image_path in enumerate(image_paths, start=1):
        ocr_output = None
        extraction_output = None
        row_error = ""
        status = "failed"
        stage = "ocr"
        try:
            ocr_output = run_document_ocr(
                OCRDocumentInput(
                    document_id=f"p15f2-{index:03d}",
                    file_name=image_path.name,
                    mime_type="image/png",
                    file_path=str(image_path),
                    source="local_eval",
                    requested_by="p15f2_script",
                    hint_document_type="invoice",
                )
            )
            if ocr_output.status != "succeeded":
                ocr_failed_count += 1
                row_error = str(ocr_output.error or "ocr_failed")
                error_distribution[row_error] += 1
                failed_cases.append(
                    {
                        "image_file": image_path.name,
                        "stage": "ocr",
                        "error": row_error,
                        "fallback_reason": ocr_output.fallback_reason,
                        "provider_actual": ocr_output.provider,
                        "fallback_used": bool(ocr_output.fallback_used),
                    }
                )
            else:
                stage = "extraction"
                ocr_success_count += 1
                raw_text = str(ocr_output.raw_text or "")
                raw_len = len(raw_text)
                total_raw_text_length += raw_len
                total_blocks_count += len(ocr_output.blocks)
                if raw_len == 0:
                    raw_text_empty_count += 1
                if ocr_output.fallback_used:
                    fallback_used_count += 1
                    reason = str(ocr_output.fallback_reason or "unknown")
                    fallback_reason_distribution[reason] += 1

                extraction_output = run_document_extraction(
                    DocumentExtractionInput(
                        document_id=f"p15f2-{index:03d}",
                        document_type="invoice",
                        raw_text=raw_text,
                        ocr_confidence=float(ocr_output.confidence),
                        ocr_provider=ocr_output.provider,
                        hint_document_type="invoice",
                        ocr_fallback_used=bool(ocr_output.fallback_used),
                    )
                )
                if extraction_output.status != "succeeded":
                    extraction_failed_count += 1
                    row_error = str(extraction_output.error or "extraction_failed")
                    error_distribution[row_error] += 1
                    failed_cases.append(
                        {
                            "image_file": image_path.name,
                            "stage": "extraction",
                            "error": row_error,
                            "fallback_reason": ocr_output.fallback_reason,
                            "provider_actual": ocr_output.provider,
                            "fallback_used": bool(ocr_output.fallback_used),
                        }
                    )
                else:
                    extraction_success_count += 1
                    status = "succeeded"
                    if extraction_output.needs_manual_review:
                        needs_review_count += 1
                    for field in extraction_output.missing_fields:
                        missing_fields_distribution[field] += 1
                    value_map = _field_map(extraction_output)
                    for key in _KEY_FIELDS:
                        if value_map.get(key):
                            non_empty_field_count[key] += 1
        except Exception as exc:  # pragma: no cover - defensive branch
            row_error = str(exc)
            error_distribution[row_error] += 1
            failed_cases.append(
                {
                    "image_file": image_path.name,
                    "stage": stage,
                    "error": row_error,
                    "fallback_reason": str(getattr(ocr_output, "fallback_reason", "")),
                    "provider_actual": str(getattr(ocr_output, "provider", provider)),
                    "fallback_used": bool(getattr(ocr_output, "fallback_used", False)),
                }
            )

        value_map = _field_map(extraction_output) if extraction_output and extraction_output.status == "succeeded" else {}
        warnings = extraction_output.warnings if extraction_output else []
        row = {
            "index": index,
            "image_file": image_path.name,
            "status": status,
            "provider_actual": str(getattr(ocr_output, "provider", "")),
            "fallback_used": bool(getattr(ocr_output, "fallback_used", False)),
            "fallback_reason": str(getattr(ocr_output, "fallback_reason", "")),
            "raw_text_length": len(str(getattr(ocr_output, "raw_text", "") or "")),
            "blocks_count": len(getattr(ocr_output, "blocks", []) or []),
            "ocr_confidence": float(getattr(ocr_output, "confidence", 0.0) or 0.0),
            "extraction_status": str(getattr(extraction_output, "status", "failed")),
            "document_type": str(getattr(extraction_output, "document_type", "invoice") or "invoice"),
            "overall_confidence": float(getattr(extraction_output, "overall_confidence", 0.0) or 0.0),
            "needs_manual_review": bool(getattr(extraction_output, "needs_manual_review", True)),
            "missing_fields": "|".join(getattr(extraction_output, "missing_fields", []) or []),
            "invoice_number": value_map.get("invoice_number", ""),
            "invoice_date": value_map.get("invoice_date", ""),
            "buyer_name": value_map.get("buyer_name", ""),
            "seller_name": value_map.get("seller_name", ""),
            "total_amount": value_map.get("total_amount", ""),
            "tax_amount": value_map.get("tax_amount", ""),
            "amount_without_tax": value_map.get("amount_without_tax", ""),
            "currency": value_map.get("currency", ""),
            "warnings": "|".join(str(item) for item in warnings),
            "error": row_error,
            "raw_text_snippet": _raw_text_snippet(str(getattr(ocr_output, "raw_text", "") or "")),
            "manual_invoice_number_correct": "",
            "manual_invoice_date_correct": "",
            "manual_buyer_name_correct": "",
            "manual_seller_name_correct": "",
            "manual_total_amount_correct": "",
            "manual_note": "",
        }
        if save_raw_text:
            row["raw_text"] = str(getattr(ocr_output, "raw_text", "") or "")
        details.append(row)

    total_images = len(image_paths)
    field_non_empty_rate = {
        key: _safe_rate(non_empty_field_count[key], extraction_success_count) for key in _KEY_FIELDS
    }
    summary = {
        "total_images": total_images,
        "processed_images": len(details),
        "ocr_success_count": ocr_success_count,
        "ocr_failed_count": ocr_failed_count,
        "fallback_used_count": fallback_used_count,
        "fallback_rate": _safe_rate(fallback_used_count, ocr_success_count),
        "raw_text_empty_count": raw_text_empty_count,
        "average_raw_text_length": _safe_rate(total_raw_text_length, ocr_success_count),
        "average_blocks_count": _safe_rate(total_blocks_count, ocr_success_count),
        "extraction_success_count": extraction_success_count,
        "extraction_failed_count": extraction_failed_count,
        "needs_review_count": needs_review_count,
        "needs_review_rate": _safe_rate(needs_review_count, extraction_success_count),
        "field_non_empty_rate": field_non_empty_rate,
        "missing_fields_distribution": dict(missing_fields_distribution),
        "fallback_reason_distribution": dict(fallback_reason_distribution),
        "error_distribution": dict(error_distribution),
    }
    return details, failed_cases, summary


def write_outputs(
    *,
    output_root: Path,
    run_id: str,
    details: list[dict[str, object]],
    failed_cases: list[dict[str, object]],
    summary: dict[str, object],
) -> dict[str, Path]:
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    summary_path = run_dir / "summary.json"
    details_path = run_dir / "details.csv"
    failed_cases_path = run_dir / "failed_cases.json"

    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    headers = list(_DETAIL_HEADERS)
    if details and "raw_text" in details[0] and "raw_text" not in headers:
        headers.append("raw_text")
    with details_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in details:
            writer.writerow({key: row.get(key, "") for key in headers})

    with failed_cases_path.open("w", encoding="utf-8") as f:
        json.dump(failed_cases, f, ensure_ascii=False, indent=2)

    return {
        "run_dir": run_dir,
        "summary_path": summary_path,
        "details_path": details_path,
        "failed_cases_path": failed_cases_path,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Batch evaluate invoice OCR + structured extraction.")
    parser.add_argument("--input-dir", default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--provider", default=DEFAULT_PROVIDER)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--labels-csv", default="")
    parser.add_argument("--save-raw-text", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    input_dir = Path(args.input_dir)
    output_root = Path(args.output_root)
    run_id = args.run_id.strip() or datetime.now().strftime("p15f2_%Y%m%d_%H%M%S")
    image_paths = discover_images(input_dir=input_dir, limit=args.limit if args.limit > 0 else None)
    details, failed_cases, summary = evaluate_batch(
        image_paths=image_paths,
        provider=args.provider,
        save_raw_text=args.save_raw_text,
        labels_csv=args.labels_csv or None,
    )
    artifacts = write_outputs(
        output_root=output_root,
        run_id=run_id,
        details=details,
        failed_cases=failed_cases,
        summary=summary,
    )
    print(
        json.dumps(
            {
                "run_dir": str(artifacts["run_dir"]),
                "summary_json": str(artifacts["summary_path"]),
                "details_csv": str(artifacts["details_path"]),
                "failed_cases_json": str(artifacts["failed_cases_path"]),
                "total_images": len(image_paths),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
