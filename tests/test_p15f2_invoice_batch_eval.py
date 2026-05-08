from __future__ import annotations

import importlib.util
import json
import zipfile
from pathlib import Path


def _load_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _script_path(name: str) -> Path:
    return Path(__file__).resolve().parent.parent / "scripts" / name


def test_p15f2_safe_output_name_is_stable():
    mod = _load_module("p15f2_download_mod_stable", _script_path("download_hf_chinese_invoice_samples.py"))
    name1 = mod.safe_output_name("Chinese/Invoice 01.PNG")
    name2 = mod.safe_output_name("Chinese/Invoice 01.PNG")
    assert name1 == name2
    assert name1 == "chinese_invoice_01.png"


def test_p15f2_download_dry_run_generates_manifest_only(monkeypatch, tmp_path):
    mod = _load_module("p15f2_download_mod_dryrun", _script_path("download_hf_chinese_invoice_samples.py"))
    monkeypatch.setattr(
        mod,
        "list_candidate_files",
        lambda repo_id, language_prefix: [
            "Chinese/invoice_a.jpg",
            "Chinese/invoice_b.png",
        ],
    )
    output_dir = tmp_path / "samples"
    result = mod.download_samples(
        repo_id="repo/demo",
        language_prefix="Chinese/",
        output_dir=output_dir,
        cache_dir=tmp_path / "cache",
        limit=2,
        seed=42,
        dry_run=True,
    )
    assert result["selected_count"] == 2
    assert result["direct_image_candidates"] == 2
    assert result["downloaded_count"] == 0
    assert (output_dir / "manifest.csv").exists()
    images = [p for p in output_dir.iterdir() if p.suffix.lower() in {".jpg", ".png", ".jpeg", ".webp"}]
    assert images == []


def test_p15f2_download_archive_fallback_and_manifest_fields(monkeypatch, tmp_path):
    mod = _load_module("p15f2_download_mod_archive", _script_path("download_hf_chinese_invoice_samples.py"))
    monkeypatch.setattr(mod, "list_candidate_files", lambda repo_id, language_prefix: [])
    monkeypatch.setattr(
        mod,
        "list_repo_files_all",
        lambda repo_id: ["Chinese.zip", "README.md"],
    )

    archive_src = tmp_path / "mock_chinese.zip"
    with zipfile.ZipFile(archive_src, "w") as zipf:
        zipf.writestr("folder/a.jpg", b"a")
        zipf.writestr("folder/b.png", b"b")
        zipf.writestr("folder/c.jpeg", b"c")

    monkeypatch.setattr(mod, "download_repo_file", lambda repo_id, filename, cache_dir: archive_src)

    output_dir = tmp_path / "samples"
    result = mod.download_samples(
        repo_id="repo/demo",
        language_prefix="Chinese/",
        output_dir=output_dir,
        cache_dir=tmp_path / "cache",
        limit=2,
        seed=42,
        dry_run=False,
    )
    assert result["candidate_count"] == 0
    assert result["archive_candidate"] == "Chinese.zip"
    assert result["zip_image_candidates"] == 3
    assert result["selected_count"] == 2
    assert result["downloaded_count"] == 2

    manifest = (output_dir / "manifest.csv").read_text(encoding="utf-8")
    assert "source_archive" in manifest
    assert "archive_inner_path" in manifest
    assert "Chinese.zip" in manifest
    copied = [p for p in output_dir.iterdir() if p.is_file() and p.name != "manifest.csv"]
    assert len(copied) == 2


def test_p15f2_download_archive_dry_run_reports_fallback(monkeypatch, tmp_path):
    mod = _load_module("p15f2_download_mod_archive_dry", _script_path("download_hf_chinese_invoice_samples.py"))
    monkeypatch.setattr(mod, "list_candidate_files", lambda repo_id, language_prefix: [])
    monkeypatch.setattr(mod, "list_repo_files_all", lambda repo_id: ["Chinese.zip"])

    archive_src = tmp_path / "mock_chinese.zip"
    with zipfile.ZipFile(archive_src, "w") as zipf:
        for i in range(5):
            zipf.writestr(f"folder/{i:02d}.jpg", b"x")

    monkeypatch.setattr(mod, "download_repo_file", lambda repo_id, filename, cache_dir: archive_src)

    output_dir = tmp_path / "samples"
    result = mod.download_samples(
        repo_id="repo/demo",
        language_prefix="Chinese/",
        output_dir=output_dir,
        cache_dir=tmp_path / "cache",
        limit=3,
        seed=7,
        dry_run=True,
    )
    assert result["direct_image_candidates"] == 0
    assert result["archive_candidate"] == "Chinese.zip"
    assert result["zip_image_candidates"] == 5
    assert result["selected_count"] == 3
    assert result["downloaded_count"] == 0
    copied = [p for p in output_dir.iterdir() if p.is_file() and p.name != "manifest.csv"]
    assert copied == []


