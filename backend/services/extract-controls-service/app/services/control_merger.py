"""
Control Merger Service — Cumulative merge of controls across file versions
Merges extracted controls when multiple files are uploaded to same framework
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def clean_section_name(name: str) -> str:
    if not name:
        return ""
    original = name
    # Remove anything in parenthesis (including the parenthesis)
    name = re.sub(r"\s*\([^)]*\)", "", name)
    # Remove leading numbers and prefixes (e.g., "3. ", "10 - ", "A.5 ")
    name = re.sub(r"^(?:\d+|[A-Za-z]\.\d+(?:\.\d+)*)[\.\-\s]+", "", name)
    cleaned = name.strip()
    return cleaned if cleaned else original.strip()


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
        if not isinstance(fv, dict):
            continue

        if fv.get("fileVersion") == current_file_version:
            continue  # Skip current version

        ai_extraction = fv.get("aiExtraction")
        if not ai_extraction:
            continue

        if isinstance(ai_extraction, dict):
            status = ai_extraction.get("status")
            if status != "extracted":
                continue  # Skip incomplete versions

            controls_block = ai_extraction.get("controls", {})
        else:
            continue

        # Extract controls_data from structure
        if isinstance(controls_block, dict):
            controls_data = controls_block.get("controls_data", [])
        elif isinstance(controls_block, list):
            controls_data = controls_block
        else:
            controls_data = []

        if controls_data:
            prev_file_hash = fv.get("fileHash")
            logger.info(
                f"[MERGE] ✅ Previous controls found | fileVersion={fv.get('fileVersion')} "
                f"| sections={len(controls_data)} | fileHash={prev_file_hash}"
            )
            return controls_data, fv.get("fileVersion"), prev_file_hash

    logger.info("[MERGE] ℹ️ No previous extracted version found")
    return [], None, None


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

    # Build section map from old (preserve order)
    sec_map = {}
    sec_order = []
    for sec in old_sections:
        # Use ID as primary key if available, fallback to name
        sec_id = (sec.get("id") or "").lower().strip()
        sec_name = (sec.get("name") or "").lower().strip()
        key = sec_id if sec_id else sec_name
        sec_map[key] = {
            "id": sec.get("id"),
            "name": clean_section_name(sec.get("name")),
            "controls": [dict(c) for c in sec.get("controls", [])],
        }
        sec_order.append(key)

    # Merge new sections
    for new_sec in new_sections:
        sec_id = (new_sec.get("id") or "").lower().strip()
        sec_name = (new_sec.get("name") or "").lower().strip()
        sec_key = sec_id if sec_id else sec_name

        if sec_key not in sec_map:
            # Brand new section
            sec_map[sec_key] = {
                "id": new_sec.get("id"),
                "name": clean_section_name(new_sec.get("name")),
                "controls": list(new_sec.get("controls", [])),
            }
            sec_order.append(sec_key)
            summary["new_sections"] += 1
            summary["new_controls"] += len(new_sec.get("controls", []))
            logger.info(
                f"[MERGE] Added new section: {new_sec.get('name')} "
                f"with {len(new_sec.get('controls', []))} controls"
            )
            continue
        else:
            # If merging into existing section by ID, just keep the existing name.
            pass

        # Merge controls within existing section
        old_ctrl_list = sec_map[sec_key]["controls"]
        ctrl_by_id = {c.get("id", "").strip(): c for c in old_ctrl_list if c.get("id")}
        ctrl_by_name = {c.get("name", "").lower().strip(): c for c in old_ctrl_list if c.get("name")}

        for new_ctrl in new_sec.get("controls", []):
            nc_id = (new_ctrl.get("id") or "").strip()
            nc_name = (new_ctrl.get("name") or "").lower().strip()
            existing = ctrl_by_id.get(nc_id) or ctrl_by_name.get(nc_name)

            if existing:
                # Update description (new wins)
                if new_ctrl.get("description"):
                    existing["description"] = new_ctrl["description"]

                # Merge DPs — deduplicate by name
                existing_dp_names = {
                    dp.get("name", "").lower().strip() for dp in existing.get("deployment_points", [])
                }
                dps = existing.setdefault("deployment_points", [])
                for new_dp in new_ctrl.get("deployment_points", []):
                    dp_name_lower = (new_dp.get("name") or "").lower().strip()
                    if dp_name_lower and dp_name_lower not in existing_dp_names:
                        dps.append(
                            {
                                "id": f"DP-{len(dps) + 1:03d}",
                                "name": new_dp.get("name", ""),
                                "status": "pending",
                                "path": "",
                                "weightage": 0,
                                "remark": "",
                            }
                        )
                        existing_dp_names.add(dp_name_lower)
                        summary["new_dps"] += 1

                summary["merged_controls"] += 1
                logger.info(f"[MERGE] Merged control: {nc_id} ({nc_name})")

            else:
                # New control — append
                old_ctrl_list.append(new_ctrl)
                if nc_id:
                    ctrl_by_id[nc_id] = new_ctrl
                if nc_name:
                    ctrl_by_name[nc_name] = new_ctrl
                summary["new_controls"] += 1
                logger.info(f"[MERGE] Added new control: {nc_id} ({nc_name})")

    merged_result = [sec_map[k] for k in sec_order]

    # Re-number sections sequentially for safety (SEC-01, SEC-02, etc.)
    # Wait, if we are grouping by A.5, A.7 etc, we shouldn't overwrite their IDs with SEC-01!
    # Let's keep original ID if it's already structured, or assign SEC- if missing.
    for idx, sec in enumerate(merged_result, 1):
        if isinstance(sec, dict):
            if not sec.get("id"):
                sec["id"] = f"SEC-{idx:02d}"

    logger.info(
        f"[MERGE] ✅ Merge complete | merged={summary['merged_controls']} "
        f"| new_controls={summary['new_controls']} | new_dps={summary['new_dps']} "
        f"| new_sections={summary['new_sections']} | total_sections={len(merged_result)}"
    )

    return merged_result, summary
