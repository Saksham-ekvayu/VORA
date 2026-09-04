import os

import requests

# Routed through the API gateway to compliance-agent-service's
# POST /api/compliance-agent/evaluate/{dd_id} endpoint.
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000")


def call_agent(payload: dict, _agent_name: str):
    dd_id = payload["deployment_document_id"]

    url = f"{GATEWAY_URL}/api/compliance-agent/evaluate/{dd_id}"

    response = requests.post(url, timeout=60)
    return response.json()
