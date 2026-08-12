from typing import List, Optional
from pydantic import BaseModel


class SourceConfigRequest(BaseModel):
    control_name: str
    dp_name: str
    organization_name: str
    source_type: str
    source_name: Optional[str] = None
    config_json: dict


class DeploymentPointModel(BaseModel):
    id: str
    name: str
    status: str
    path: str
    weightage: int
    remark: Optional[str] = ""


class ControlModel(BaseModel):
    id: str
    name: str
    description: Optional[str] = ""
    deployment_points: List[DeploymentPointModel] = []


class SectionModel(BaseModel):
    id: str
    name: str
    controls: List[ControlModel] = []


class SectionsConfigRequest(BaseModel):
    sections: List[SectionModel]


# ---------- combined ----------

class FullConfigRequest(BaseModel):
    source_config: SourceConfigRequest
    sections_config: SectionsConfigRequest