# collectors/gitlab_collector.py

import requests

def fetch_gitlab_files(project_id, token):
    url = f"https://gitlab.com/api/v4/projects/{project_id}/repository/tree"
    headers = {"PRIVATE-TOKEN": token}

    response = requests.get(url, headers=headers).json()

    files = []
    for item in response:
        files.append({
            "source": "gitlab",
            "file_name": item["name"],
            "file_path": item["path"],
            "type": item["type"]
        })

    return files