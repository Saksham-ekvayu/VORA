"""Avatar upload handling — mirrors `upload.middleware.js` (multer disk
storage, 5MB limit, jpeg/png/gif/webp only) from profile-service-main."""

import mimetypes
import secrets
import time
from pathlib import Path

from fastapi import UploadFile

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5MB

# services/profile-service/uploads — served publicly by main.py's StaticFiles mount.
UPLOADS_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"


class AvatarUploadError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


async def save_avatar(upload: UploadFile, subdir: str) -> str:
    """Validate + persist an avatar upload under `uploads/{subdir}/avatar/`.

    Returns the public URL (e.g. `/uploads/<id>/avatar/<file>`), matching
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
    filename = f"{int(time.time() * 1000)}-{secrets.token_hex(4)}{ext}"

    directory = UPLOADS_DIR / subdir / "avatar"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / filename).write_bytes(data)

    return f"/uploads/{subdir}/avatar/{filename}"


def delete_avatar_file(public_url: str | None) -> None:
    """Best-effort delete of a previous avatar (fire-and-forget, like Node's
    `fs.unlink(path, () => {})`)."""
    if not public_url:
        return
    relative = public_url.replace("/uploads/", "", 1)
    file_path = UPLOADS_DIR / relative
    try:
        file_path.unlink(missing_ok=True)
    except OSError:
        pass
