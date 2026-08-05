"""Port of deployment-framework-service-main/src/services/ai.service.js.

HTTP client for the external AI service using httpx instead of axios.
"""

import os
from pathlib import Path
from typing import Any

import httpx

AI_API = {
    "HEALTH": "/health",
    "UPLOAD_DEPLOYMENT_FRAMEWORK": "/api/load/deployment-frameworks/upload",
    "UPLOAD_FRAMEWORK_ASSIGNMENT": "/api/load/framework-assignments/upload",
    "DELETE_DEPLOYMENT_FRAMEWORK": "/api/load/deployment-frameworks/{id}",
    "DELETE_PACKAGE_VERSION": "/api/load/deployment-frameworks/{id}/packageversion/{packageVersion}",
    "UPDATE_FRAMEWORK_ASSIGNMENT_CONTROL_WEIGHTAGE": (
        "/api/extract/framework-assignments/{id}/file-versions/{fileVersion}/controls/{controlId}/weightage"
    ),
    "FINALIZE_FRAMEWORK_ASSIGNMENT": "/api/extract/framework-assignments/{id}/finalize",
    "UPDATE_FRAMEWORK_ASSIGNMENT_CONTROLS_APPLICABILITY": (
        "/api/extract/framework-assignments/{id}/file-versions/{fileVersion}/controls/applicability"
    ),
}

AI_SERVICE_UNAVAILABLE = "AI service is currently offline or unreachable"


def _base_url() -> str:
    return os.environ.get("AI_SERVICE_URL", "http://192.168.1.30:7000")


def _timeout() -> float:
    try:
        return float(os.environ.get("AI_SERVICE_TIMEOUT", "10"))
    except ValueError:
        return 10.0


async def check_health() -> bool:
    try:
        async with httpx.AsyncClient(base_url=_base_url(), timeout=_timeout()) as client:
            resp = await client.get(AI_API["HEALTH"])
            if resp.status_code != 200:
                return False
            try:
                data = resp.json()
            except Exception:
                return bool(resp.text)
            if isinstance(data, str):
                return data == "OK"
            if isinstance(data, dict):
                return data.get("status") in ("OK", 200) or bool(data)
            return bool(data)
    except Exception:
        return False


def _find_active_package(framework: Any, package_version: str | None, upload_file_ids: set[str]) -> Any | None:
    packages = getattr(framework, "packages", None) or []
    if package_version:
        for pkg in packages:
            if pkg.packageVersion == package_version:
                return pkg
    for pkg in packages:
        if any(str(doc.fileId) in upload_file_ids for doc in (pkg.documents or [])):
            return pkg
    for pkg in packages:
        if pkg.packageVersion == framework.currentPackageVersion:
            return pkg
    return None


async def upload_deployment_framework(
    framework: Any,
    documents: Any,
    file_paths: Any,
    package_version: str | None = None,
) -> dict[str, Any]:
    docs_array = documents if isinstance(documents, list) else [documents]
    paths_array = file_paths if isinstance(file_paths, list) else [file_paths]

    upload_file_ids = {str(doc.fileId) for doc in docs_array}
    active_package = _find_active_package(framework, package_version, upload_file_ids)

    mapped_package = None
    if active_package:
        mapped_package = {
            "packageVersion": active_package.packageVersion,
            "type": active_package.type,
            "trigger": active_package.trigger,
            "documents": [
                {
                    "fileId": str(doc.fileId),
                    "fileVersion": doc.fileVersion,
                    "replicated": doc.replicated,
                }
                for doc in (active_package.documents or [])
            ],
        }

    if not await check_health():
        raise RuntimeError(AI_SERVICE_UNAVAILABLE)

    for file_path in paths_array:
        if not Path(file_path).exists():
            raise RuntimeError(f"File not found at path: {file_path}")

    files: list[tuple[str, tuple[str, bytes]]] = []
    for file_path, doc in zip(paths_array, docs_array):
        with open(file_path, "rb") as fh:
            content = fh.read()
        field_name = f"file_{doc.fileId}"
        files.append((field_name, (doc.originalFileName, content)))

    data: dict[str, str] = {
        "id": str(framework.id),
        "uploadedBy": str(framework.uploadedBy),
        "currentPackageVersion": framework.currentPackageVersion,
        "assignedFrameworkId": str(framework.assignedFrameworkId),
    }
    if mapped_package:
        import json

        data["package"] = json.dumps(mapped_package, default=str)

    async with httpx.AsyncClient(base_url=_base_url(), timeout=_timeout()) as client:
        resp = await client.request(
            "PATCH", AI_API["UPLOAD_DEPLOYMENT_FRAMEWORK"], data=data, files=files
        )
        return _handle_response(resp)


