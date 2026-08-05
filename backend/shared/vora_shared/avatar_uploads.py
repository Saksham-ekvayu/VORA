import mimetypes
import secrets
import time
from pathlib import Path

from fastapi import UploadFile

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5MB

from vora_shared.file_storage import UPLOAD_ROOT


class AvatarUploadError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


async def save_avatar(upload: UploadFile, subdir: str) -> str:
    """Validate + persist an avatar upload under `uploads/avatar/{subdir}/`.

    Returns the public URL (e.g. `/uploads/avatar/<subdir>/<file>`), matching
    Node's stored `avatarUrl` path exactly.
    """
    content_type = upload.content_type or mimetypes.guess_type(upload.filename or "")[0] or ""
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise AvatarUploadError("Invalid file type. Allowed types: jpeg, png, gif, webp")

    data = await upload.read()
    if len(data) > MAX_AVATAR_SIZE:
        raise AvatarUploadError("File too large. Maximum size is 5MB")
    if not data:
        raise AvatarUploadError("Please select an image file to upload")

    ext = Path(upload.filename or "").suffix or ".jpg"
    name_without_ext = Path(upload.filename or "image").stem
    timestamp = int(time.time() * 1000)
    filename = f"{name_without_ext}-{timestamp}{ext}"

    directory = UPLOAD_ROOT / "avatar" / subdir
    directory.mkdir(parents=True, exist_ok=True)
    (directory / filename).write_bytes(data)

    return f"/uploads/avatar/{subdir}/{filename}"


def delete_avatar_file(public_url: str | None) -> None:
    """Best-effort delete of a previous avatar."""
    if not public_url:
        return
    relative = public_url.replace("/uploads/", "", 1)
    file_path = UPLOAD_ROOT / relative
    try:
        file_path.unlink(missing_ok=True)
    except OSError:
        pass
