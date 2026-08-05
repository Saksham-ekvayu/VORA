import hashlib
import os
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Any

from vora_shared.ids import new_id

_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
UPLOAD_BASE_PATH = os.environ.get("DEPLOYMENT_UPLOAD_BASE_PATH", str(_BACKEND_ROOT / "shared" / "uploads"))
UPLOAD_ROOT = _BACKEND_ROOT / "shared" / "uploads"

from vora_shared.config import get_settings

_settings = get_settings()
ALLOWED_EXTENSIONS = set(_settings.allowed_extensions.split(","))
MAX_FILE_SIZE = _settings.max_file_size
CONTENT_TYPES = {
    "pdf": "application/pdf",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
PREVIEW_MIME_TYPES = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
    "svg": "image/svg+xml",
    "txt": "text/plain",
    "csv": "text/csv",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "doc": "application/msword",
}

@dataclass
class FilePathInfo:
    filename: str
    relative_path: str
    absolute_path: str
    directory: str

@dataclass
class FramworkFilePathInfo:
    filename: str
    file_id: str
    relative_path: Path
    absolute_path: Path
    directory: Path
    sub_dir: Path


def generate_deployment_file_path(
    original_name: str, user_id: str, category: str = "document", version: str = None
) -> FilePathInfo:
    ext = Path(original_name).suffix
    name_without_ext = Path(original_name).stem
    timestamp = int(time.time() * 1000)
    filename = f"{name_without_ext}-{timestamp}{ext}"
    if version:
        sub_dir = os.path.join("file", category, _sanitize_version(version), user_id)
    else:
        sub_dir = os.path.join("file", category, user_id)
    relative_path = os.path.join(sub_dir, filename)
    absolute_path = os.path.join(UPLOAD_BASE_PATH, relative_path)
    return FilePathInfo(
        filename=filename,
        relative_path=relative_path,
        absolute_path=absolute_path,
        directory=os.path.dirname(absolute_path),
    )

def _sanitize_version(version: str) -> str:
    sanitized = version
    for ch in [":", "/", "\\", "?", "*", '"', "<", ">", "|"]:
        sanitized = sanitized.replace(ch, "-")
    return sanitized


def generate_framework_file_path(
    original_name: str, user_id: str, framework_version: str = None
) -> FramworkFilePathInfo:
    ext = Path(original_name).suffix
    name_without_ext = Path(original_name).stem
    timestamp = int(time.time() * 1000)
    filename = f"{name_without_ext}-{timestamp}{ext}"
    file_id = f"{name_without_ext}-{timestamp}"
    if framework_version:
        sub_dir = Path("file/framework") / _sanitize_version(framework_version) / user_id
    else:
        sub_dir = Path("file/framework") / user_id
    relative_path = sub_dir / filename
    absolute_path = UPLOAD_ROOT / relative_path
    return FramworkFilePathInfo(
        filename=filename,
        file_id=file_id,
        relative_path=relative_path,
        absolute_path=absolute_path,
        directory=absolute_path.parent,
        sub_dir=sub_dir,
    )


def save_file(file_data: bytes, file_path: Path | str) -> bool:
    try:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            f.write(file_data)
        return True
    except OSError as exc:
        print(f"Error saving file: {exc}")
        return False


def delete_file(file_path: Path | str) -> bool:
    try:
        path = Path(file_path)
        if path.exists():
            path.unlink()
            return True
        return False
    except OSError as exc:
        print(f"Error deleting file: {exc}")
        return False


def calculate_file_hash(file_path: Path | str) -> str:
    try:
        with open(file_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError as exc:
        print(f"Error calculating file hash: {exc}")
        return ""


def calculate_buffer_hash(buffer: bytes) -> str:
    return hashlib.sha256(buffer).hexdigest()
calculate_bytes_hash = calculate_buffer_hash


def file_exists(file_path: Path | str) -> bool:
    return Path(file_path).exists()


def read_file(file_path: Path | str) -> bytes | None:
    try:
        path = Path(file_path)
        if path.exists():
            return path.read_bytes()
        return None
    except OSError as exc:
        print(f"Error reading file: {exc}")
        return None


def get_file_url(filename: str) -> str:
    return f"/api/v1/frameworks/files/{filename}"


def resolve_actual_file_path(file_url: str, user_id: str) -> str | None:
    if not file_url.startswith("/api/"):
        return file_url
    filename = os.path.basename(file_url)
    base_upload_dir = UPLOAD_ROOT / user_id
    try:
        if base_upload_dir.exists():
            for framework_dir in base_upload_dir.iterdir():
                candidate = framework_dir / filename
                if candidate.exists():
                    return str(candidate)
    except OSError as exc:
        print(f"Error searching for file {filename}: {exc}")
    return None

def validate_uploaded_file(filename: str, size: int) -> dict[str, Any]:
    max_size = MAX_FILE_SIZE
    allowed = [ext if ext.startswith(".") else f".{ext}" for ext in ALLOWED_EXTENSIONS]

    # Validate file size
    if size > max_size:
        return {
            "isValid": False,
            "status": 400,
            "message": f"File size exceeds maximum allowed size of {format_file_size(max_size)}"
        }

    # Validate file extension
    ext = Path(filename).suffix.lower()
    if ext not in allowed:
        return {
            "isValid": False,
            "status": 400,
            "message": f"Invalid file type. Allowed types: {', '.join(sorted([e.lstrip('.') for e in allowed]))}"
        }

    return {"isValid": True, "message": None, "status": 200}

def ensure_directory_exists(directory_path: str) -> None:
    os.makedirs(directory_path, exist_ok=True)

def format_file_size(num_bytes: int) -> str:
    sizes = ["Bytes", "KB", "MB", "GB"]
    if not num_bytes:
        return "0 Bytes"
    import math
    i = math.floor(math.log(num_bytes) / math.log(1024))
    return f"{round((num_bytes / (1024 ** i)) * 100) / 100} {sizes[i]}"


