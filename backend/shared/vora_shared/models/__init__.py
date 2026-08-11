"""Shared SQLAlchemy models for the unified Postgres `vora` database."""

from vora_shared.models.ai_tables import (
    AgentPrompt,
 
    EvidenceOutput,
   
    UploadedFile,
)
from vora_shared.models.customer import AddressBlock, Customer, CustomerAddress, CustomerCreatedBy
from vora_shared.models.deployment_document import DeploymentDocument, DeploymentDocumentFileVersion
from vora_shared.models.deployment_framework import (
    DeploymentFramework,
    ExpertReview,
    FrameworkPackageDocument,
    PackageVersion,
)
from vora_shared.models.deployment_package_merge import DeploymentPackageMerge
from vora_shared.models.document_extraction import (
    AiExtractionInfo,
    DocumentExtraction,
    ExtractionControlItem,
    ExtractionControls,
    ExtractionDeploymentPoint,
    ExtractionSection,
    ExtractionStatusHistory,
)
from vora_shared.models.framework import Framework
from vora_shared.models.framework_access import FrameworkAccess
from vora_shared.models.framework_assignment import (
    AssignmentControl,
    AssignmentCustomization,
    AssignmentDeploymentPoint,
    AssignmentFileVersion,
    AssignmentFinalization,
    AssignmentInfo,
    AssignmentRevocation,
    AssignmentSection,
    AssignmentWeightage,
    FrameworkAssignment,
)
from vora_shared.models.framework_category import FrameworkCategory
from vora_shared.models.framework_merge import FrameworkMerge
from vora_shared.models.package_comparison import PackageComparison
from vora_shared.models.package_gap_analysis import PackageGapAnalysis, GapThresholdConfig
from vora_shared.models.package_merge import PackageMerge
from vora_shared.models.user import User, UserAddress, UserCreatedBy, UserOtp

__all__ = [
    "AddressBlock",
    "AgentPrompt",
    "AiExtractionInfo",
    "AssignmentControl",
    "AssignmentCustomization",
    "AssignmentDeploymentPoint",
    "AssignmentFileVersion",
    "AssignmentFinalization",
    "AssignmentInfo",
    "AssignmentRevocation",
    "AssignmentSection",
    "AssignmentWeightage",
   
    "Customer",
    "CustomerAddress",
    "CustomerCreatedBy",
    "DeploymentDocument",
    "DeploymentDocumentFileVersion",
    "DeploymentFramework",
   
  
    "DeploymentPackageMerge",
    "DocumentExtraction",
    "EvidenceOutput",
    "ExpertReview",
    "ExtractionControlItem",
    "ExtractionControls",
    "ExtractionDeploymentPoint",
    "ExtractionSection",
    "ExtractionStatusHistory",
    "Framework",
    "FrameworkAccess",
    "FrameworkAssignment",
    "FrameworkCategory",
    "FrameworkMerge",
    "FrameworkPackageDocument",
    "GapConfig",
    "GapThresholdConfig",
    "PackageComparison",
    "PackageGapAnalysis",
    "PackageMerge",
    "PackageMergeTracking",
    "PackageVersion",
    "UploadedFile",
    "User",
    "UserAddress",
    "UserCreatedBy",
    "UserOtp",
]
