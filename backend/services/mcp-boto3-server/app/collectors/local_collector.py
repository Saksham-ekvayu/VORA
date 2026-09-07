import logging
import os
import shutil
from pathlib import Path, PureWindowsPath

from app.utils.live_logs import add_live_log

BASE_DIR = Path(__file__).resolve().parents[4]
UPLOAD_DIR = BASE_DIR / "shared" / "uploads" / "file" / "deployment-document"
DOCS_ROOT = BASE_DIR.parent / "docs"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)


def _resolve_directory(directory: str) -> Path | None:
    """
    Resolve a deployment point's stored directory to a real path on THIS machine.

    Deployment points may carry an absolute path recorded on whichever
    machine/checkout created them (e.g. "C:\\dev\\VORA\\docs\\..."), which
    rarely exists elsewhere. If the literal path is missing, fall back to
    re-anchoring it under this machine's own docs folder — first by trying
    its "docs\\..." tail as-is, then (since the folder structure under docs
    can itself differ between checkouts, e.g. an extra subfolder) by
    searching for a directory matching just its last path segment anywhere
    under the docs root.
    """
    path = Path(directory)

    if path.is_dir():
        return path

    parts = PureWindowsPath(directory).parts
    if "docs" not in parts:
        return None

    tail = parts[parts.index("docs") + 1 :]

    fallback = DOCS_ROOT.joinpath(*tail)
    if fallback.is_dir():
        return fallback

    target_name = tail[-1] if tail else None
    if target_name and DOCS_ROOT.is_dir():
        for candidate in DOCS_ROOT.rglob(target_name):
            if candidate.is_dir():
                return candidate

    return None


def fetch_local_files(directory, allowed_extensions=None):
    files = []

    resolved = _resolve_directory(directory)

    if resolved is None:
        logger.warning(f"Local source directory not found on this machine: {directory}")
        add_live_log(f"Local source directory not found on this machine: {directory}")
        return files

    for root, _, filenames in os.walk(resolved):
        for file in filenames:
            src = Path(root) / file

            if allowed_extensions and not file.lower().endswith(tuple(allowed_extensions)):
                continue

            dst = UPLOAD_DIR / file

            if not dst.exists():
                shutil.copy2(src, dst)

            files.append(
                {
                    "source": "local",
                    "file_name": file,
                    "file_path": str(src),
                    "saved_path": str(dst),
                    "type": "file",
                }
            )

    return files
