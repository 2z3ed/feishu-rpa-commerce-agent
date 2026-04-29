import json

import pytest

from app.core.config import settings
from app.graph.nodes.execute_action import execute_action
from app.schemas.ocr_document import OCRDocumentInput
from app.services.ocr.document_ocr import run_document_ocr


def _fake_paddle_ocr_result(lines: list[tuple[str, float]]) -> list:
    """
    Build a result shaped like PaddleOCR:
    result -> list[page], page -> list[item], item -> [box, (text, conf)]
    """
    page = []
    for text, conf in lines:
        page.append([[0, 0, 1, 1], (text, conf)])
    return [page]


def _patch_paddle_provider_with_result(monkeypatch, result, with_predict: bool = True, with_ocr: bool = False):
    from app.services.ocr.providers import paddle_provider

    class _FakePaddleOCR:
        def __init__(self, *args, **kwargs):
            # Ensure provider does not pass deprecated use_gpu parameter.
            assert "use_gpu" not in kwargs

        if with_predict:
            def predict(self, image_path: str):
                # `image_path` is only used for existence checks in provider.
                return result

        if with_ocr:
            def ocr(self, image_path: str):
                # Old ocr() return structure compatibility.
                return result

    monkeypatch.setattr(paddle_provider, "_load_paddle_ocr_class", lambda: _FakePaddleOCR)


def test_p15e_provider_prefers_predict_without_cls(monkeypatch, tmp_path):
    from app.services.ocr.providers import paddle_provider

    calls = {"predict": 0, "ocr": 0}

    class _FakePaddleOCR:
        def __init__(self, *args, **kwargs):
            assert "use_gpu" not in kwargs

        def predict(self, image_path: str):
            calls["predict"] += 1
            return _fake_paddle_ocr_result([("发票号码：987654321", 0.9)])

        def ocr(self, image_path: str):
            calls["ocr"] += 1
            raise AssertionError("predict exists, should not call ocr")

    monkeypatch.setattr(settings, "ENABLE_OCR_DOCUMENT_RECOGNIZE", True)
    monkeypatch.setattr(settings, "OCR_DOCUMENT_PROVIDER", "paddle")
    monkeypatch.setattr(settings, "OCR_PADDLE_ENABLED", True)
    monkeypatch.setattr(paddle_provider, "_load_paddle_ocr_class", lambda: _FakePaddleOCR)

    sample = tmp_path / "sample.png"
    sample.write_bytes(b"fake-image-bytes")
    out = run_document_ocr(
        OCRDocumentInput(
            document_id="mock-doc-p15e-predict",
            file_name="invoice.png",
            mime_type="image/png",
            file_path=str(sample),
            source="feishu",
            requested_by="feishu_user",
            hint_document_type="invoice",
        )
    )
    assert out.status == "succeeded"
    assert out.provider == "paddle"
    assert calls["predict"] == 1
    assert calls["ocr"] == 0


def test_p15e_provider_ocr_fallback_without_cls(monkeypatch, tmp_path):
    from app.services.ocr.providers import paddle_provider

    calls = {"ocr": 0}

    class _FakePaddleOCR:
        def __init__(self, *args, **kwargs):
            assert "use_gpu" not in kwargs

        def ocr(self, image_path: str):
            calls["ocr"] += 1
            return _fake_paddle_ocr_result([("开票日期：2026-04-29", 0.87)])

    monkeypatch.setattr(settings, "ENABLE_OCR_DOCUMENT_RECOGNIZE", True)
    monkeypatch.setattr(settings, "OCR_DOCUMENT_PROVIDER", "paddle")
    monkeypatch.setattr(settings, "OCR_PADDLE_ENABLED", True)
    monkeypatch.setattr(paddle_provider, "_load_paddle_ocr_class", lambda: _FakePaddleOCR)

    sample = tmp_path / "sample.png"
    sample.write_bytes(b"fake-image-bytes")
    out = run_document_ocr(
        OCRDocumentInput(
            document_id="mock-doc-p15e-ocr",
            file_name="invoice.png",
            mime_type="image/png",
            file_path=str(sample),
            source="feishu",
            requested_by="feishu_user",
            hint_document_type="invoice",
        )
    )
    assert out.status == "succeeded"
    assert out.provider == "paddle"
    assert calls["ocr"] == 1


