from fastapi import APIRouter,Depends
from fastapi.responses import FileResponse
import os
from app.services.downloader import download_file
from app.utils.live_logs import live_logs
from app.schemas.source_schema import FullConfigRequest
from app.db.queries import save_full_config
from sqlalchemy.ext.asyncio import AsyncSession
from vora_shared.database import get_session
from app.scheduler import (
    start_dynamic_scheduler,
    stop_scheduler,
    scheduler_status
)
from app.schemas.scheduler_schema import StartSchedulerRequest
from app.collectors.collector_manager import collect_files
router = APIRouter(
    prefix="/scheduler",
    tags=["Scheduler APIs"]
)


@router.post("/start")
def start_scheduler(payload: StartSchedulerRequest):
    return start_dynamic_scheduler(payload.model_dump())

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
async def create_full_config(
    request: FullConfigRequest,
    db: AsyncSession = Depends(get_session),
):
    result = await save_full_config(db, request)

    return {
        "status": True,
        "message": "Configuration saved successfully",
        "source_config_id": result["source_config_id"],
    }