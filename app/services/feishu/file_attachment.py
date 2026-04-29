from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Callable
from uuid import uuid4

from app.core.config import settings
from app.schemas.feishu_file import DownloadedFeishuFile, FeishuAttachmentMeta
from app.schemas.ocr_document import OCRDocumentInput
from app.services.feishu.client import feishu_client
from app.services.feishu.parser import build_payload_safe_summary


def _normalize_mime_types(raw_value: str) -> set[str]:
    values = [item.strip().lower() for item in str(raw_value or "").split(",")]
    return {item for item in values if item}


def _safe_filename(file_name: str, default_ext: str = ".bin") -> str:
    raw = str(file_name or "").strip()
    if not raw:
        return f"feishu_attachment_{uuid4().hex[:8]}{default_ext}"
    keep = []
    for ch in raw:
        if ch.isalnum() or ch in ("-", "_", ".", " "):
            keep.append(ch)
    sanitized = "".join(keep).strip().replace(" ", "_")
    if not sanitized:
        sanitized = f"feishu_attachment_{uuid4().hex[:8]}{default_ext}"
    return sanitized


def _extract_post_attachment_items(content: object) -> list[dict]:
    items: list[dict] = []
    if not isinstance(content, dict):
        return items

    direct_content = content.get("content")
    if isinstance(direct_content, list):
        for row in direct_content:
            if not isinstance(row, list):
                continue
            for item in row:
                if isinstance(item, dict):
                    items.append(item)

    post_obj = content.get("post")
    if isinstance(post_obj, dict):
        for lang_obj in post_obj.values():
            if not isinstance(lang_obj, dict):
                continue
            nested_content = lang_obj.get("content")
            if not isinstance(nested_content, list):
                continue
            for row in nested_content:
                if not isinstance(row, list):
                    continue
                for item in row:
                    if isinstance(item, dict):
                        items.append(item)
    return items


def _diagnostic_paths_and_counts(payload: dict) -> dict:
    event = payload.get("event") if isinstance(payload.get("event"), dict) else {}
    message = event.get("message") if isinstance(event.get("message"), dict) else {}
    content_raw = message.get("content")
    content = content_raw if isinstance(content_raw, dict) else {}
    content_is_json_string = isinstance(content_raw, str)
    checked_paths = ["content.image_key", "content.file_key", "content.content[][]", "content.post.zh_cn.content[][]", "message.image_key", "message.file_key"]
    image_key_paths: list[str] = []
    file_key_paths: list[str] = []
    has_image_key = False
    has_file_key = False

    def walk(obj, path):
        nonlocal has_image_key, has_file_key
        if isinstance(obj, dict):
            for k, v in obj.items():
                p = f"{path}.{k}"
                if k == "image_key" and isinstance(v, str) and v:
                    has_image_key = True
                    image_key_paths.append(p)
                if k == "file_key" and isinstance(v, str) and v:
                    has_file_key = True
                    file_key_paths.append(p)
                walk(v, p)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                walk(v, f"{path}[{i}]")

    walk(content, "$content")
    walk(message, "$message")
    return {
        "source_message_payload_exists": bool(payload),
        "source_message_payload_type": type(payload).__name__,
        "source_message_payload_keys": list(payload.keys()) if isinstance(payload, dict) else [],
        "message_type": str(message.get("message_type") or ""),
        "content_type": type(content_raw).__name__,
        "content_keys": list(content.keys()) if isinstance(content, dict) else [],
        "content_is_json_string": content_is_json_string,
        "has_image_key": has_image_key,
        "image_key_paths": image_key_paths,
        "has_file_key": has_file_key,
        "file_key_paths": file_key_paths,
        "resolver_checked_paths": checked_paths,
    }