def test_p15e_parse_paddle_predict_v3_dict_result(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "ENABLE_OCR_DOCUMENT_RECOGNIZE", True)
    monkeypatch.setattr(settings, "OCR_DOCUMENT_PROVIDER", "paddle")
    monkeypatch.setattr(settings, "OCR_PADDLE_ENABLED", True)

    result = [
        {
            "rec_texts": [
                "发票号码：987654321",
                "开票日期：2026-04-29",
                "购买方：深圳测试科技有限公司",
                "金额：256.80",
            ],
            "rec_scores": [0.98, 0.97, 0.96, 0.95],
        }
    ]
    _patch_paddle_provider_with_result(monkeypatch, result, with_predict=True, with_ocr=False)

    sample = tmp_path / "sample.png"
    sample.write_bytes(b"fake-image-bytes")
    out = run_document_ocr(
        OCRDocumentInput(
            document_id="mock-doc-p15e-v3",
            file_name="invoice.png",
            mime_type="image/png",
            file_path=str(sample),
            source="feishu",
            requested_by="feishu_user",
            hint_document_type="invoice",
        )
    )

    assert out.provider == "paddle"
    assert out.fallback_used is False
    assert "987654321" in out.raw_text
    assert "深圳测试科技有限公司" in out.raw_text
    assert len(out.blocks) == 4
    assert out.confidence > 0.9
    assert "12345678" not in out.raw_text
    assert "测试公司" not in out.raw_text
    assert "128.50" not in out.raw_text


def _image_event_payload() -> dict:
    # Must match app.services.feishu.file_attachment.resolve_feishu_attachments().
    return {
        "event": {
            "message": {
                "message_id": "om_xxx",
                "message_type": "image",
                "content": json.dumps(
                    {
                        "image_key": "img_key_xxx",
                        "file_name": "invoice.png",
                        "mime_type": "image/png",
                        "file_size": 128,
                    }
                ),
            }
        }
    }


def test_p15e_paddle_enabled_false_fallbacks_to_mock(monkeypatch, tmp_path):
    # Requirement 1 + 7: provider=paddle but OCR_PADDLE_ENABLED=false => fallback mock
    monkeypatch.setattr(settings, "ENABLE_OCR_DOCUMENT_RECOGNIZE", True)
    monkeypatch.setattr(settings, "OCR_DOCUMENT_PROVIDER", "paddle")
    monkeypatch.setattr(settings, "OCR_PADDLE_ENABLED", False)

    sample = tmp_path / "sample.png"
    sample.write_bytes(b"fake-image-bytes")

    out = run_document_ocr(
        OCRDocumentInput(
            document_id="mock-doc-p15e-1",
            file_name="invoice.png",
            mime_type="image/png",
            file_path=str(sample),
            source="feishu",
            requested_by="feishu_user",
            hint_document_type="invoice",
        )
    )
    assert out.status == "succeeded"
    assert out.provider == "mock"
    assert out.fallback_used is True
    assert out.fallback_reason == "paddle_disabled"


def test_p15e_file_not_found_fallback_reason(monkeypatch, tmp_path):
    # Requirement 2: provider=paddle but file_path does not exist => fallback_reason=file_not_found
    monkeypatch.setattr(settings, "ENABLE_OCR_DOCUMENT_RECOGNIZE", True)
    monkeypatch.setattr(settings, "OCR_DOCUMENT_PROVIDER", "paddle")
    monkeypatch.setattr(settings, "OCR_PADDLE_ENABLED", True)

    missing = tmp_path / "missing.png"
    assert not missing.exists()

    out = run_document_ocr(
        OCRDocumentInput(
            document_id="mock-doc-p15e-2",
            file_name="invoice.png",
            mime_type="image/png",
            file_path=str(missing),
            source="feishu",
            requested_by="feishu_user",
            hint_document_type="invoice",
        )
    )
    assert out.status == "succeeded"
    assert out.provider == "mock"
    assert out.fallback_used is True
    assert out.fallback_reason == "file_not_found"


