# normalizer/normalize.py
def normalize_data(data):
    normalized = []

    for item in data:
        normalized.append(
            {
                "source": item.get("source"),
                "name": item.get("file_name"),
                "path": item.get("file_path"),
                "type": item.get("type"),
            }
        )

    return normalized
