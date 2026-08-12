from fastapi import APIRouter
from fastapi.responses import FileResponse
import os
from fastapi.responses import FileResponse
from services.downloader import download_file
from utils.live_logs import live_logs
from schemas.source_schema import FullConfigRequest
from db.queries import save_full_config
from scheduler import (
    start_dynamic_scheduler,
    stop_scheduler,
    scheduler_status
)
from collectors.collector_manager import collect_files
router = APIRouter(
    prefix="/scheduler",
    tags=["Scheduler APIs"]
)


@router.post("/start")
def start_scheduler(payload: dict):

    """
    Example Payload:

    {
        "source": "aws",
        "scheduler_type": "interval",
        "minutes": 1
    }

    OR

    {
        "source": "gitlab",
        "scheduler_type": "cron",
        "hour": 14,
        "minute": 30
    }
    """

    return start_dynamic_scheduler(payload)


@router.get("/stop")
def stop_scheduler_api():

    return stop_scheduler()


@router.get("/status")
def scheduler_status_api():

    return scheduler_status()


@router.get("/generate-report")
def generate_report():

    log_file = "logs/pipeline.log"

    if not os.path.exists(log_file):

        return {
            "status": False,
            "message": "No logs found"
        }

    with open(log_file, "r") as file:
        content = file.read()

    report_path = "reports/pipeline_report.txt"

    os.makedirs("reports", exist_ok=True)

    with open(report_path, "w") as report:
        report.write(content)

    return {
        "status": True,
        "message": "Report generated successfully",
        "report_path": report_path
    }


@router.get("/download-report")
def download_report():

    report_path = "reports/pipeline_report.txt"

    if not os.path.exists(report_path):

        return {
            "status": False,
            "message": "Report not found"
        }

    return FileResponse(
        path=report_path,
        filename="pipeline_report.txt",
        media_type="application/octet-stream"
    )

@router.get("/list-downloaded-files")
def list_downloaded_files():

    folder = "aws_files"

    if not os.path.exists(folder):

        return {
            "status": False,
            "message": "No files found"
        }

    files = []

    for file in os.listdir(folder):

        file_path = os.path.join(folder, file)

        files.append({
            "file_name": file,
            "file_path": file_path,
            "size": os.path.getsize(file_path)
        })

    return {
        "status": True,
        "total_files": len(files),
        "files": files
    }

@router.get("/download-file")
def download_file_api(file_name: str):

    file_path = os.path.join(
        "aws_files",
        file_name
    )

    if not os.path.exists(file_path):

        return {
            "status": False,
            "message": "File not found"
        }

    return FileResponse(
        path=file_path,
        filename=file_name,
        media_type="application/octet-stream"
    )

@router.get("/live-logs")
def get_live_logs():

    return {
        "status": True,
        "total_logs": len(live_logs),
        "logs": live_logs
    }

@router.post("/save-config")
def create_full_config(request: FullConfigRequest):
    result = save_full_config(request)

    source_ok = result["source_config_id"] is not None
    sections_ok = result["sections_success"]

    if not source_ok and not sections_ok:
        return {
            "status": False,
            "message": "Failed to save source configuration and sections configuration"
        }

    if not source_ok:
        return {
            "status": False,
            "message": "Sections configuration saved, but source configuration failed",
            "source_config_id": None
        }

    if not sections_ok:
        return {
            "status": False,
            "message": "Source configuration saved, but sections configuration failed",
            "source_config_id": result["source_config_id"]
        }

    # both saved -- now attempt to run the collector using source_config's
    # source_type + config_json
    try:
        files = collect_files(
            request.source_config.source_type,
            request.source_config.config_json
        )
    except ValueError as e:
        return {
            "status": False,
            "message": f"Configuration saved, but collection failed: {e}",
            "source_config_id": result["source_config_id"]
        }
    except Exception as e:
        # catches unexpected errors from boto3 / requests / os.walk etc.
        # (e.g. bad credentials, network failure, permission denied)
        return {
            "status": False,
            "message": f"Configuration saved, but collection raised an unexpected error: {e}",
            "source_config_id": result["source_config_id"]
        }

    return {
        "status": True,
        "message": "Configuration saved and files collected successfully",
        "source_config_id": result["source_config_id"],
        "file_count": len(files),
        "files": files
    }