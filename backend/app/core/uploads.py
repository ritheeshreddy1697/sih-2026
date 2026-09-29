from __future__ import annotations

import io
import re
import zipfile
from pathlib import PurePath
from urllib.parse import quote

from fastapi import HTTPException, UploadFile

DOCUMENT_TYPES = {"application/pdf", "image/jpeg", "image/png"}
FACE_IMAGE_TYPES = {"image/jpeg", "image/png"}
RESUME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
ASSIGNMENT_TYPES = DOCUMENT_TYPES | {
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
LESSON_MEDIA_TYPES = {
    "application/pdf",
    "video/mp4",
    "video/webm",
    "audio/mpeg",
    "audio/wav",
    "audio/ogg",
}


def safe_filename(filename: str | None, fallback: str = "upload") -> str:
    candidate = PurePath((filename or fallback).replace("\\", "/")).name
    candidate = re.sub(r"[\x00-\x1f\x7f\";]", "", candidate).strip(" .")
    return (candidate or fallback)[:255]


def attachment_header(filename: str, *, inline: bool = False) -> str:
    disposition = "inline" if inline else "attachment"
    return f"{disposition}; filename*=UTF-8''{quote(safe_filename(filename))}"


def _is_docx(content: bytes) -> bool:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            entries = archive.infolist()
            if len(entries) > 500 or sum(item.file_size for item in entries) > 25 * 1024 * 1024:
                return False
            names = {item.filename for item in entries}
            return "[Content_Types].xml" in names and any(
                name.startswith("word/") for name in names
            )
    except (OSError, zipfile.BadZipFile):
        return False


def content_matches_type(content: bytes, content_type: str) -> bool:
    signatures = {
        "application/pdf": content.startswith(b"%PDF-"),
        "image/jpeg": content.startswith(b"\xff\xd8\xff"),
        "image/png": content.startswith(b"\x89PNG\r\n\x1a\n"),
        "application/msword": content.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"),
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": _is_docx(
            content
        ),
        "video/mp4": len(content) >= 12 and content[4:8] == b"ftyp",
        "video/webm": content.startswith(b"\x1aE\xdf\xa3"),
        "audio/mpeg": content.startswith(b"ID3")
        or (len(content) >= 2 and content[0] == 0xFF and content[1] & 0xE0 == 0xE0),
        "audio/wav": len(content) >= 12
        and content.startswith(b"RIFF")
        and content[8:12] == b"WAVE",
        "audio/ogg": content.startswith(b"OggS"),
    }
    return signatures.get(content_type, False)


async def read_validated_upload(
    upload: UploadFile,
    *,
    allowed_types: set[str],
    maximum_bytes: int,
    kind: str,
) -> tuple[bytes, str, str]:
    content_type = (upload.content_type or "").split(";", 1)[0].strip().lower()
    if content_type not in allowed_types:
        raise HTTPException(status_code=422, detail=f"Unsupported {kind} file type")
    content = await upload.read(maximum_bytes + 1)
    if not content:
        raise HTTPException(status_code=422, detail=f"{kind.capitalize()} file is empty")
    if len(content) > maximum_bytes:
        size_mb = maximum_bytes // (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"{kind.capitalize()} must be {size_mb} MB or smaller",
        )
    if not content_matches_type(content, content_type):
        raise HTTPException(
            status_code=422,
            detail=f"{kind.capitalize()} content does not match its declared file type",
        )
    return content, content_type, safe_filename(upload.filename, kind)