def test_p15e_paddle_success_mapping_and_raw_text_not_mock(monkeypatch, tmp_path):
    # Requirement 3/5/6: paddle success => mapping to OCRDocumentOutput,
    # raw_text comes from provider result (not P15-A mock fixed text).
    monkeypatch.setattr(settings, "ENABLE_OCR_DOCUMENT_RECOGNIZE", True)
    monkeypatch.setattr(settings, "OCR_DOCUMENT_PROVIDER", "paddle")
    monkeypatch.setattr(settings, "OCR_PADDLE_ENABLED", True)

    # Fake PaddleOCR output should include the "real sample" key text.
    lines = [
        ("发票号码：987654321", 0.93),
        ("开票日期：2026-04-29", 0.88),
        ("购买方：深圳测试科技有限公司", 0.9),
        ("金额：256.80", 0.86),
    ]
    result = _fake_paddle_ocr_result(lines)
    _patch_paddle_provider_with_result(monkeypatch, result, with_predict=False, with_ocr=True)

    sample = tmp_path / "sample.png"
    sample.write_bytes(b"fake-image-bytes")

    out = run_document_ocr(
        OCRDocumentInput(
            document_id="mock-doc-p15e-3",
            file_name="invoice.png",
            mime_type="image/png",
            file_path=str(sample),
            source="feishu",
            requested_by="feishu_user",
            hint_document_type="invoice",
        )
    )

    assert out.status == "succeeded"
    assert out.provider == "paddle"
    assert out.fallback_used is False
    assert out.fallback_reason == ""
    assert out.blocks
    assert len(out.blocks) == 4
    assert out.confidence > 0
    assert "987654321" in out.raw_text
    assert "12345678" not in out.raw_text  # P15-A mock fixed content


def test_p15e_empty_paddle_result_fallback(monkeypatch, tmp_path):
    # Requirement 4: PaddleOCR returns empty result => friendly failure or fallback
    monkeypatch.setattr(settings, "ENABLE_OCR_DOCUMENT_RECOGNIZE", True)
    monkeypatch.setattr(settings, "OCR_DOCUMENT_PROVIDER", "paddle")
    monkeypatch.setattr(settings, "OCR_PADDLE_ENABLED", True)

    # Empty: no usable text => provider should raise and fallback to mock.
    result = [[]]
    _patch_paddle_provider_with_result(monkeypatch, result)

    sample = tmp_path / "sample.png"
    sample.write_bytes(b"fake-image-bytes")

    out = run_document_ocr(
        OCRDocumentInput(
            document_id="mock-doc-p15e-4",
            file_name="invoice.png",
            mime_type="image/png",
            file_path=str(sample),
            source="feishu",
            requested_by="feishu_user",
            hint_document_type="invoice",
        )
    )
    assert out.provider == "mock"
    assert out.fallback_used is True
    assert out.fallback_reason  # non-empty


