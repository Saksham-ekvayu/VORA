import os
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[4]
UPLOAD_DIR = BASE_DIR / "shared" / "uploads" / "file" / "deployment-document"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def fetch_local_files(directory, allowed_extensions=None):
    files = []

    for root, _, filenames in os.walk(directory):
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
