from __future__ import annotations

import argparse
import csv
import random
import re
import shutil
import zipfile
from pathlib import Path

DEFAULT_REPO_ID = "AlroWilde/invoice-checkmark-annotations"
DEFAULT_LANGUAGE_PREFIX = "Chinese/"
DEFAULT_OUTPUT_DIR = "data/ocr_samples/hf_chinese_invoice_20"
DEFAULT_CACHE_DIR = "data/hf_cache/invoice_checkmark_annotations"
DEFAULT_LIMIT = 20
DEFAULT_SEED = 42
_IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff")


def safe_output_name(source_path: str) -> str:
    normalized = source_path.replace("\\", "/").strip("/")
    stem = re.sub(r"[^a-zA-Z0-9._-]+", "_", normalized)
    stem = re.sub(r"_+", "_", stem).strip("._")
    if not stem:
        stem = "sample"
    return stem.lower()


def list_candidate_files(repo_id: str, language_prefix: str) -> list[str]:
    from huggingface_hub import list_repo_files

    files = list_repo_files(repo_id=repo_id, repo_type="dataset")
    prefix = language_prefix.strip()
    return sorted(
        file_path
        for file_path in files
        if file_path.startswith(prefix) and file_path.lower().endswith(_IMAGE_SUFFIXES)
    )


def list_repo_files_all(repo_id: str) -> list[str]:
    from huggingface_hub import list_repo_files

    return list_repo_files(repo_id=repo_id, repo_type="dataset")


def download_repo_file(*, repo_id: str, filename: str, cache_dir: Path) -> Path:
    from huggingface_hub import hf_hub_download

    return Path(
        hf_hub_download(
            repo_id=repo_id,
            repo_type="dataset",
            filename=filename,
            cache_dir=str(cache_dir),
        )
    )


def detect_archive_candidate(repo_files: list[str], language_prefix: str) -> str:
    preferred = (
        "Chinese.zip",
        "Chinese/Chinese.zip",
    )
    for item in preferred:
        if item in repo_files:
            return item
    prefix = language_prefix.strip("/").lower()
    for item in repo_files:
        lowered = item.lower()
        if lowered.endswith(".zip") and prefix in lowered:
            return item
    return ""


def find_images_in_directory(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(
        path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in _IMAGE_SUFFIXES
    )


def select_files(candidates: list[str], limit: int, seed: int) -> list[str]:
    if limit <= 0 or not candidates:
        return []
    picked = list(candidates)
    random.Random(seed).shuffle(picked)
    return sorted(picked[: min(limit, len(picked))])


def write_manifest(output_dir: Path, rows: list[dict[str, str]]) -> Path:
    manifest_path = output_dir / "manifest.csv"
    with manifest_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "index",
                "source_repo",
                "source_path",
                "source_archive",
                "archive_inner_path",
                "output_file",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    return manifest_path


def download_samples(
    *,
    repo_id: str,
    language_prefix: str,
    output_dir: Path,
    cache_dir: Path,
    limit: int,
    seed: int,
    dry_run: bool,
) -> dict[str, object]:
    direct_candidates = list_candidate_files(repo_id=repo_id, language_prefix=language_prefix)
    selected = select_files(candidates=direct_candidates, limit=limit, seed=seed)
    archive_candidate = ""
    zip_image_candidates: list[Path] = []
    extracted_root = cache_dir / "extracted" / "Chinese"
    mode = "direct"

    if not direct_candidates:
        mode = "archive_fallback"
        repo_files = list_repo_files_all(repo_id=repo_id)
        archive_candidate = detect_archive_candidate(repo_files=repo_files, language_prefix=language_prefix)
        if archive_candidate:
            local_archive = download_repo_file(
                repo_id=repo_id,
                filename=archive_candidate,
                cache_dir=cache_dir,
            )
            if not dry_run:
                extracted_root.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(local_archive, "r") as zip_ref:
                    zip_ref.extractall(extracted_root)
            else:
                # Dry-run still reads zip entries to preview candidate count,
                # but does not copy sample images to output_dir.
                extracted_root.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(local_archive, "r") as zip_ref:
                    zip_ref.extractall(extracted_root)
            zip_image_candidates = find_images_in_directory(extracted_root)
            selected_zip = select_files(
                candidates=[str(path.relative_to(extracted_root)) for path in zip_image_candidates],
                limit=limit,
                seed=seed,
            )
        else:
            selected_zip = []
        selected = selected_zip

    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []
    downloaded_count = 0

    for index, source_path in enumerate(selected, start=1):
        safe_name = f"{index:03d}_{safe_output_name(source_path)}"
        target_path = output_dir / safe_name
        source_archive = ""
        archive_inner_path = ""
        source_path_value = source_path

        if mode == "direct":
            if not dry_run:
                local_cached = download_repo_file(
                    repo_id=repo_id,
                    filename=source_path,
                    cache_dir=cache_dir,
                )
                shutil.copy2(local_cached, target_path)
                downloaded_count += 1
        else:
            source_archive = archive_candidate
            archive_inner_path = source_path
            source_path_value = archive_candidate
            if not dry_run:
                extracted_file = extracted_root / source_path
                shutil.copy2(extracted_file, target_path)
                downloaded_count += 1
        rows.append(
            {
                "index": str(index),
                "source_repo": repo_id,
                "source_path": source_path_value,
                "source_archive": source_archive,
                "archive_inner_path": archive_inner_path,
                "output_file": safe_name,
            }
        )

    manifest_path = write_manifest(output_dir=output_dir, rows=rows)
    return {
        "repo_id": repo_id,
        "language_prefix": language_prefix,
        "output_dir": str(output_dir),
        "cache_dir": str(cache_dir),
        "dry_run": dry_run,
        "mode": mode,
        "candidate_count": len(direct_candidates),
        "direct_image_candidates": len(direct_candidates),
        "archive_candidate": archive_candidate,
        "zip_image_candidates": len(zip_image_candidates),
        "selected_count": len(selected),
        "downloaded_count": downloaded_count,
        "manifest_path": str(manifest_path),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Download Chinese invoice sample images from Hugging Face datasets.")
    parser.add_argument("--repo-id", default=DEFAULT_REPO_ID)
    parser.add_argument("--language-prefix", default=DEFAULT_LANGUAGE_PREFIX)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--cache-dir", default=DEFAULT_CACHE_DIR)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = download_samples(
        repo_id=args.repo_id,
        language_prefix=args.language_prefix,
        output_dir=Path(args.output_dir),
        cache_dir=Path(args.cache_dir),
        limit=args.limit,
        seed=args.seed,
        dry_run=args.dry_run,
    )
    print(result)


if __name__ == "__main__":
    main()