def resolve_feishu_attachments(message_payload: dict) -> list[FeishuAttachmentMeta]:
    payload = message_payload if isinstance(message_payload, dict) else {}
    if isinstance(payload.get("event"), dict) and isinstance(payload.get("event", {}).get("message"), dict):
        message = payload["event"]["message"]
    else:
        message = payload
    message_id = str(message.get("message_id") or "")
    message_type = str(message.get("message_type") or payload.get("message_type") or "").strip().lower()
    content_raw = message.get("content") if "content" in message else payload.get("content")
    content: dict = {}
    if isinstance(content_raw, dict):
        content = content_raw
    elif isinstance(content_raw, str):
        try:
            maybe = json.loads(content_raw)
            if isinstance(maybe, dict):
                content = maybe
        except Exception:
            content = {}

    attachments: list[FeishuAttachmentMeta] = []
    image_key = str(payload.get("image_key") or message.get("image_key") or content.get("image_key") or "")
    file_key = str(payload.get("file_key") or message.get("file_key") or content.get("file_key") or "")
    file_name = str(payload.get("file_name") or message.get("file_name") or content.get("file_name") or "")
    size_bytes_raw = payload.get("file_size") or message.get("file_size") or content.get("file_size") or payload.get("size") or message.get("size") or content.get("size")
    try:
        size_bytes = int(size_bytes_raw or 0)
    except Exception:
        size_bytes = 0
    mime_type = str(payload.get("mime_type") or message.get("mime_type") or content.get("mime_type") or "")

    if message_type == "image" and image_key:
        attachments.append(
            FeishuAttachmentMeta(
                attachment_type="image",
                message_id=message_id,
                image_key=image_key,
                file_name=file_name or "feishu_image.png",
                mime_type=mime_type or "image/png",
                size_bytes=size_bytes,
            )
        )
    elif message_type == "file" and file_key:
        attachments.append(
            FeishuAttachmentMeta(
                attachment_type="file",
                message_id=message_id,
                file_key=file_key,
                file_name=file_name or "feishu_file",
                mime_type=mime_type or "application/octet-stream",
                size_bytes=size_bytes,
            )
        )

    if attachments:
        return attachments

    for item in _extract_post_attachment_items(content):
        tag = str(item.get("tag") or "").strip().lower()
        if tag == "img":
            image_key = str(item.get("image_key") or "")
            if image_key:
                attachments.append(
                    FeishuAttachmentMeta(
                        attachment_type="image",
                        message_id=message_id,
                        image_key=image_key,
                        file_name=str(item.get("file_name") or content.get("file_name") or "feishu_image.png"),
                        mime_type=str(item.get("mime_type") or content.get("mime_type") or "image/png"),
                        size_bytes=int(item.get("file_size") or item.get("size") or content.get("file_size") or content.get("size") or 0),
                    )
                )
                break
        elif tag == "file":
            file_key = str(item.get("file_key") or "")
            if file_key:
                attachments.append(
                    FeishuAttachmentMeta(
                        attachment_type="file",
                        message_id=message_id,
                        file_key=file_key,
                        file_name=str(item.get("file_name") or content.get("file_name") or "feishu_file"),
                        mime_type=str(item.get("mime_type") or content.get("mime_type") or "application/octet-stream"),
                        size_bytes=int(item.get("file_size") or item.get("size") or content.get("file_size") or content.get("size") or 0),
                    )
                )
                break

    if attachments:
        return attachments

    # Fallback: some payloads keep keys directly in message.
    fallback_image_key = str(message.get("image_key") or content.get("image_key") or "")
    fallback_file_key = str(message.get("file_key") or content.get("file_key") or "")
    if fallback_image_key:
        attachments.append(
            FeishuAttachmentMeta(
                attachment_type="image",
                message_id=message_id,
                image_key=fallback_image_key,
                file_name=str(message.get("file_name") or content.get("file_name") or "feishu_image.png"),
                mime_type=str(message.get("mime_type") or content.get("mime_type") or "image/png"),
                size_bytes=int(message.get("file_size") or message.get("size") or content.get("file_size") or content.get("size") or 0),
            )
        )
    elif fallback_file_key:
        attachments.append(
            FeishuAttachmentMeta(
                attachment_type="file",
                message_id=message_id,
                file_key=fallback_file_key,
                file_name=str(message.get("file_name") or content.get("file_name") or "feishu_file"),
                mime_type=str(message.get("mime_type") or content.get("mime_type") or "application/octet-stream"),
                size_bytes=int(message.get("file_size") or message.get("size") or content.get("file_size") or content.get("size") or 0),
            )
        )
    return attachments


def select_single_supported_attachment(attachments: list[FeishuAttachmentMeta]) -> tuple[FeishuAttachmentMeta | None, str]:
    if not attachments:
        return None, "missing"
    if len(attachments) > 1:
        return None, "multiple_not_supported"
    attachment = attachments[0]
    allowed = _normalize_mime_types(settings.FEISHU_FILE_ALLOWED_MIME_TYPES)
    mime_type = str(attachment.mime_type or "").strip().lower()
    if mime_type not in allowed:
        return None, "unsupported_type"
    max_bytes = int(settings.FEISHU_FILE_MAX_SIZE_MB) * 1024 * 1024
    if int(attachment.size_bytes or 0) > 0 and int(attachment.size_bytes) > max_bytes:
        return None, "too_large"
    return attachment, ""


def download_feishu_file(
    attachment: FeishuAttachmentMeta,
    task_id: str,
    downloader: Callable[[str, str, str], bytes] | None = None,
) -> DownloadedFeishuFile:
    download_func = downloader or feishu_client.download_message_resource
    key = attachment.image_key if attachment.attachment_type == "image" else attachment.file_key
    data = download_func(attachment.message_id, key, attachment.attachment_type)
    if not isinstance(data, (bytes, bytearray)) or len(data) <= 0:
        raise ValueError("empty_download_content")

    max_bytes = int(settings.FEISHU_FILE_MAX_SIZE_MB) * 1024 * 1024
    file_size = len(data)
    if file_size > max_bytes:
        raise ValueError("file_too_large")

    evidence_base = Path(str(settings.FEISHU_FILE_EVIDENCE_DIR or "data/ocr_evidence"))
    task_dir = evidence_base / str(task_id or "unknown_task")
    task_dir.mkdir(parents=True, exist_ok=True)
    suffix = ".png" if attachment.attachment_type == "image" else ".bin"
    filename = _safe_filename(attachment.file_name, suffix)
    target = task_dir / filename
    with open(target, "wb") as f:
        f.write(bytes(data))

    digest = hashlib.sha256(bytes(data)).hexdigest()
    rel_path = os.path.relpath(str(target), os.getcwd())
    return DownloadedFeishuFile(
        document_id=f"feishu-file-{uuid4().hex[:12]}",
        file_name=filename,
        mime_type=attachment.mime_type,
        file_path=rel_path,
        source="feishu",
        file_size=file_size,
        file_hash=digest,
        attachment_type=attachment.attachment_type,
    )


def build_ocr_input_from_downloaded_file(
    downloaded_file: DownloadedFeishuFile,
    requested_by: str,
    hint_document_type: str,
) -> OCRDocumentInput:
    return OCRDocumentInput(
        document_id=downloaded_file.document_id,
        file_name=downloaded_file.file_name,
        mime_type=downloaded_file.mime_type,
        file_path=downloaded_file.file_path,
        source="feishu",
        requested_by=str(requested_by or "feishu_user"),
        hint_document_type=str(hint_document_type or "unknown"),
    )
