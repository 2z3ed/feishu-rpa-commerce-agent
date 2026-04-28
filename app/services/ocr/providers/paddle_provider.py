from __future__ import annotations

from pathlib import Path

from app.core.config import settings
from app.schemas.ocr_document import OCRDocumentInput, OCRTextBlock


class PaddleOCRProviderError(Exception):
    def __init__(self, reason: str, message: str):
        super().__init__(message)
        self.reason = reason
        self.message = message


def _load_paddle_ocr_class():
    try:
        from paddleocr import PaddleOCR  # type: ignore
    except ImportError as exc:
        raise PaddleOCRProviderError("paddleocr_not_installed", "paddleocr_not_installed") from exc
    return PaddleOCR


def run_paddle_ocr(ocr_input: OCRDocumentInput) -> tuple[str, list[OCRTextBlock], float]:
    if not settings.OCR_PADDLE_ENABLED:
        raise PaddleOCRProviderError("paddle_disabled", "paddle_provider_disabled")

    file_path = str(ocr_input.file_path or "").strip()
    if not file_path or file_path.startswith("mock://"):
        raise PaddleOCRProviderError("file_not_found", "ocr_input_file_not_found")

    path_obj = Path(file_path)
    if not path_obj.exists() or not path_obj.is_file():
        raise PaddleOCRProviderError("file_not_found", "ocr_input_file_not_found")

    paddle_cls = _load_paddle_ocr_class()
    try:
        engine = paddle_cls(
            use_angle_cls=True,
            lang=settings.OCR_PADDLE_LANG or "ch",
            use_gpu=bool(settings.OCR_PADDLE_USE_GPU),
        )
        result = engine.ocr(str(path_obj), cls=True)
    except PaddleOCRProviderError:
        raise
    except Exception as exc:
        raise PaddleOCRProviderError("provider_error", f"paddle_inference_failed:{exc}") from exc

    lines: list[OCRTextBlock] = []
    for page in result or []:
        if not isinstance(page, list):
            continue
        for item in page:
            if not isinstance(item, (list, tuple)) or len(item) < 2:
                continue
            line_info = item[1]
            if not isinstance(line_info, (list, tuple)) or len(line_info) < 2:
                continue
            text = str(line_info[0] or "").strip()
            if not text:
                continue
            try:
                conf = float(line_info[1])
            except Exception:
                conf = 0.0
            conf = max(0.0, min(1.0, conf))
            lines.append(OCRTextBlock(text=text, confidence=conf))

    raw_text = "\n".join(block.text for block in lines)
    if lines:
        confidence = sum(block.confidence for block in lines) / len(lines)
    else:
        confidence = 0.0
    return raw_text, lines, round(confidence, 4)
