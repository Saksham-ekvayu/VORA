import os

def fetch_local_files(directory, allowed_extensions=None):
    if not os.path.isdir(directory):
        raise ValueError(f"Directory not accessible (mount may be down): {directory}")

    # extra check: mounted drives that are disconnected sometimes still
    # "exist" as a path but list as empty — do a quick access test
    try:
        os.listdir(directory)
    except (PermissionError, OSError) as e:
        raise ValueError(f"Cannot access directory (mount may have dropped): {directory} — {e}")

    files = []
    for root, dirs, filenames in os.walk(directory):
        for file in filenames:
            file_path = os.path.join(root, file)
            if allowed_extensions:
                if not file.lower().endswith(tuple(allowed_extensions)):
                    continue
            files.append({
                "source": "local",
                "file_name": file,
                "file_path": file_path,
                "type": "file"
            })
    return files