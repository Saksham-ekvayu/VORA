"""Utility helpers for deployment pipeline processing."""

from collections import defaultdict
from typing import Any


def extract_deployment_points(controls_data: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Extract deployment points that contain BOTH path and source.

    Expected structure:
    controls_data -> controls -> deployment_points
    """

    deployment_points: list[dict[str, Any]] = []

    sections = controls_data.get("controls_data", [])

    for section in sections:
        controls = section.get("controls", [])

        for control in controls:
            dps = control.get("deployment_points", [])

            for dp in dps:
                path = dp.get("path")
                source = dp.get("source")

                # Ignore empty values
                if path and source:
                    deployment_points.append(
                        {
                            "section_id": section.get("id"),
                            "control_id": control.get("id"),
                            "dp_id": dp.get("id"),
                            "path": str(path).strip(),
                            "source": str(source).strip().lower(),
                        }
                    )

    return deployment_points


def extract_source_paths(controls_data: dict[str, Any], source: str) -> list[str]:
    """
    Return only the file paths for a specific source type.

    Example:
        extract_source_paths(data, "aws")

    Returns:
        ["s3://bucket/file1.pdf", "s3://bucket/file2.docx"]
    """

    source = source.lower()

    deployment_points = extract_deployment_points(controls_data)

    return [
        dp["path"]
        for dp in deployment_points
        if dp["source"] == source
    ]


def group_paths_by_source(controls_data: dict[str, Any]) -> dict[str, list[str]]:
    """
    Group all paths by source type.

    Returns:
        {
            "aws": ["s3://bucket/file1.pdf"],
            "local": ["C:/docs/file2.pdf"],
            "sharepoint": ["https://tenant.sharepoint.com/..."],
        }
    """

    grouped: dict[str, list[str]] = defaultdict(list)

    for dp in extract_deployment_points(controls_data):
        grouped[dp["source"]].append(dp["path"])

    return dict(grouped)