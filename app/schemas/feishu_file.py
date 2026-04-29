from __future__ import annotations

from pydantic import BaseModel, Field


class FeishuAttachmentMeta(BaseModel):
    attachment_type: str = Field(default="file", min_length=1)
    message_id: str = Field(default="", min_length=1)
    file_key: str = ""
    image_key: str = ""
    file_name: str = ""
    mime_type: str = Field(default="application/octet-stream", min_length=1)
    size_bytes: int = Field(default=0, ge=0)


class DownloadedFeishuFile(BaseModel):
    document_id: str = Field(default="", min_length=1)
    file_name: str = Field(default="", min_length=1)
    mime_type: str = Field(default="application/octet-stream", min_length=1)
    file_path: str = Field(default="", min_length=1)
    source: str = Field(default="feishu", min_length=1)
    file_size: int = Field(default=0, ge=0)
    file_hash: str = ""
    attachment_type: str = Field(default="file", min_length=1)
