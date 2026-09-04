import logging
from datetime import datetime

import app.utils.live_logs as live_log_manager
from app.mcp_server.controller import run_pipeline
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

live_logs = []

scheduler = AsyncIOScheduler()

current_scheduler_config = {"scheduler_type": "interval", "minutes": 1}


async def start_dynamic_scheduler(payload: dict):
    scheduler_type = payload.get("scheduler_type", "interval")

    scheduler.remove_all_jobs()

    if scheduler_type == "interval":
        scheduler.add_job(
            run_pipeline,
            "interval",
            minutes=payload.get("minutes", 1),
            id="mcp_pipeline",
            replace_existing=True,
            next_run_time=datetime.now(),  # fire immediately, then repeat on the interval
        )
    else:
        scheduler.add_job(
            run_pipeline,
            "cron",
            hour=payload.get("hour", 0),
            minute=payload.get("minute", 0),
            id="mcp_pipeline",
            replace_existing=True,
            next_run_time=datetime.now(),  # fire immediately, then follow the cron schedule
        )

    if not scheduler.running:
        try:
            scheduler.start()
        except Exception as e:
            logging.exception("Failed to start scheduler")
            return {"status": False, "message": f"Failed to start scheduler: {e}"}

    return {
        "status": True,
        "message": "Scheduler started - sources are auto-detected from the LIVE deployment framework",
    }


def stop_scheduler():
    if scheduler.running == False:
        return {"Status": False, "Message": "Scheduler is already stop"}
    if scheduler.running:
        scheduler.shutdown(wait=False)
        live_log_manager.live_logs.clear()

    return {"status": True, "message": "Scheduler stopped successfully"}


def scheduler_status():

    jobs = scheduler.get_jobs()

    return {
        "running": scheduler.running,
        "jobs": [job.id for job in jobs],
        "config": current_scheduler_config,
    }


def add_live_log(message):

    live_logs.append(message)

    # STORE ONLY LAST 100 LOGS
    if len(live_logs) > 1000:
        live_logs.pop(0)

    logging.info(message)