def test_p15e_execute_action_steps_include_evidence_and_provider_details(
    monkeypatch, tmp_path
):
    # Requirement 8/9 (steps leaving trace): evidence_relative_path + provider_actual/paddle
    # should be visible in ocr steps detail.
    monkeypatch.setattr(settings, "ENABLE_OCR_DOCUMENT_RECOGNIZE", True)
    monkeypatch.setattr(settings, "OCR_DOCUMENT_PROVIDER", "paddle")
    monkeypatch.setattr(settings, "OCR_PADDLE_ENABLED", True)
    monkeypatch.setattr(settings, "ENABLE_FEISHU_FILE_DOWNLOAD", True)
    monkeypatch.setattr(settings, "FEISHU_FILE_EVIDENCE_DIR", str(tmp_path / "evidence"))

    # Fake feishu file download.
    monkeypatch.setattr(
        "app.services.feishu.client.feishu_client.download_message_resource",
        lambda message_id, file_key, attachment_type: b"fakepngbytes",
    )

    lines = [
        ("发票号码：987654321", 0.93),
        ("开票日期：2026-04-29", 0.88),
        ("购买方：深圳测试科技有限公司", 0.9),
        ("金额：256.80", 0.86),
    ]
    result = _fake_paddle_ocr_result(lines)
    _patch_paddle_provider_with_result(monkeypatch, result)

    logs = []
    monkeypatch.setattr("app.graph.nodes.execute_action.log_step", lambda *args: logs.append(args))

    state = execute_action(
        {
            "task_id": "TASK-P15E-EXEC",
            "intent_code": "document.ocr_recognize",
            "slots": {"hint_document_type": "invoice"},
            "source_message_payload": _image_event_payload(),
        }
    )

    assert state["status"] == "succeeded"
    assert state["parsed_result"]["provider_actual"] == "paddle"
    assert state["parsed_result"]["fallback_used"] is False
    assert int(state["parsed_result"]["blocks_count"]) > 0
    assert int(state["parsed_result"]["raw_text_length"]) > 0
    assert state["parsed_result"]["evidence_relative_path"]
    assert not str(state["parsed_result"]["evidence_relative_path"]).startswith("/")

    # Verify ocr_document_succeeded step detail contains evidence/provider fields.
    succeeded_details = [
        item[3]
        for item in logs
        if len(item) >= 4 and item[1] == "ocr_document_succeeded"
    ]
    assert succeeded_details, "missing ocr_document_succeeded step"
    detail = succeeded_details[-1]
    assert "provider_actual=paddle" in detail
    assert "fallback_used=false" in detail
    assert "image_source=feishu" in detail
    assert "evidence_relative_path=" in detail

    # Raw text must be from provider result, not P15-A mock fixed text.
    assert "987654321" in state["result_summary"]
    assert "12345678" not in state["result_summary"]


def test_p15e_execute_action_structured_extract_uses_real_raw_text(monkeypatch, tmp_path):
    # Extra coverage: document.structured_extract should use OCR raw_text from paddle result.
    monkeypatch.setattr(settings, "ENABLE_OCR_DOCUMENT_RECOGNIZE", True)
    monkeypatch.setattr(settings, "OCR_DOCUMENT_PROVIDER", "paddle")
    monkeypatch.setattr(settings, "OCR_PADDLE_ENABLED", True)
    monkeypatch.setattr(settings, "ENABLE_DOCUMENT_STRUCTURED_EXTRACTION", True)
    monkeypatch.setattr(settings, "DOCUMENT_EXTRACTION_PROVIDER", "rule")
    monkeypatch.setattr(settings, "ENABLE_FEISHU_FILE_DOWNLOAD", True)
    monkeypatch.setattr(settings, "FEISHU_FILE_EVIDENCE_DIR", str(tmp_path / "evidence"))

    monkeypatch.setattr(
        "app.services.feishu.client.feishu_client.download_message_resource",
        lambda message_id, file_key, attachment_type: b"fakepngbytes",
    )

    lines = [
        ("发票号码：987654321", 0.93),
        ("开票日期：2026-04-29", 0.88),
        ("购买方：深圳测试科技有限公司", 0.9),
        ("金额：256.80", 0.86),
    ]
    result = _fake_paddle_ocr_result(lines)
    _patch_paddle_provider_with_result(monkeypatch, result)

    state = execute_action(
        {
            "task_id": "TASK-P15E-STRUCT",
            "intent_code": "document.structured_extract",
            "slots": {"hint_document_type": "invoice"},
            "source_message_payload": _image_event_payload(),
        }
    )

    assert state["status"] == "succeeded"
    assert state["parsed_result"]["provider_actual"] == "paddle"
    assert state["parsed_result"]["fallback_used"] is False
    assert "发票号码：987654321" in state["result_summary"]
    # Confirm that mock fixed content is not used.
    assert "发票号码：12345678" not in state["result_summary"]

