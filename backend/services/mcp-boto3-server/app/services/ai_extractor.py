import requests

BASE_URL = "http://localhost:7007"


def trigger_ai_extraction(document_id: str):
    url = f"{BASE_URL}/api/extract/deployment-document/" f"{document_id}/ai-extract"

    response = requests.post(
        url,
        headers={"accept": "application/json"},
        timeout=120,
    )

    try:
        return response.json()
    except Exception:
        return {
            "status_code": response.status_code,
            "text": response.text,
        }