def test_p15f2_eval_scan_directory_with_limit(tmp_path):
    mod = _load_module("p15f2_eval_mod_scan", _script_path("evaluate_invoice_ocr_batch.py"))
    (tmp_path / "a.jpg").write_bytes(b"x")
    (tmp_path / "b.png").write_bytes(b"x")
    (tmp_path / "c.txt").write_text("x", encoding="utf-8")
    paths = mod.discover_images(tmp_path, limit=1)
    assert len(paths) == 1
    assert paths[0].suffix.lower() in {".jpg", ".png", ".jpeg", ".webp"}


def test_p15f2_eval_metrics_and_outputs(monkeypatch, tmp_path):
    mod = _load_module("p15f2_eval_mod_metrics", _script_path("evaluate_invoice_ocr_batch.py"))
    image1 = tmp_path / "img1.jpg"
    image2 = tmp_path / "img2.png"
    image3 = tmp_path / "img3.webp"
    image1.write_bytes(b"1")
    image2.write_bytes(b"2")
    image3.write_bytes(b"3")

    class DummyOcr:
        def __init__(self, status, provider, fallback_used, fallback_reason, raw_text, conf, blocks, error=""):
            self.status = status
            self.provider = provider
            self.fallback_used = fallback_used
            self.fallback_reason = fallback_reason
            self.raw_text = raw_text
            self.confidence = conf
            self.blocks = blocks
            self.error = error

    class DummyField:
        def __init__(self, name, value):
            self.name = name
            self.value = value

    class DummyExtraction:
        def __init__(self, status, fields, missing_fields, needs_manual_review, warnings, error=""):
            self.status = status
            self.fields = fields
            self.missing_fields = missing_fields
            self.needs_manual_review = needs_manual_review
            self.warnings = warnings
            self.error = error
            self.document_type = "invoice"
            self.overall_confidence = 0.88

    def fake_run_document_ocr(ocr_input):
        name = Path(ocr_input.file_path).name
        if name == "img1.jpg":
            return DummyOcr("succeeded", "paddle", False, "", "发票号码:123\n价税合计:105", 0.9, [1, 2, 3])
        if name == "img2.png":
            return DummyOcr("succeeded", "mock", True, "paddle_disabled", "", 0.7, [], "")
        return DummyOcr("failed", "paddle", False, "", "", 0.0, [], "ocr_failed_for_test")

    def fake_run_document_extraction(extraction_input):
        if extraction_input.ocr_provider == "mock":
            return DummyExtraction(
                "succeeded",
                [
                    DummyField("invoice_date", "2024-04-07"),
                    DummyField("seller_name", "销售方A"),
                    DummyField("currency", "CNY"),
                ],
                ["invoice_number", "buyer_name", "total_amount", "tax_amount", "amount_without_tax"],
                True,
                ["需要人工复核"],
            )
        return DummyExtraction(
            "succeeded",
            [
                DummyField("invoice_number", "123"),
                DummyField("invoice_date", "2024-04-07"),
                DummyField("buyer_name", "购买方A"),
                DummyField("seller_name", "销售方A"),
                DummyField("total_amount", "105"),
                DummyField("tax_amount", "5"),
                DummyField("amount_without_tax", "100"),
                DummyField("currency", "CNY"),
            ],
            [],
            False,
            [],
        )

    monkeypatch.setattr(mod, "run_document_ocr", fake_run_document_ocr)
    monkeypatch.setattr(mod, "run_document_extraction", fake_run_document_extraction)

    details, failed_cases, summary = mod.evaluate_batch(
        image_paths=[image1, image2, image3],
        provider="paddle",
        save_raw_text=False,
    )

    assert summary["total_images"] == 3
    assert summary["processed_images"] == 3
    assert summary["ocr_success_count"] == 2
    assert summary["ocr_failed_count"] == 1
    assert summary["fallback_used_count"] == 1
    assert summary["fallback_rate"] == 0.5
    assert summary["extraction_success_count"] == 2
    assert summary["extraction_failed_count"] == 0
    assert summary["needs_review_count"] == 1
    assert summary["needs_review_rate"] == 0.5
    assert "paddle_disabled" in summary["fallback_reason_distribution"]
    assert "invoice_number" in summary["missing_fields_distribution"]
    assert "ocr_failed_for_test" in summary["error_distribution"]

    headers = set(details[0].keys())
    assert "manual_note" in headers
    assert "manual_invoice_number_correct" in headers
    assert "raw_text_snippet" in headers
    assert len(failed_cases) == 1
    assert failed_cases[0]["stage"] == "ocr"

    artifacts = mod.write_outputs(
        output_root=tmp_path / "runs",
        run_id="demo_run",
        details=details,
        failed_cases=failed_cases,
        summary=summary,
    )
    assert artifacts["summary_path"].exists()
    assert artifacts["details_path"].exists()
    assert artifacts["failed_cases_path"].exists()

    summary_loaded = json.loads(artifacts["summary_path"].read_text(encoding="utf-8"))
    failed_loaded = json.loads(artifacts["failed_cases_path"].read_text(encoding="utf-8"))
    assert summary_loaded["total_images"] == 3
    assert failed_loaded[0]["image_file"] == "img3.webp"
