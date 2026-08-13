from pydantic import BaseModel
from typing import Literal


class StartSchedulerRequest(BaseModel):
    source: Literal["aws", "local", "gitlab"]
    scheduler_type: Literal["interval", "cron"] = "interval"
    minutes: int | None = 1
    hour: int | None = None
    minute: int | None = None