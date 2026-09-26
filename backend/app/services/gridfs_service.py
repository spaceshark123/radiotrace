"""GridFS helpers for uploading and streaming supported audio formats."""

from __future__ import annotations

import io
import mimetypes
from typing import BinaryIO

from bson import ObjectId
from bson.errors import InvalidId
from gridfs.errors import NoFile

from app.services.mongo import get_gridfs_bucket


class AudioNotFoundError(LookupError):
    """Raised when a GridFS audio document does not exist."""


def audio_content_type(filename: str) -> str:
    """Return the MIME type used for a supported filename."""
    if filename.lower().endswith(".m4a"):
        return "audio/mp4"
    if filename.lower().endswith(".mp3"):
        return "audio/mpeg"
    return mimetypes.guess_type(filename)[0] or "application/octet-stream"


def upload_mp3(
    data: bytes | BinaryIO,
    filename: str = "clip.mp3",
    metadata: dict | None = None,
) -> str:
    """Store audio bytes in GridFS and return the file id as a hex string."""
    bucket = get_gridfs_bucket()
    stream = data if hasattr(data, "read") else io.BytesIO(data)
    file_id = bucket.upload_from_stream(
        filename,
        stream,
        metadata={"contentType": audio_content_type(filename), **(metadata or {})},
    )
    return str(file_id)


def open_mp3_stream(file_id: str):
    """Open a download stream for a stored MP3. Caller must close the stream."""
    bucket = get_gridfs_bucket()
    try:
        oid = ObjectId(file_id)
    except (InvalidId, TypeError) as exc:
        raise AudioNotFoundError(f"Invalid audio id: {file_id}") from exc
    try:
        return bucket.open_download_stream(oid)
    except NoFile as exc:
        raise AudioNotFoundError(f"Audio not found: {file_id}") from exc


def download_mp3(file_id: str) -> bytes:
    """Read an entire MP3 from GridFS into memory (used by tests and the pipeline)."""
    download_stream = open_mp3_stream(file_id)
    try:
        return download_stream.read()
    finally:
        download_stream.close()


def delete_mp3(file_id: str) -> None:
    bucket = get_gridfs_bucket()
    try:
        bucket.delete(ObjectId(file_id))
    except (InvalidId, NoFile, TypeError):
        raise AudioNotFoundError(f"Audio not found: {file_id}")