async def upload_framework_assignment(assignment_data: dict[str, Any]) -> dict[str, Any]:
    if not await check_health():
        raise RuntimeError(AI_SERVICE_UNAVAILABLE)

    data = {
        "id": str(assignment_data.get("_id")),
        "customerId": str(assignment_data.get("customerId")),
        "assignedBy": str(assignment_data.get("assignment", {}).get("assignedBy")),
        "frameworkId": str(assignment_data.get("frameworkId")),
    }

    async with httpx.AsyncClient(base_url=_base_url(), timeout=_timeout()) as client:
        resp = await client.post(AI_API["UPLOAD_FRAMEWORK_ASSIGNMENT"], data=data)
        return _handle_response(resp)


async def update_framework_assignment_control_weightage(
    id: str, file_version: str, control_id: str, weightage_data: dict[str, Any]
) -> dict[str, Any]:
    if not await check_health():
        raise RuntimeError(AI_SERVICE_UNAVAILABLE)

    endpoint = AI_API["UPDATE_FRAMEWORK_ASSIGNMENT_CONTROL_WEIGHTAGE"].format(
        id=id, fileVersion=file_version, controlId=control_id
    )

    async with httpx.AsyncClient(base_url=_base_url(), timeout=_timeout()) as client:
        resp = await client.patch(
            endpoint,
            json={
                "weightage": {
                    "framework_weightage": weightage_data.get("framework_weightage"),
                    "customer_weightage": weightage_data.get("customer_weightage"),
                }
            },
        )
        return _handle_response(resp)


async def finalize_framework_assignment(id: str, finalize_data: dict[str, Any]) -> dict[str, Any]:
    if not await check_health():
        raise RuntimeError(AI_SERVICE_UNAVAILABLE)

    endpoint = AI_API["FINALIZE_FRAMEWORK_ASSIGNMENT"].format(id=id)

    async with httpx.AsyncClient(base_url=_base_url(), timeout=_timeout()) as client:
        resp = await client.patch(
            endpoint,
            json={
                "isFinalized": finalize_data.get("isFinalized"),
                "finalizedBy": finalize_data.get("finalizedBy"),
            },
        )
        return _handle_response(resp)


async def update_framework_assignment_controls_applicability(
    id: str, file_version: str, applicability_data: dict[str, Any]
) -> dict[str, Any]:
    if not await check_health():
        raise RuntimeError(AI_SERVICE_UNAVAILABLE)

    endpoint = AI_API["UPDATE_FRAMEWORK_ASSIGNMENT_CONTROLS_APPLICABILITY"].format(
        id=id, fileVersion=file_version
    )

    async with httpx.AsyncClient(base_url=_base_url(), timeout=_timeout()) as client:
        resp = await client.patch(
            endpoint,
            json={
                "controlIds": applicability_data.get("controlIds"),
                "is_applicable": applicability_data.get("is_applicable"),
            },
        )
        return _handle_response(resp)


async def delete_deployment_framework(id: str) -> dict[str, Any]:
    if not await check_health():
        raise RuntimeError(AI_SERVICE_UNAVAILABLE)
    endpoint = AI_API["DELETE_DEPLOYMENT_FRAMEWORK"].format(id=id)
    async with httpx.AsyncClient(base_url=_base_url(), timeout=_timeout()) as client:
        resp = await client.delete(endpoint)
        return _handle_response(resp)


async def delete_package_version(id: str, package_version: str) -> dict[str, Any]:
    if not await check_health():
        raise RuntimeError(AI_SERVICE_UNAVAILABLE)
    endpoint = AI_API["DELETE_PACKAGE_VERSION"].format(id=id, packageVersion=package_version)
    async with httpx.AsyncClient(base_url=_base_url(), timeout=_timeout()) as client:
        resp = await client.delete(endpoint)
        return _handle_response(resp)


def _handle_response(resp: httpx.Response) -> dict[str, Any]:
    if resp.status_code >= 400:
        try:
            body = resp.json()
            message = body.get("message") or body.get("detail") or str(body)
        except Exception:
            message = resp.text or f"AI Service HTTP {resp.status_code}"
        raise RuntimeError(f"AI Service Error: {message}")
    try:
        return resp.json()
    except Exception:
        return {"raw": resp.text}
