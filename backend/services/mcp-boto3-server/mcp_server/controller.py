import requests
import os
import logging

from collectors.collector_manager import collect_files
from services.downloader import download_file
from db.queries import is_processed, mark_processed
from utils.live_logs import add_live_log
import logging
import os

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/pipeline.log"),
        logging.StreamHandler()
    ]
)

AGENT_API = os.getenv(
    "AGENT_API",
    "http://192.168.1.30:7000/api/load/upload"
)
def detect_agent(file_path):
    if file_path.endswith(".log"):
        return "Compliance_Audit_Agent"
    elif file_path.endswith(".pdf"):
        return "Policy_Enforcement_Agent"
    elif file_path.endswith((".png", ".jpg")):
        return "Security_Training_Agent"
    else:
        return "Compliance_Reporting_Agent"


def call_agent(file_path, agent_name):
    try:
        with open(file_path, "rb") as f:
            files = {
                "file": (os.path.basename(file_path), f)
            }
            data = {
                "agent_name": agent_name
            }

            response = requests.post(AGENT_API, files=files, data=data)

        return response.json()

    except Exception as e:
        return {"error": str(e)}


def run_pipeline(source="aws"):

    CONFIG = {

        "aws": {
            "bucket": "my-audit-logs-bucket-test",
            "prefix": "ec2-logs/"
        },

        "local": {
            "directory": "C:/logs",
            "extensions": [".log", ".txt"]
        },

        "gitlab": {
            "project_id": "123456",
            "token": "YOUR_GITLAB_TOKEN"
        }
    }

    files = collect_files(source, CONFIG.get(source, {}))

    logging.info(f"Running pipeline for source: {source}")
    add_live_log(f"Running pipeline for source: {source}")
    logging.info(f"Total files fetched: {len(files)}")
    add_live_log(f"Total files fetched: {len(files)}")

    for f in files:

        path = f["file_path"]

        if path.endswith("/"):
            continue

        try:

            logging.info(f"Processing: {path}")
            add_live_log(f"Processing: {path}")

            if path.startswith("s3://"):
                local_path = download_file(path)
            else:
                local_path = path

            agent_name = detect_agent(local_path)

            logging.info(f"Using Agent: {agent_name}")
            add_live_log(f"Using Agent: {agent_name}")

            response = call_agent(local_path, agent_name)

            logging.info(f"Agent Response: {response}")
            add_live_log(f"Agent Response: {response}")

            mark_processed(path)

        except Exception as e:
            logging.error(f"Error processing {path}: {e}")