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


def _create_paddle_engine():
    """
    Initialize PaddleOCR with a minimal, version-tolerant parameter set.

    - Do NOT pass deprecated `use_gpu` (PaddleOCR 3.5.0 no longer accepts it).
    - Prefer CPU (`device='cpu'`) when OCR_PADDLE_USE_GPU is false.
    - When OCR_PADDLE_USE_GPU is true, try `device='gpu'` first, then fall back to CPU/default.
    - If all candidates fail, raise a PaddleOCRProviderError with a clear reason:
      * paddle_backend_not_installed: paddlepaddle backend not available
      * paddle_init_failed: other initialization errors
    """
    paddle_cls = _load_paddle_ocr_class()
    lang = settings.OCR_PADDLE_LANG or "ch"

    base_kwargs: dict = {"lang": lang}
    candidates: list[dict] = []

    if bool(settings.OCR_PADDLE_USE_GPU):
        candidates.append({**base_kwargs, "device": "gpu"})
        candidates.append({**base_kwargs, "device": "cpu"})
        candidates.append(base_kwargs)
    else:
        candidates.append({**base_kwargs, "device": "cpu"})
        candidates.append(base_kwargs)

    last_exc: Exception | None = None
    for kw in candidates:
        try:
            return paddle_cls(**kw)
        except Exception as exc:  # pragma: no cover - exercised via integration/fallback tests
            last_exc = exc

    message = str(last_exc) if last_exc else "paddle_ocr_init_failed"
    lowered = message.lower()
    if "paddlepaddle is not installed" in lowered:
        reason = "paddle_backend_not_installed"
    else:
        reason = "paddle_init_failed"
    raise PaddleOCRProviderError(reason, message[:200])


def _resolve_file_path(file_path: str) -> Path:
    """
    Resolve evidence file path to something PaddleOCR can read.

    - `feishu_file_download` returns a relative path computed from os.getcwd().
    - Worker CWD may differ, so we attempt to resolve relative paths against repo root.
    """
    raw = str(file_path or "").strip()
    if not raw:
        return Path(raw)

    p = Path(raw)
    if p.is_absolute() or p.exists():
        return p

    # Best-effort: interpret relative paths under repo root.
    try:
        repo_root = Path(__file__).resolve().parents[4]  # app/services/ocr/providers -> repo root
        candidate = repo_root / raw
        if candidate.exists():
            return candidate
    except Exception:
        pass

    return p


def _normalize_confidence(value) -> float:
    try:
        conf = float(value)
    except Exception:
        conf = 0.0
    return max(0.0, min(1.0, conf))


def _append_text_block(lines: list[OCRTextBlock], text, confidence) -> None:
    normalized_text = str(text or "").strip()
    if not normalized_text:
        return
    lines.append(OCRTextBlock(text=normalized_text, confidence=_normalize_confidence(confidence)))


def _parse_paddle_result(result) -> list[OCRTextBlock]:
    lines: list[OCRTextBlock] = []

    for page in result or []:
        # PaddleOCR 3.x predict() often returns list[dict] with rec_texts/rec_scores.
        if isinstance(page, dict):
            rec_texts = page.get("rec_texts") or []
            rec_scores = page.get("rec_scores") or []
            if isinstance(rec_texts, list):
                for idx, text in enumerate(rec_texts):
                    score = rec_scores[idx] if isinstance(rec_scores, list) and idx < len(rec_scores) else 0.0
                    _append_text_block(lines, text, score)
            continue

        # Backward-compatible parsing for old ocr() list structures.
        if not isinstance(page, list):
            continue

        # Old style can be either:
        # - [[box, (text, conf)], ...]
        # - [box, (text, conf)]  (single item page)
        items = page
        if len(page) >= 2 and isinstance(page[1], (list, tuple)) and not isinstance(page[0], (list, tuple)):
            items = [page]

        for item in items:
            if not isinstance(item, (list, tuple)) or len(item) < 2:
                continue
            line_info = item[1]
            if not isinstance(line_info, (list, tuple)) or len(line_info) < 1:
                continue
            text = line_info[0]
            score = line_info[1] if len(line_info) > 1 else 0.0
            _append_text_block(lines, text, score)

    return lines


def run_paddle_ocr(ocr_input: OCRDocumentInput) -> tuple[str, list[OCRTextBlock], float]:
    if not settings.OCR_PADDLE_ENABLED:
        raise PaddleOCRProviderError("paddle_disabled", "paddle_provider_disabled")

    file_path = str(ocr_input.file_path or "").strip()
    if not file_path or file_path.startswith("mock://"):
        raise PaddleOCRProviderError("file_not_found", "ocr_input_file_not_found")

    path_obj = _resolve_file_path(file_path)
    if not path_obj.exists() or not path_obj.is_file():
        raise PaddleOCRProviderError("file_not_found", "ocr_input_file_not_found")

    try:
        engine = _create_paddle_engine()
        image = str(path_obj)
        # PaddleOCR 3.x prefers predict(image). Avoid legacy cls/use_gpu style args.
        if hasattr(engine, "predict"):
            result = engine.predict(image)
        elif hasattr(engine, "ocr"):
            result = engine.ocr(image)
        else:
            raise PaddleOCRProviderError("provider_error", "paddle_ocr_method_not_found")
    except PaddleOCRProviderError:
        raise
    except Exception as exc:
        reason = "paddle_runtime_error" if isinstance(exc, NotImplementedError) else "provider_error"
        raise PaddleOCRProviderError(reason, f"paddle_inference_failed:{exc}") from exc

    lines = _parse_paddle_result(result)

    raw_text = "\n".join(block.text for block in lines)

    # P15-E: if PaddleOCR returns no usable text, treat it as provider failure
    # (so we can fall back to mock with an explicit reason).
    if not lines or not raw_text.strip():
        raise PaddleOCRProviderError("empty_ocr_result", "paddle_ocr_empty_result")

    confidence = sum(block.confidence for block in lines) / len(lines)
    return raw_text, lines, round(confidence, 4)
