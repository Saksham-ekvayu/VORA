import os

import requests

AGENT_API = os.getenv("AGENT_API", "http://localhost:7000/api/load/upload")


def call_agent(payload: dict, agent_name: str):
    body = {
        "id": payload["id"],
        "agent_name": agent_name,
        "framework_name": payload["framework_name"],
        "package_version": payload["package_version"],
        "merge_document": payload["merge_document"],
        "deployment_framework": payload["deployment_framework"],
        "file_path": payload["file_path"],
    }

    response = requests.post(AGENT_API, json=body, timeout=60)
    return response.json()
