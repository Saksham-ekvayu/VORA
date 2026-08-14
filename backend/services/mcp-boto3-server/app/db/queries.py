import json

# =========================================
# PROCESSED FILES
# =========================================
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from vora_shared.models import (
    ProcessedFile,
    SourceConfig,
    SourceCredential,
)
from vora_shared.models.deployment_framework import DeploymentFramework
from vora_shared.models.deployment_package_merge import DeploymentPackageMerge

shared_path = Path(__file__).resolve().parents[3] / "shared"
sys.path.insert(0, str(shared_path))


async def is_processed(db: AsyncSession, file_path: str):
    result = await db.execute(select(ProcessedFile).where(ProcessedFile.file_path == file_path))
    return result.scalar_one_or_none() is not None


async def mark_processed(db: AsyncSession, file_path: str, status: str = "done") -> bool:
    try:
        processed = ProcessedFile(
            file_path=file_path,
            status=status,
        )

        db.add(processed)
        await db.flush()

        return True

    except Exception as e:
        print(f"mark_processed error: {e}")
        return False


# =========================================
# SOURCE CONFIG / CREDENTIALS
# =========================================


async def save_source_config(
    db: AsyncSession,
    data,
) -> int | None:
    try:
        source_config = SourceConfig(
            control_name=data.control_name,
            dp_name=data.dp_name,
            organization_name=data.organization_name,
            source_type=data.source_type,
            source_name=data.source_name,
        )
        db.add(source_config)
        await db.flush()  # gets generated ID

        credential = SourceCredential(
            source_config_id=source_config.id,
            config_json=json.dumps(data.config_json),
        )

        db.add(credential)

        await db.flush()
        await db.refresh(source_config)

        return source_config.id

    except Exception as e:
        print(f"save_source_config error: {e}")
        return None


# =========================================
# FULL CONFIG
# =========================================


async def save_full_config(
    db: AsyncSession,
    data,
):
    source_config_id = await save_source_config(
        db,
        data.source_config,
    )

    return {
        "source_config_id": source_config_id,
        "sections_success": True,
    }


# =========================================
# GET SOURCE CONFIGS
# =========================================


async def get_source_configs(
    db: AsyncSession,
):
    result = await db.execute(select(SourceConfig))

    configs = result.scalars().all()

    response = []

    for config in configs:
        response.append(
            {
                "id": config.id,
                "control_name": config.control_name,
                "dp_name": config.dp_name,
                "organization_name": config.organization_name,
                "source_type": config.source_type,
                "source_name": config.source_name,
                "is_active": config.is_active,
                "created_at": config.created_at,
            }
        )

    return response


async def get_live_package(db: AsyncSession):
    """
    Return the latest LIVE deployment package from deployment_frameworks.
    """

    stmt = select(DeploymentFramework).order_by(DeploymentFramework.updatedAt.desc())

    result = await db.execute(stmt)
    frameworks = result.scalars().all()

    for framework in frameworks:
        for package in framework.packages or []:
            if package.get("status") == "live":
                return {
                    "framework_id": framework.id,
                    "framework_name": framework.frameworkName,
                    "package_version": package.get("packageVersion"),
                    "merge_document": package.get("mergeDocument"),
                    "documents": package.get("documents", []),
                }

    return None


async def get_live_framework(db: AsyncSession):
    result = await db.execute(select(DeploymentFramework))
    frameworks = result.scalars().all()

    for framework in frameworks:
        for pkg in framework.packages or []:
            if pkg.get("status") == "live":
                return {
                    "framework_id": framework.id,
                    "framework_name": framework.frameworkName,
                    "package_version": pkg.get("packageVersion"),
                    "merge_document": pkg.get("mergeDocument"),
                }

    return None


async def get_framework_merge(db: AsyncSession, merge_id: str):
    result = await db.execute(select(DeploymentPackageMerge).where(DeploymentPackageMerge.id == merge_id))

    merge = result.scalar_one_or_none()

    if not merge:
        return None

    return {
        "id": merge.id,
        "controls": merge.controls,
        "summary": merge.summary,
        "status": merge.status,
        "file_hashes": merge.fileHashes,
    }
