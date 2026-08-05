"""Request body schemas for framework-service routes."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RejectFrameworkBody(BaseModel):
    rejectionReason: str | None = Field(default=None, max_length=500)


class AssignFrameworkToCustomerBody(BaseModel):
    customerId: str
    tenantId: str
    frameworkIds: list[str]


class DeploymentPointIn(BaseModel):
    id: str | None = None
    name: str
    status: str | None = None
    path: str | None = None
    weightage: float | None = None
    remark: str | None = None


class AddControlBody(BaseModel):
    sectionId: str | None = None
    newSection: str | None = None
    name: str
    description: str = ""
    deployment_points: list[DeploymentPointIn] = Field(default_factory=list)


class UpdateControlBody(BaseModel):
    name: str | None = None
    description: str | None = None
    deployment_points: list[DeploymentPointIn] | None = None


class UpdateControlWeightageBody(BaseModel):
    weightage: float
