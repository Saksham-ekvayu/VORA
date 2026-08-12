from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import utils.live_logs as live_log_manager
from mcp_server.controller import run_pipeline
import logging  
live_logs = []

scheduler = BackgroundScheduler()

current_scheduler_config = {
    "source": "aws",
    "scheduler_type": "interval",
    "minutes": 1
}


def start_dynamic_scheduler(config):
    """
    Start scheduler dynamically
    """

    global current_scheduler_config

    current_scheduler_config = config

    if scheduler.running:
        scheduler.remove_all_jobs()

    scheduler_type = config.get("scheduler_type")

    if scheduler_type == "interval":

        minutes = config.get("minutes", 1)

        scheduler.add_job(
            run_pipeline,
            IntervalTrigger(minutes=minutes),
            kwargs={"source": config.get("source")},
            id="pipeline_job"
        )

    elif scheduler_type == "cron":

        scheduler.add_job(
            run_pipeline,
            CronTrigger(
                hour=config.get("hour"),
                minute=config.get("minute")
            ),
            kwargs={"source": config.get("source")},
            id="pipeline_job"
        )

    if not scheduler.running:
        scheduler.start()

    return {
        "status": True,
        "message": "Scheduler started successfully",
        "config": config
    }


def stop_scheduler():
    if scheduler.running==False:
        return{
            "Status": False,
            "Message":"Scheduler is already stop"
        }
    if scheduler.running:
        scheduler.shutdown(wait=False)
        live_log_manager.live_logs.clear()

    return {
        "status": True,
        "message": "Scheduler stopped successfully"
    }


def scheduler_status():

    jobs = scheduler.get_jobs()

    return {
        "running": scheduler.running,
        "jobs": [job.id for job in jobs],
        "config": current_scheduler_config
    }
def add_live_log(message):

    live_logs.append(message)

    # STORE ONLY LAST 100 LOGS
    if len(live_logs) > 1000:
        live_logs.pop(0)

    logging.info(message)