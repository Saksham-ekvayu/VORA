"""
Control Extraction Service — AI-powered extraction using OpenAI GPT-4o-mini
Extracts controls from framework documents with deployment points
"""

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from app.services.control_merger import clean_section_name
from dotenv import load_dotenv
from openai import OpenAI

logger = logging.getLogger(__name__)

# Load environment variables from shared .env ONLY
shared_env_path = Path(__file__).resolve().parents[4] / "shared" / ".env"
if shared_env_path.exists():
    load_dotenv(shared_env_path)
else:
    logger.warning(f"[ENV] Shared .env not found at {shared_env_path}")

# OpenAI configuration - lazy load to avoid errors during import
_client = None


def get_openai_client():
    """Get or create OpenAI client"""
    global _client
    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.error("[OPENAI] OPENAI_API_KEY not found in environment")
            logger.error(f"[OPENAI] Checked path: {shared_env_path}")
            raise ValueError("OPENAI_API_KEY environment variable not set")
        logger.info("[OPENAI] Client initialized")
        _client = OpenAI(api_key=api_key)
    return _client


# Batching configuration for large extractions
DEPLOYMENT_BATCH_SIZE = 10
DEPLOYMENT_MAX_TOKENS = 16000
CONTROL_EXTRACTION_MAX_TOKENS = 16000


def _log_llm_call(tag: str, response: Any, elapsed: float):
    """Log LLM call results with timing and token usage"""
    try:
        finish_reason = response.choices[0].finish_reason
        usage = getattr(response, "usage", None)
        usage_str = (
            f" | tokens(prompt={usage.prompt_tokens},completion={usage.completion_tokens})" if usage else ""
        )
        logger.info(f"[{tag}] LLM call done in {elapsed:.1f}s | finish_reason={finish_reason}{usage_str}")
        if finish_reason == "length":
            logger.warning(f"[{tag}] Response truncated — hit max_tokens limit")
        return finish_reason
    except Exception:
        logger.info(f"[{tag}] LLM call done in {elapsed:.1f}s")
        return None


