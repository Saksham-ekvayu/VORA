# pipeline/processor.py

def process_files(files):
    results = []

    for file in files:
        results.append({
            "file": file["name"],
            "status": "processed"
        })

    return results