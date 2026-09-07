"""
Control Merger Service — Cumulative merge of controls across file versions
Merges extracted controls when multiple files are uploaded to same framework
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def _remove_parenthetical_text(name: str) -> str:
    result = []
    index = 0
    while index < len(name):
        if name[index] != "(":
            result.append(name[index])
            index += 1
            continue

        while result and result[-1] in " \t":
            result.pop()
        index += 1
        while index < len(name) and name[index] != ")":
            index += 1
        if index < len(name):
            index += 1
    return "".join(result)


def clean_section_name(name: str) -> str:
    if not name:
        return ""
    original = name
    # Remove anything in parenthesis (including the parenthesis)
    name = _remove_parenthetical_text(name)
    # Remove leading numbers and prefixes (e.g., "3. ", "10 - ", "A.5 ")
    name = re.sub(r"^(?:\d+|[A-Za-z]\.\d+(?:\.\d+)*)[\.\-\s]+", "", name)
    cleaned = name.strip()
    return cleaned if cleaned else original.strip()


def _extract_previous_controls(ai_extraction: Any) -> list | None:
    if not isinstance(ai_extraction, dict) or ai_extraction.get("status") != "extracted":
        return None
    controls_block = ai_extraction.get("controls", {})
    if isinstance(controls_block, dict):
        return controls_block.get("controls_data", [])
    if isinstance(controls_block, list):
        return controls_block
    return []


def _is_previous_version_candidate(fv: Any, current_file_version: str) -> bool:
    return (
        isinstance(fv, dict)
        and fv.get("fileVersion") != current_file_version
        and bool(fv.get("aiExtraction"))
    )


def get_framework_previous_controls(
    file_versions: list[dict[str, Any]], current_file_version: str
) -> tuple[list[dict[str, Any]], str | None, str | None]:
    """
    Get controls from previous completed version in fileVersions array.
    Skip current_file_version and find the most recent completed extraction.

    Args:
        file_versions: List of file version objects from framework.fileVersions
        current_file_version: Current file version to skip

    Returns:
        (controls_data, prev_file_version, prev_file_hash) or ([], None, None)
    """
    if not file_versions:
        logger.info("[MERGE] No previous file versions found")
        return [], None, None

    # Reverse iterate — latest first
    for fv in reversed(file_versions):
        if not _is_previous_version_candidate(fv, current_file_version):
            continue
        controls_data = _extract_previous_controls(fv.get("aiExtraction"))
        if controls_data is None or not controls_data:
            continue

        prev_file_hash = fv.get("fileHash")
        logger.info(
            f"[MERGE] Previous controls found | fileVersion={fv.get('fileVersion')} "
            f"| sections={len(controls_data)} | fileHash={prev_file_hash}"
        )
        return controls_data, fv.get("fileVersion"), prev_file_hash

    logger.info("[MERGE] No previous extracted version found")
    return [], None, None


def _section_key(section: dict[str, Any]) -> str:
    section_id = (section.get("id") or "").lower().strip()
    section_name = (section.get("name") or "").lower().strip()
    return section_id or section_name


def _copy_section(section: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": section.get("id"),
        "name": clean_section_name(section.get("name")),
        "controls": [dict(control) for control in section.get("controls", [])],
    }


def _index_controls(
    controls: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    by_id = {control.get("id", "").strip(): control for control in controls if control.get("id")}
    by_name = {
        control.get("name", "").lower().strip(): control for control in controls if control.get("name")
    }
    return by_id, by_name


def _merge_deployment_points(
    existing: dict[str, Any], incoming: dict[str, Any], summary: dict[str, int]
) -> None:
    points = existing.setdefault("deployment_points", [])
    existing_names = {point.get("name", "").lower().strip() for point in points}
    for new_point in incoming.get("deployment_points", []):
        point_name = (new_point.get("name") or "").lower().strip()
        if not point_name or point_name in existing_names:
            continue
        points.append(
            {
                "id": f"DP-{len(points) + 1:03d}",
                "name": new_point.get("name", ""),
                "status": "pending",
                "path": "",
                "source": "",
                "weightage": 0,
                "remark": "",
            }
        )
        existing_names.add(point_name)
        summary["new_dps"] += 1


def _merge_existing_control(
    existing: dict[str, Any],
    incoming: dict[str, Any],
    control_id: str,
    control_name: str,
    summary: dict[str, int],
) -> None:
    if incoming.get("description"):
        existing["description"] = incoming["description"]
    _merge_deployment_points(existing, incoming, summary)
    summary["merged_controls"] += 1
    logger.info(f"[MERGE] Merged control: {control_id} ({control_name})")


def _merge_section_controls(
    old_controls: list[dict[str, Any]],
    new_controls: list[dict[str, Any]],
    summary: dict[str, int],
) -> None:
    controls_by_id, controls_by_name = _index_controls(old_controls)
    for new_control in new_controls:
        control_id = (new_control.get("id") or "").strip()
        control_name = (new_control.get("name") or "").lower().strip()
        existing = controls_by_id.get(control_id) or controls_by_name.get(control_name)
        if existing:
            _merge_existing_control(existing, new_control, control_id, control_name, summary)
            continue

        old_controls.append(new_control)
        if control_id:
            controls_by_id[control_id] = new_control
        if control_name:
            controls_by_name[control_name] = new_control
        summary["new_controls"] += 1
        logger.info(f"[MERGE] Added new control: {control_id} ({control_name})")


def _add_new_section(
    section_map: dict[str, dict[str, Any]],
    section_order: list[str],
    section: dict[str, Any],
    summary: dict[str, int],
) -> None:
    key = _section_key(section)
    section_map[key] = {
        "id": section.get("id"),
        "name": clean_section_name(section.get("name")),
        "controls": list(section.get("controls", [])),
    }
    section_order.append(key)
    controls = section.get("controls", [])
    summary["new_sections"] += 1
    summary["new_controls"] += len(controls)
    logger.info(f"[MERGE] Added new section: {section.get('name')} with {len(controls)} controls")


def merge_controls_cumulative(
    old_sections: list[dict[str, Any]], new_sections: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Cumulative merge: old + new → merged sections list.

    Control match: ID (exact) then Name (case-insensitive)
    Rules:
      - Same control exists → description override (new wins), DPs deduplicate by name
      - New control only → add
      - Old control only → keep as-is
      - New section only → append
      - Old section only → keep as-is

    Args:
        old_sections: Previously extracted sections
        new_sections: Newly extracted sections

    Returns:
        (merged_sections, summary) where summary contains merge statistics
    """
    if not old_sections:
        logger.info("[MERGE] No previous sections, merging new sections from scratch")
        old_sections = []

    if not new_sections:
        logger.info(f"[MERGE] No new sections, keeping previous {len(old_sections)} sections")
        return old_sections, {"skipped": "no_new_controls"}

    summary = {"merged_controls": 0, "new_controls": 0, "new_dps": 0, "new_sections": 0}

    sec_map = {_section_key(section): _copy_section(section) for section in old_sections}
    sec_order = [_section_key(section) for section in old_sections]

    # Merge new sections
    for new_sec in new_sections:
        sec_key = _section_key(new_sec)

        if sec_key not in sec_map:
            _add_new_section(sec_map, sec_order, new_sec, summary)
            continue

        _merge_section_controls(sec_map[sec_key]["controls"], new_sec.get("controls", []), summary)

    merged_result = [sec_map[k] for k in sec_order]

    # Re-number sections sequentially for safety (SEC-01, SEC-02, etc.)
    # Wait, if we are grouping by A.5, A.7 etc, we shouldn't overwrite their IDs with SEC-01!
    # Let's keep original ID if it's already structured, or assign SEC- if missing.
    for idx, sec in enumerate(merged_result, 1):
        if isinstance(sec, dict) and not sec.get("id"):
            sec["id"] = f"SEC-{idx:02d}"

    logger.info(
        f"[MERGE] Merge complete | merged={summary['merged_controls']} "
        f"| new_controls={summary['new_controls']} | new_dps={summary['new_dps']} "
        f"| new_sections={summary['new_sections']} | total_sections={len(merged_result)}"
    )

    return merged_result, summary