def extract_framework_controls(chunks: list, framework_id: str, is_deployment: bool = False) -> list:
    """
    Extract controls from framework document using AI.
    Two-stage extraction:
    1. Extract Control_id, Control_name, Control_description, Section_name
    2. Generate Deployment_points for each control (in batches)
    """
    if not chunks:
        logger.warning("[EXTRACT] No chunks provided")
        return []

    text = " ".join(chunks) if isinstance(chunks, list) else str(chunks)
    REGEX = r"\b(?:[A-Z]+(?:\.[A-Z]+)*[-.]?)?\d+(?:\.\d+)*\b"

    # Stage 1: Extract controls
    logger.info(f"[EXTRACT] Starting framework extraction | framework_id={framework_id}")

    if is_deployment:
        prompt_stage1 = f"""You are a strict JSON generator.
Extract ALL compliance controls, policy statements, procedures, and key directives from the following text.
Do NOT skip ANY important directive.

Rules for Control IDs and Section IDs:
1. If explicit Section and Control IDs exist in the document text, you MUST extract and use them EXACTLY as they appear.
2. If the document does NOT contain explicit IDs, you MUST generate them sequentially starting strictly from A.1 (e.g., Section IDs: A.1, A.2, A.3...).
3. When generating, Control IDs MUST be based on their Section ID. For example, if a control belongs to section A.1, its Control IDs must be A.1.1, A.1.2, A.1.3, etc. Do not skip or start from a random number.

Extract the NAME and detailed DESCRIPTION for each item.

For Section_name: Extract the EXACT section/category heading this item belongs to. Do NOT include Section IDs or numbering in the Section_name (e.g. use "Facility Security" instead of "A.7 Facility Security" or "7. Facility Security").

Use JSON list ONLY:
[{{"Control_id": "","Control_name": "","Control_type":"","Control_description": "","Section_name": ""}}]

TEXT:
{text}

Return ONLY JSON. No markdown. No text outside JSON."""
    else:
        prompt_stage1 = f"""You are a strict JSON generator.
Extract ALL compliance controls from the following text.
Do NOT skip ANY control.

EXTRACT ONLY if all three are present in this sequence: ID, NAME and DESCRIPTION, otherwise return null.

Rules for Control IDs and Section IDs:
1. If explicit Section and Control IDs exist in the document text, you MUST extract and use them EXACTLY as they appear.
2. If the document does NOT contain explicit IDs, you MUST generate them sequentially starting strictly from A.1 (e.g., Section IDs: A.1, A.2, A.3...).
3. When generating, Control IDs MUST be based on their Section ID. For example, if a control belongs to section A.1, its Control IDs must be A.1.1, A.1.2, A.1.3, etc. Do not skip or start from a random number.

For Section_name: Extract the EXACT section/category heading this control belongs to. Do NOT include Section IDs or numbering in the Section_name (e.g. use "Facility Security" instead of "A.7 Facility Security" or "7. Facility Security").

Extract control IDs using this regex: {REGEX!r}
Treat ALL numeric headings (0.1, 0.2, 1.1, 1.2, A.1.2, A.2 etc.) as controls, but format their Control_id as described above.

Use JSON list ONLY:
[{{"Control_id": "","Control_name": "","Control_type":"","Control_description": "","Section_name": ""}}]

TEXT:
{text}

Return ONLY JSON. No markdown. No text outside JSON."""

    t_start = datetime.now()
    try:
        response = get_openai_client().chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt_stage1}],
            temperature=0,
            max_tokens=CONTROL_EXTRACTION_MAX_TOKENS,
        )
        elapsed = (datetime.now() - t_start).total_seconds()
        _log_llm_call("EXTRACT-STAGE1", response, elapsed)

        controls = json.loads(response.choices[0].message.content)
        logger.info(f"[EXTRACT] Stage 1 complete: {len(controls)} controls extracted")

    except json.JSONDecodeError as e:
        logger.exception(f"[EXTRACT] JSON decode failed: {e}")
        return []
    except Exception as e:
        logger.exception(f"[EXTRACT] OpenAI API error: {e}", exc_info=True)
        return []

    # Stage 2: Generate deployment points (batched)
    logger.info(f"[EXTRACT] Stage 2: Generating deployment points in batches of {DEPLOYMENT_BATCH_SIZE}")

    final_controls = []
    total_batches = (len(controls) + DEPLOYMENT_BATCH_SIZE - 1) // DEPLOYMENT_BATCH_SIZE if controls else 0

    for batch_idx in range(0, len(controls), DEPLOYMENT_BATCH_SIZE):
        batch = controls[batch_idx : batch_idx + DEPLOYMENT_BATCH_SIZE]
        batch_num = batch_idx // DEPLOYMENT_BATCH_SIZE + 1

        logger.info(f"[EXTRACT] Batch {batch_num}/{total_batches}: {len(batch)} controls")

        prompt_stage2 = f"""You are an analyser.
From each control in the given JSON, generate 5-6 deployment points.

Deployment points must describe:
- How to implement this control
- What actions/steps are required
- How to operationalize it
- Important implementation details

Every point should be numbered (1. 2. 3. etc.).
Store all points as a single string.

IMPORTANT: Keep Section_name exactly as provided. Do NOT change it.

Input JSON:
{json.dumps(batch)}

Add Deployment_points field to each control.
Use JSON list ONLY:
[{{"Control_id": "","Control_name": "","Control_type":"","Control_description": "","Section_name": "","Deployment_points": ""}}]

Return ONLY JSON. No markdown."""

        t_start = datetime.now()
        try:
            response = get_openai_client().chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt_stage2}],
                temperature=0,
                max_tokens=DEPLOYMENT_MAX_TOKENS,
            )
            elapsed = (datetime.now() - t_start).total_seconds()
            finish_reason = _log_llm_call(f"EXTRACT-STAGE2-batch{batch_num}", response, elapsed)

            batch_result = json.loads(response.choices[0].message.content)

            # Map deployment points by Control_id to preserve Stage 1 descriptions/names
            dp_map = {}
            for res_ctrl in batch_result:
                if isinstance(res_ctrl, dict):
                    c_id = str(res_ctrl.get("Control_id", "")).strip()
                    if c_id:
                        dp_map[c_id] = res_ctrl.get("Deployment_points", "")

            merged_batch = []
            for orig_ctrl in batch:
                c_id = str(orig_ctrl.get("Control_id", "")).strip()
                orig_ctrl["Deployment_points"] = dp_map.get(c_id, orig_ctrl.get("Deployment_points", ""))
                merged_batch.append(orig_ctrl)

            final_controls.extend(merged_batch)
            logger.info(f"[EXTRACT] Batch {batch_num}/{total_batches} OK")

        except json.JSONDecodeError as e:
            logger.exception(f"[EXTRACT] Batch {batch_num} JSON parse failed: {e}")
            if finish_reason == "length":
                logger.warning(
                    f"[EXTRACT] Batch {batch_num} truncated — consider lowering DEPLOYMENT_BATCH_SIZE"
                )
            # Fallback: keep original controls without deployment points
            final_controls.extend(batch)

        except Exception as e:
            logger.exception(f"[EXTRACT] Batch {batch_num} API error: {e}")
            final_controls.extend(batch)

    logger.info(f"[EXTRACT] Complete: {len(final_controls)} controls extracted")
    return final_controls


