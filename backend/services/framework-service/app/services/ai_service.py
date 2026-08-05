"""Port of ai.service.js — HTTP client for the AI extraction service."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from vora_shared.config import get_settings

AI_API = {
    "HEALTH": "/health",
    "UPLOAD_FRAMEWORK": "/api/load/frameworks/upload",
    "DELETE_FRAMEWORK": "/api/load/frameworks/{frameworkId}",
    "DELETE_FRAMEWORK_FILE": "/api/load/frameworks/{frameworkId}/file/{fileId}",
    "DELETE_FRAMEWORK_CONTROL": (
        "/api/extract/ai/jobs/{frameworkId}/file-versions/{fileVersion}/controls/{controlId}"
    ),
    "UPDATE_FRAMEWORK_CONTROL": (
        "/api/extract/ai/jobs/{frameworkId}/file-versions/{fileVersion}/controls/{controlId}"
    ),
    "ADD_FRAMEWORK_CONTROL": (
        "/api/extract/ai/jobs/{frameworkId}/file-versions/{fileVersion}/controls"
    ),
    "UPDATE_FRAMEWORK_APPROVAL_STATUS": (
        "/api/extract/ai/jobs/{frameworkId}/approval-status"
    ),
}

AI_SERVICE_UNAVAILABLE_MESSAGE = "AI service is currently offline or unreachable"


class AiServiceError(Exception):
    pass


def _extract_error_message(exc: httpx.HTTPStatusError) -> str:
    try:
        payload = exc.response.json()
    except Exception:
        return exc.response.text or str(exc)

    message = payload.get("message") or payload.get("detail") or str(payload)
    if not isinstance(message, str):
        message = json.dumps(message)
    return message


class AiService:
    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.ai_service_url
        self._timeout = settings.ai_service_timeout

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout)

    async def check_health(self) -> bool:
        try:
            async with self._client() as client:
                response = await client.get(AI_API["HEALTH"])
                response.raise_for_status()
                try:
                    data = response.json()
                except Exception:
                    data = response.text
                if isinstance(data, str):
                    return data == "OK" or bool(data)
                if isinstance(data, dict):
                    return data.get("status") in ("OK", 200) or bool(data)
                return bool(data)
        except httpx.HTTPError as exc:
            print(f"AI Service health check failed: {exc}")
            return False

    async def _request(
        self,
        method: str,
        url: str,
        *,
        json_body: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> Any:
        try:
            async with self._client() as client:
                response = await client.request(
                    method, url, json=json_body, files=files, data=data
                )
                response.raise_for_status()
                if not response.content:
                    return None
                try:
                    return response.json()
                except Exception:
                    return response.text
        except httpx.HTTPStatusError as exc:
            error_msg = _extract_error_message(exc)
            print(f"[AI Service Error] {error_msg}")
            raise AiServiceError(f"AI Service Error: {error_msg}") from exc
        except httpx.HTTPError as exc:
            print(f"[AI Service Error] {exc}")
            raise AiServiceError(AI_SERVICE_UNAVAILABLE_MESSAGE) from exc

    async def upload_framework(self, framework, file_path: str | Path) -> Any:
        is_healthy = await self.check_health()
        if not is_healthy:
            raise AiServiceError(AI_SERVICE_UNAVAILABLE_MESSAGE)

        path = Path(file_path)
        if not path.exists():
            raise AiServiceError(f"File not found at path: {file_path}")

        def _fv_get(fv, key, default=None):
            if isinstance(fv, dict):
                return fv.get(key, default)
            return getattr(fv, key, default)

        def _approval_get(key, default=None):
            approval = framework.approval or {}
            if isinstance(approval, dict):
                return approval.get(key, default)
            return getattr(approval, key, default)

        file_name = None
        if framework.fileVersions:
            file_name = _fv_get(framework.fileVersions[0], "originalFileName")

        mapped_file_versions = [
            {
                "fileVersion": _fv_get(fv, "fileVersion"),
                "fileId": str(_fv_get(fv, "fileId")),
                "originalFileName": _fv_get(fv, "originalFileName"),
                "fileSize": _fv_get(fv, "fileSize"),
                "fileType": _fv_get(fv, "fileType"),
            }
            for fv in (framework.fileVersions or [])
        ]

        approved_at = _approval_get("date")
        mapped_approval = {
            "status": _approval_get("status"),
            "approvedBy": str(_approval_get("by")) if _approval_get("by") else None,
            "approvedAt": approved_at.isoformat() if hasattr(approved_at, "isoformat") else approved_at,
            "rejectionReason": _approval_get("remark"),
        }

        data = {
            "id": str(framework.id),
            "frameworkName": framework.frameworkName,
            "frameworkVersion": framework.frameworkVersion,
            "frameworkCategoryId": str(framework.frameworkCategoryId),
            "frameworkCode": framework.frameworkCode,
            "uploadedBy": str(framework.uploadedBy),
            "currentFileVersion": framework.currentFileVersion,
            "fileVersions": json.dumps(mapped_file_versions),
            "approval": json.dumps(mapped_approval),
        }

        file_bytes = path.read_bytes()
        files = {"file": (file_name or path.name, file_bytes)}

        return await self._request(
            "POST", AI_API["UPLOAD_FRAMEWORK"], data=data, files=files
        )

    async def delete_framework_control(
        self, framework_id: str, file_version: str, control_id: str
    ) -> Any:
        if not await self.check_health():
            raise AiServiceError(AI_SERVICE_UNAVAILABLE_MESSAGE)
        endpoint = AI_API["DELETE_FRAMEWORK_CONTROL"].format(
            frameworkId=framework_id, fileVersion=file_version, controlId=control_id
        )
        return await self._request("DELETE", endpoint)

    async def update_framework_control(
        self,
        framework_id: str,
        file_version: str,
        control_id: str,
        control_data: dict[str, Any],
    ) -> Any:
        if not await self.check_health():
            raise AiServiceError(AI_SERVICE_UNAVAILABLE_MESSAGE)
        endpoint = AI_API["UPDATE_FRAMEWORK_CONTROL"].format(
            frameworkId=framework_id, fileVersion=file_version, controlId=control_id
        )
        return await self._request(
            "PATCH",
            endpoint,
            json_body={
                "name": control_data.get("name"),
                "description": control_data.get("description"),
                "deployment_points": control_data.get("deployment_points"),
            },
        )

    async def add_framework_control(
        self, framework_id: str, file_version: str, control_data: dict[str, Any]
    ) -> Any:
        if not await self.check_health():
            raise AiServiceError(AI_SERVICE_UNAVAILABLE_MESSAGE)
        endpoint = AI_API["ADD_FRAMEWORK_CONTROL"].format(
            frameworkId=framework_id, fileVersion=file_version
        )
        payload: dict[str, Any] = {
            "name": control_data.get("name"),
            "description": control_data.get("description") or "",
            "deployment_points": control_data.get("deployment_points") or [],
        }
        if control_data.get("sectionId"):
            payload["section_id"] = control_data["sectionId"]
        if control_data.get("newSection"):
            payload["new_section"] = control_data["newSection"]
        return await self._request("POST", endpoint, json_body=payload)

    async def update_framework_approval_status(
        self, framework_id: str, approval_data: dict[str, Any]
    ) -> Any:
        if not await self.check_health():
            raise AiServiceError(AI_SERVICE_UNAVAILABLE_MESSAGE)
        endpoint = AI_API["UPDATE_FRAMEWORK_APPROVAL_STATUS"].format(
            frameworkId=framework_id
        )
        timestamp = approval_data.get("timestamp")
        return await self._request(
            "POST",
            endpoint,
            json_body={
                "status": approval_data.get("status"),
                "timestamp": timestamp.isoformat() if hasattr(timestamp, "isoformat") else timestamp,
                "reason": approval_data.get("reason"),
            },
        )

    async def delete_framework(self, framework_id: str) -> Any:
        if not await self.check_health():
            raise AiServiceError(AI_SERVICE_UNAVAILABLE_MESSAGE)
        endpoint = AI_API["DELETE_FRAMEWORK"].format(frameworkId=framework_id)
        return await self._request("DELETE", endpoint)

    async def delete_framework_file(self, framework_id: str, file_id: str) -> Any:
        if not await self.check_health():
            raise AiServiceError(AI_SERVICE_UNAVAILABLE_MESSAGE)
        endpoint = AI_API["DELETE_FRAMEWORK_FILE"].format(
            frameworkId=framework_id, fileId=file_id
        )
        return await self._request("DELETE", endpoint)


ai_service = AiService()
