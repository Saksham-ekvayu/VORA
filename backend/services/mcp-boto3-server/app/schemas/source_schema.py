from pydantic import BaseModel


class SourceConfigRequest(BaseModel):
    control_name: str
    dp_name: str
    organization_name: str
    source_type: str
    source_name: str | None = None
    config_json: dict


class DeploymentPointModel(BaseModel):
    id: str
    name: str
    status: str
    path: str
    weightage: int
    remark: str | None = ""


class ControlModel(BaseModel):
    id: str
    name: str
    description: str | None = ""
    deployment_points: list[DeploymentPointModel] = []


class SectionModel(BaseModel):
    id: str
    name: str
    controls: list[ControlModel] = []


class SectionsConfigRequest(BaseModel):
    sections: list[SectionModel]


# ---------- combined ----------


class FullConfigRequest(BaseModel):
    source_config: SourceConfigRequest
    sections_config: SectionsConfigRequest