def convert_to_section_structure(controls: list, resource_type: str = "framework") -> list:
    """
    Convert flat control list to section-wise nested structure.
    Sections are determined by:
    1. Section_name from control (if provided)
    2. Control ID prefix (e.g., "A.6" from "A.6.1")
    3. Default "No Section"
    """
    if not controls:
        logger.warning("[STRUCTURE] Empty controls list")
        return []

    sections_map = {}
    section_order = []

    def _title_case(text):
        if text is None:
            return ""
        return str(text).strip().title()

    for idx, ctrl in enumerate(controls):
        # Extract fields based on resource type
        if resource_type == "framework":
            ctrl_id = str(ctrl.get("Control_id") or f"CTR-{idx+1:03d}").strip()
            ctrl_name = str(ctrl.get("Control_name") or "").strip()
            ctrl_desc = str(ctrl.get("Control_description") or "").strip()
            raw_dp = ctrl.get("Deployment_points") or ""
            section_name = str(ctrl.get("Section_name") or "").strip()
        else:
            ctrl_id = str(ctrl.get("Control_id") or f"CTR-{idx+1:03d}").strip()
            ctrl_name = str(ctrl.get("Client_control_name") or ctrl.get("Control_name") or "").strip()
            ctrl_desc = str(
                ctrl.get("Client_control_description") or ctrl.get("Control_description") or ""
            ).strip()
            raw_dp = ctrl.get("Client_deployment_points") or ctrl.get("Deployment_points") or ""
            section_name = str(ctrl.get("Section_name") or "").strip()

        # Extract ID prefix for section grouping
        parts = re.split(r"[.\-]", ctrl_id)
        if len(parts) >= 2 and parts[0] not in ("CTR",):
            two_part_prefix = f"{parts[0]}.{parts[1]}"
            one_part_prefix = parts[0]
            id_prefix = two_part_prefix if len(parts) > 2 else one_part_prefix
        else:
            id_prefix = None

        # Determine section name with priority
        if id_prefix:
            sec_key = id_prefix.upper()
            sec_id = id_prefix.upper()
            sec_display_name = (
                _title_case(clean_section_name(section_name))
                if section_name
                else _title_case(clean_section_name(id_prefix))
            )
        elif section_name:
            sec_key = section_name.upper().strip()
            sec_display_name = _title_case(clean_section_name(section_name))
            sec_id = None
        else:
            sec_key = "NO_SECTION"
            sec_display_name = "No Section"
            sec_id = None

        # Create section if new
        if sec_key not in sections_map:
            sec_idx = len(section_order) + 1
            sections_map[sec_key] = {
                "id": sec_id if sec_id else f"SEC-{sec_idx:02d}",
                "name": sec_display_name,
                "controls": [],
            }
            section_order.append(sec_key)

        # Parse deployment points
        dp_list = _parse_deployment_points(raw_dp, ctrl_id)

        # Create control object
        control_obj = {
            "id": ctrl_id,
            "name": ctrl_name.strip().lower() if ctrl_name.strip() else ctrl_id,
            "description": ctrl_desc,
            "deployment_points": dp_list,
        }

        sections_map[sec_key]["controls"].append(control_obj)

    result = [sections_map[k] for k in section_order]
    total_ctrls = sum(len(s["controls"]) for s in result)
    logger.info(f"[STRUCTURE] Built {len(result)} sections with {total_ctrls} controls")
    return result


def _parse_deployment_points(raw: Any, ctrl_id: str) -> list:
    """
    Parse deployment points string into structured list of dicts.
    Handles numbered format: "1. Do X\n2. Do Y"
    """
    if not raw:
        return []

    if isinstance(raw, list):
        result = []
        for i, item in enumerate(raw):
            if isinstance(item, dict):
                result.append(
                    {
                        "id": item.get("id") or f"DP-{i+1:03d}",
                        "name": str(item.get("name") or item.get("dp") or ""),
                        "status": item.get("status", "pending"),
                        "path": item.get("path", ""),
                        "source": item.get("source", ""),
                        "weightage": item.get("weightage", 10),
                        "remark": item.get("remark", ""),
                    }
                )
            else:
                result.append(
                    {
                        "id": f"DP-{i+1:03d}",
                        "name": str(item).strip(),
                        "status": "pending",
                        "path": "",
                        "source": "",
                        "weightage": 10,
                        "remark": "",
                    }
                )
        return result

    # Parse numbered string: "1. ...\n2. ..." format
    raw_str = str(raw).strip()
    points = re.split(r"\n?\s*\d+\.\s+", raw_str)
    points = [p.strip() for p in points if p.strip()]

    result = []
    for i, point in enumerate(points):
        result.append(
            {
                "id": f"DP-{i+1:03d}",
                "name": point,
                "status": "pending",
                "path": "",
                "source": "",
                "weightage": 10,
                "remark": "",
            }
        )
    return result
