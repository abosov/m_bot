from __future__ import annotations

import os
import re
import uuid
from pathlib import Path

from fastapi import UploadFile


_FILENAME_SAFE_RE = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_filename(filename: str | None) -> str:
    raw = (filename or "").strip()
    raw = os.path.basename(raw)
    raw = raw.replace("/", "_").replace("\\", "_")
    raw = raw.replace("..", "_")
    safe = _FILENAME_SAFE_RE.sub("_", raw).strip("._")
    if not safe:
        safe = "file"
    return safe[:120]


async def save_upload_file_atomic(
    upload: UploadFile,
    *,
    uploads_root: Path,
    key_prefix: str,
    max_bytes: int,
) -> tuple[str, str]:
    safe_name = sanitize_filename(upload.filename)
    final_name = f"{uuid.uuid4().hex}_{safe_name}"
    relative_key = f"{key_prefix}/{final_name}"
    final_path = uploads_root / relative_key
    final_path.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = final_path.parent / f".{uuid.uuid4().hex}.tmp"

    size = 0
    try:
        with tmp_path.open("wb") as fh:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    raise ValueError("file_too_large")
                fh.write(chunk)
        os.replace(tmp_path, final_path)
    finally:
        await upload.close()
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)

    return relative_key, safe_name


def save_bytes_atomic(*, uploads_root: Path, file_key: str, payload: bytes) -> None:
    final_path = uploads_root / file_key
    final_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = final_path.parent / f".{uuid.uuid4().hex}.tmp"
    try:
        with tmp_path.open("wb") as fh:
            fh.write(payload)
        os.replace(tmp_path, final_path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def stage_bytes_temp(*, uploads_root: Path, key_prefix: str, payload: bytes, suffix: str = ".tmp") -> str:
    temp_key = f"{key_prefix}/.{uuid.uuid4().hex}{suffix}"
    save_bytes_atomic(uploads_root=uploads_root, file_key=temp_key, payload=payload)
    return temp_key


def promote_staged_file(*, uploads_root: Path, staged_key: str, final_key: str) -> None:
    staged_path = uploads_root / staged_key
    final_path = uploads_root / final_key
    final_path.parent.mkdir(parents=True, exist_ok=True)
    os.replace(staged_path, final_path)


def remove_file_if_exists(*, uploads_root: Path, file_key: str) -> None:
    path = uploads_root / file_key
    try:
        path.unlink(missing_ok=True)
    except OSError:
        return
