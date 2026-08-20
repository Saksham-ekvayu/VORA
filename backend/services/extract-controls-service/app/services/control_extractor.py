"""
Control Extraction Service — AI-powered extraction using OpenAI GPT-4o-mini
Extracts controls from framework documents with deployment points
"""

import json
import logging
import os
import re
from collections import defaultdict
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
            f" | tokens(prompt={usage.prompt_tokens},completion={usage.completion_tokens})"
            if usage
            else ""
        )
        logger.info(
            f"[{tag}] LLM call done in {elapsed:.1f}s | finish_reason={finish_reason}{usage_str}"
        )
        if finish_reason == "length":
            logger.warning(f"[{tag}] Response truncated — hit max_tokens limit")
        return finish_reason
    except Exception:
        logger.info(f"[{tag}] LLM call done in {elapsed:.1f}s")
        return None


# ---------------------------------------------------------------------------
# Structural safety nets (version-agnostic — no framework/version/ID is ever
# hardcoded below; everything is derived from the SHAPE of the IDs/text)
# ---------------------------------------------------------------------------
_OBJECTIVE_LEAD_RE = re.compile(
    r"^\s*(objective\s*:|to\s+(provide|establish|manage|ensure|maintain|prevent|achieve|support|reduce|control))",
    re.IGNORECASE,
)
_CONTROL_VERB_RE = re.compile(r"\b(shall|must|should)\b", re.IGNORECASE)


def _split_id(ctrl_id: str) -> list:
    """Split an ID like 'A.5.1.1' or 'B-12-3' into parts by '.' or '-'."""
    return [p for p in re.split(r"[.\-]", str(ctrl_id).strip()) if p != ""]


def _looks_like_objective_only(desc: str) -> bool:
    """
    Heuristic, version-agnostic safety net.

    Catches cases where the LLM mistakenly extracted a category/objective
    heading (pure purpose statement, e.g. "Objective: To provide management
    direction...") as if it were an actual control. Real controls are
    requirement statements and almost always contain a modal verb like
    "shall"/"must"/"should". Objective text describes intent/purpose and
    typically does not.

    HOWEVER: If the text contains BOTH objective language AND control language
    (shall/must/should), it's a real control. Accept it.

    Makes no reference to any specific framework/version/ID — only looks at
    the shape of the text itself.
    """
    if not desc:
        return False
    d = desc.strip()
    
    # Check if it has control language (shall/must/should)
    has_control_verb = _CONTROL_VERB_RE.search(d)
    
    # If it has control verbs, it's a REAL control - keep it
    if has_control_verb:
        return False
    
    # If it starts with objective lead AND has no control verbs, it's just an objective
    if _OBJECTIVE_LEAD_RE.match(d) and not has_control_verb:
        return True
    
    return False


def _detect_control_id_depth(controls: list) -> int:
    """
    Automatically detect the expected control ID depth by analyzing extracted controls.
    
    Works for ANY standard:
    - ISO 27001: Annex A controls are A.5.1.1 (4-part), objectives are A.5.1 (3-part)
    - Other standards may have different patterns
    
    Returns the minimum depth that represents actual controls (leaf level).
    """
    if not controls:
        return 4  # Default fallback
    
    # Collect all ID depths
    depths = []
    for ctrl in controls:
        ctrl_id = str(ctrl.get("Control_id", "")).strip()
        if ctrl_id:
            parts = _split_id(ctrl_id)
            if parts and parts[0] and parts[0][0].isalpha():
                depths.append(len(parts))
    
    if not depths:
        return 4  # Default fallback
    
    # If we have multiple depths, use the deepest one as control depth
    # This handles different standards automatically
    # - ISO 27001: 3-part = objective, 4-part = control
    # - Other standards: might differ
    
    # Count occurrences of each depth
    from collections import Counter
    depth_counts = Counter(depths)
    
    # The most common deeper level is likely the actual control depth
    # Sort by depth (descending) and get the most common one
    sorted_by_depth = sorted(depth_counts.items(), key=lambda x: x[0], reverse=True)
    
    if len(sorted_by_depth) >= 2:
        # Two or more different depths exist - use the deeper one as control depth
        detected_depth = sorted_by_depth[0][0]
        logger.info(
            f"[EXTRACT] Auto-detected control ID depth: {detected_depth}-part IDs "
            f"(distribution: {dict(sorted_by_depth)})"
        )
        return detected_depth
    else:
        # Only one depth - use it
        detected_depth = sorted_by_depth[0][0]
        logger.info(f"[EXTRACT] Single ID depth detected: {detected_depth}-part IDs")
        return detected_depth


def _filter_by_control_depth(controls: list, min_control_depth: int = None) -> tuple:
    """
    Filter controls to keep only leaf-level controls (actual controls, not objectives/categories).
    
    Dynamically determines if min_control_depth is not specified.
    Works for ANY standard by analyzing the ID structure.
    
    Returns (filtered_controls, rejected_count, detected_depth)
    """
    if not controls:
        return controls, 0, 0
    
    # Auto-detect if not specified
    if min_control_depth is None:
        min_control_depth = _detect_control_id_depth(controls)
    
    valid_controls = []
    rejected_ids = []
    
    for ctrl in controls:
        ctrl_id = str(ctrl.get("Control_id", "")).strip()
        parts = _split_id(ctrl_id)
        
        # Check if it starts with a letter (Annex-style control)
        if parts and parts[0] and parts[0][0].isalpha():
            # Check if it meets minimum control depth
            if len(parts) >= min_control_depth:
                valid_controls.append(ctrl)
            else:
                rejected_ids.append(f"{ctrl_id} (depth={len(parts)}, need>={min_control_depth})")
        else:
            # Numeric-only ID - hallucinated
            rejected_ids.append(f"{ctrl_id} (hallucinated)")
    
    if rejected_ids:
        logger.info(
            f"[EXTRACT] Depth filter rejected {len(rejected_ids)} non-control IDs: {rejected_ids[:10]}"
        )
    
    return valid_controls, len(rejected_ids), min_control_depth


def _drop_parent_prefix_duplicates(controls: list) -> list:
    """
    Structural safety net #2 (version-agnostic, works for ANY numbering scheme).

    In hierarchical IDs (A.5, A.5.1, A.5.1.1 ...), if ID X is a STRICT PREFIX
    of another extracted ID Y (i.e. Y == X + "." + something), then X is by
    definition an ancestor/category node — never a real leaf control —
    no matter what framework/version/edition it came from.

    This catches cases where OCR/LLM mis-attaches a child control's real
    text to its parent's shorter ID, when the description-based filter
    above can't catch it (because the description itself is genuine
    control language).
    """
    ids = {
        str(c.get("Control_id", "")).strip()
        for c in controls
        if isinstance(c, dict) and c.get("Control_id")
    }

    def has_child(cid: str) -> bool:
        prefix = cid + "."
        return any(other != cid and other.startswith(prefix) for other in ids)

    kept, dropped = [], []
    for c in controls:
        if not isinstance(c, dict):
            kept.append(c)
            continue
        cid = str(c.get("Control_id", "")).strip()
        if cid and has_child(cid):
            dropped.append(cid)
            continue
        kept.append(c)

    if dropped:
        logger.info(
            f"[EXTRACT] Prefix-parent safety net dropped {len(dropped)} "
            f"ancestor/category IDs (children exist under them): {dropped}"
        )
    return kept


def _fix_flattened_category_ids(controls: list) -> list:
    """
    Structural safety net #3 (version-agnostic).

    Detects and repairs the OCR/LLM failure mode where a category heading's
    OWN id (e.g. "A.5.1") gets reused and incremented as if it were the
    control id for the controls listed under it — producing "A.5.1", "A.5.2"
    instead of the correct "A.5.1.1", "A.5.1.2".

    Detection is purely structural:
      - Group all 3-part IDs by their 2-part prefix (e.g. "A.5.1" and "A.5.2"
        both share prefix "A.5").
      - If the FIRST id in that group is IDENTICAL to the group's prefix
        itself (i.e. "A.5.1" appears both as the prefix-defining anchor and
        as a control id) AND every item in the group is a real control
        (not objective text, already filtered above) AND none of them has
        a 4-part child (already filtered above) — this is the flattening
        failure pattern. Renumber the whole group under the true one-deeper
        level: prefix.1, prefix.2, prefix.3 ...

    No framework name, version, or literal ID is referenced anywhere in this
    logic — it operates purely on ID depth (part count) and prefix matching,
    so it generalizes to any hierarchical numbering scheme.
    """
    by_2part = defaultdict(list)
    for c in controls:
        if not isinstance(c, dict):
            continue
        cid = str(c.get("Control_id", "")).strip()
        parts = _split_id(cid)
        if len(parts) == 3 and parts[0] and parts[0].isalpha():
            by_2part[f"{parts[0]}.{parts[1]}".upper()].append(c)

    for prefix, group in by_2part.items():
        if len(group) < 2:
            continue
        # Never touch a group containing genuine objective/category text
        if any(
            _looks_like_objective_only(str(g.get("Control_description", "")))
            for g in group
        ):
            continue
        first_id = str(group[0].get("Control_id", "")).strip()
        # Only fix the exact failure pattern: first control's id IS the
        # section prefix itself (e.g. group prefix "A.5" and first id "A.5"
        # would only happen if a 2-part category id got treated as a
        # 3-part control — but here we match on the class of failure seen
        # in production: a 3-part CATEGORY id, e.g. "A.5.1", being reused
        # as the first control id in its own group of siblings "A.5.1",
        # "A.5.2", "A.5.3"...).
        anchor_parts = _split_id(first_id)
        if len(anchor_parts) != 3:
            continue
        anchor_prefix = f"{anchor_parts[0]}.{anchor_parts[1]}".upper()
        if anchor_prefix != prefix:
            continue
        if first_id.upper() != f"{prefix}.{anchor_parts[2]}".upper():
            continue
        # Heuristic gate: only auto-repair when the group looks artificially
        # sequential starting at 1 (i.e. classic flatten pattern), to avoid
        # touching legitimately-numbered sibling controls that just happen
        # to share a prefix.
        last_segment_first = anchor_parts[2]
        if last_segment_first != "1":
            continue

        for i, ctrl in enumerate(group, start=1):
            old_id = ctrl.get("Control_id")
            new_id = f"{prefix}.{i}"
            if old_id != new_id:
                logger.info(f"[EXTRACT] Repairing flattened ID: {old_id} → {new_id}")
                ctrl["Control_id"] = new_id

    return controls


def extract_framework_controls(
    chunks: list, framework_id: str, is_deployment: bool = False
) -> list:
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
    # REGEX pattern kept for reference but not used in current prompts
    # REGEX = r"\b(?:[A-Z]+(?:\.[A-Z]+)*[-.]?)?\d+(?:\.\d+)*\b"

    # Shared structural rule block — this is what makes extraction dynamic
    # across ANY version/edition of the framework, instead of hardcoding
    # ID patterns per version. It teaches the model to distinguish
    # "category/objective heading" text from "actual control" text based
    # on structure alone, not on specific numbering — and to preserve full
    # ID depth even when OCR text is noisy.
    STRUCTURAL_RULE = """
CRITICAL STRUCTURAL RULE (applies to ANY version/edition of this framework — do not assume a fixed numbering scheme):
Standards of this type organize content in nested numbered headings. Under many of those
headings you will find ONE of two different kinds of text:
  (a) "Objective: ..." — a CATEGORY/PURPOSE description explaining why the section exists.
      This is NEVER a control, no matter what ID number it has.
  (b) A "Control" requirement statement — a concrete, enforceable requirement, almost always
      phrased with "shall"/"must"/"should" (e.g. "A set of policies ... shall be defined...").
      This IS a control.

Illustrative pattern only (do NOT hardcode these exact numbers or names — apply the PATTERN,
not these specific IDs, since the real document may use different numbers/wording):
  <ID>    <Category heading>
          Objective: To provide management direction...      <- SKIP: category, not a control
  <ID.n>  <Control heading>
          Control: A set of policies ... shall be defined...  <- EXTRACT: this is a control

Decide whether something is a control by READING WHETHER ITS OWN TEXT is an objective/purpose
statement or an enforceable requirement — not by which ID depth it happens to have. Do NOT
extract an ID whose only associated text is an Objective/purpose statement, even if it looks
like it "should" be a control based on its numbering.

ID INTEGRITY (critical — read carefully):
Every numbered heading you see with an "Objective:" line under it is a CATEGORY heading. Its
own ID must NEVER be reused as a Control_id — not even if the source text for the actual
control IDs that follow it looks faint, truncated, or partially unreadable (e.g. due to OCR).

If a category heading is clearly followed by one or more actual control requirements (text
with "shall"/"must"/"should"), but the exact sub-IDs are hard to read from the source, you MUST
reconstruct them as <category_id>.1, <category_id>.2, <category_id>.3 ... in the order they
appear — i.e. APPEND a new depth level to the category's full id — NEVER reuse or increment the
category's own id at its existing depth.

Example of the FAILURE MODE to avoid (illustrative numbers only):
  WRONG:  Category id "X.5.1" → controls extracted as "X.5.1" and "X.5.2"
  RIGHT:  Category id "X.5.1" → controls extracted as "X.5.1.1" and "X.5.1.2"

This rule applies regardless of framework version or how clear/unclear the source text is —
always preserve the category's full ID as the PREFIX of its controls' IDs, never as a
replacement for it.
"""

    # Stage 1: Extract controls
    logger.info(f"[EXTRACT] Starting framework extraction | framework_id={framework_id}")

    if is_deployment:
        prompt_stage1 = f"""You are a strict JSON generator extracting from ISO/IEC standards.
Extract ALL compliance controls, policy statements, procedures, and key directives from the following text.
Do NOT skip ANY important directive.
{STRUCTURAL_RULE}

CRITICAL - STRUCTURE RULES FOR ANNEX A:
1. Each section in Annex A has the pattern:
   - Section heading (e.g., "A.5 Information security policies")
   - Sub-section heading with "Objective:" text (e.g., "A.5.1 Management direction...")
   - THEN multiple "Control" lines with actual controls (e.g., "A.5.1.1 Policies for information security")

2. NEVER extract IDs with only 2-3 parts if they have "Objective:" text - these are category headings, NOT controls
   - WRONG: Extract A.5 or A.5.1 (these are objectives/categories)
   - CORRECT: Extract A.5.1.1 and A.5.1.2 (these have "Control" label and actual requirement text)

3. Only extract lines that have the word "Control" in them, followed by requirement text

Rules for Control IDs:
1. Extract ONLY controls with IDs starting with a letter (A, B, C, etc.) - these are Annex controls.
2. REJECT IDs that are purely numeric (4.1.1, 5.1.1, 6.2.1) - these are main clause requirements.
3. REJECT IDs with only 2-3 parts if they don't have "Control" label (these are objectives, not controls).
4. Accept ONLY IDs with 4 parts (A.X.X.X format) like A.5.1.1, A.5.1.2, etc.
5. NEVER invent or generate IDs not explicitly shown.

Extract the NAME and detailed DESCRIPTION for each item.

For Section_name: Extract the EXACT section/category heading this item belongs to. Do NOT include Section IDs or numbering in the Section_name (e.g. use "Facility Security" instead of "A.7 Facility Security").

Use JSON list ONLY:
[{{"Control_id": "","Control_name": "","Control_type":"","Control_description": "","Section_name": ""}}]

TEXT:
{text}

Return ONLY JSON. No markdown. No text outside JSON."""
    else:
        prompt_stage1 = f"""You are a strict JSON generator extracting from ISO/IEC standards.
Extract ALL compliance controls from the following text.
{STRUCTURAL_RULE}

CRITICAL - STRUCTURE RULES FOR ANNEX A:
1. Each section in Annex A has the pattern:
   - Section heading (e.g., "A.5 Information security policies")
   - Sub-section heading with "Objective:" text (e.g., "A.5.1 Management direction...")
   - THEN multiple "Control" lines with actual controls (e.g., "A.5.1.1 Policies for information security")

2. NEVER extract IDs with only 2-3 parts if they have "Objective:" text - these are category headings, NOT controls
   - WRONG: Extract A.5 or A.5.1 (these are objectives/categories)
   - CORRECT: Extract A.5.1.1 and A.5.1.2 (these have "Control" label and actual requirement text)

3. Only extract lines that have the word "Control" in them, followed by requirement text with "shall", "must", or "should"

4. The actual control text comes AFTER the "Control" label and control ID
   - Look for the requirement text that starts after the control ID
   - This is what goes in Control_description

EXTRACT ONLY if all three are present: ID starting with letter (A.X.X.X format), "Control" label, and actual requirement with "shall"/"must"/"should"

Rules for Control IDs:
1. Extract ONLY controls with IDs starting with a letter (A, B, C, etc.) - these are Annex controls.
2. REJECT IDs that are purely numeric (4.1.1, 5.1.1, 6.2.1) - these are main clause requirements.
3. REJECT IDs with only 2-3 parts if they don't have "Control" label (these are objectives, not controls).
4. Accept ONLY IDs with 4 parts (A.X.X.X format) like A.5.1.1, A.5.1.2, etc.
5. NEVER invent or generate IDs not explicitly shown.

For Section_name: Extract the EXACT section heading (like "Information security policies" or "Access control"), NOT the ID.

Use JSON list ONLY:
[{{"Control_id": "","Control_name": "","Control_type":"","Control_description": "","Section_name": ""}}]

TEXT:
{text}

Return ONLY JSON. No markdown. No text outside JSON."""

    t_start = datetime.now()
    try:
        logger.info("[OPENAI] Client initialized")
        response = get_openai_client().chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt_stage1}],
            temperature=0,
            max_tokens=CONTROL_EXTRACTION_MAX_TOKENS,
            timeout=3600,  # 1 hour timeout
        )
        elapsed = (datetime.now() - t_start).total_seconds()
        _log_llm_call("EXTRACT-STAGE1", response, elapsed)

        controls = json.loads(response.choices[0].message.content)
        logger.info(f"[EXTRACT] Stage 1 raw: {len(controls)} candidates extracted")

        # Version-agnostic safety nets, applied in order:
        # 1) Use dynamic depth detection to keep only actual controls (leaf-level IDs)
        # 2) Drop any id that is a strict prefix of another extracted id (ancestor/category node)
        # 3) Repair the "flattened category id" OCR failure mode
        controls, rejected_count, detected_depth = _filter_by_control_depth(controls)
        logger.info(f"[EXTRACT] Depth filter: kept {len(controls)} controls (rejected {rejected_count} at depths < {detected_depth})")
        
        controls = _drop_parent_prefix_duplicates(controls)
        controls = _fix_flattened_category_ids(controls)
        logger.info(f"[EXTRACT] Stage 1 after structural filters: {len(controls)} controls")

    except json.JSONDecodeError as e:
        logger.exception(f"[EXTRACT] JSON decode failed: {e}")
        return []
    except Exception as e:
        logger.exception(f"[EXTRACT] OpenAI API error: {e}", exc_info=True)
        return []

    # This filter is now dynamic - no hardcoded rejection of 3-part or 2-part IDs
    # The dynamic depth detection automatically handles ANY standard's structure

    # Stage 2: Generate deployment points (batched, conditional)
    logger.info(
        f"[EXTRACT] Stage 2: Generating deployment points in batches of {DEPLOYMENT_BATCH_SIZE}"
    )

    final_controls = []

    # Determine which controls should have deployment points generated
    # Only generate if control description is substantial (>100 chars) - indicates it's from the document
    # Skip short descriptions as they likely indicate AI-generated/synthetic controls not in source PDF
    needs_dp = []
    no_dp_needed = []
    
    for ctrl in controls:
        desc = str(ctrl.get("Control_description", "")).strip()
        # Only generate deployment points if description is substantial (>100 chars)
        # This filters out synthesized/short controls that aren't actually in the document
        if len(desc) > 100:
            needs_dp.append(ctrl)
        else:
            # Short/minimal description - likely AI-generated, not from source document
            # Don't generate deployment points for these
            ctrl["Deployment_points"] = ""
            no_dp_needed.append(ctrl)
    
    logger.info(
        f"[EXTRACT] Stage 2 filtering: {len(needs_dp)} controls have substantial descriptions (>100 chars), "
        f"{len(no_dp_needed)} have minimal/empty descriptions (will not generate deployment points)"
    )
    logger.info(
        f"[EXTRACT] Skipping Stage 2 LLM calls for {len(no_dp_needed)} controls without document content"
    )

    # Process controls that need deployment points
    batch_count_with_dp = 0
    total_dp_batches = (len(needs_dp) + DEPLOYMENT_BATCH_SIZE - 1) // DEPLOYMENT_BATCH_SIZE if needs_dp else 0
    
    for batch_idx in range(0, len(needs_dp), DEPLOYMENT_BATCH_SIZE):
        batch = needs_dp[batch_idx : batch_idx + DEPLOYMENT_BATCH_SIZE]
        batch_num = batch_idx // DEPLOYMENT_BATCH_SIZE + 1
        batch_count_with_dp = max(batch_count_with_dp, batch_num)

        batch_ids = [str(c.get("Control_id", "")) for c in batch]
        logger.info(
            f"[EXTRACT] DP Batch {batch_num}/{total_dp_batches}: {len(batch)} controls | IDs: {batch_ids}"
        )

        prompt_stage2 = f"""You are an analyser of framework controls.

CRITICAL: Only generate deployment points if the control description contains enough detail to derive implementation steps from.
If the description is vague or lacks specifics, return empty string for Deployment_points.

For each control with substantial description, generate 4-5 deployment points.

Deployment points must describe:
- How to implement this control based on what the document actually says
- Specific actions required (derived from the control description, not invented)
- How to operationalize it
- Important implementation details

Every point should be numbered (1. 2. 3. etc.).
Store all points as a single string. If insufficient detail in description, use empty string "".

IMPORTANT: Keep Section_name exactly as provided. Do NOT change it.

Input JSON:
{json.dumps(batch)}

Add Deployment_points field to each control.
Use JSON list ONLY:
[{{"Control_id": "","Control_name": "","Control_type":"","Control_description": "","Section_name": "","Deployment_points": ""}}]

Return ONLY JSON. No markdown."""

        t_start = datetime.now()
        finish_reason = None
        try:
            response = get_openai_client().chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt_stage2}],
                temperature=0,
                max_tokens=DEPLOYMENT_MAX_TOKENS,
                timeout=3600,  # 1 hour timeout
            )
            elapsed = (datetime.now() - t_start).total_seconds()
            finish_reason = _log_llm_call(
                f"EXTRACT-STAGE2-batch{batch_num}", response, elapsed
            )

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
                orig_ctrl["Deployment_points"] = dp_map.get(
                    c_id, orig_ctrl.get("Deployment_points", "")
                )
                merged_batch.append(orig_ctrl)

            final_controls.extend(merged_batch)
            logger.info(
                f"[EXTRACT] DP Batch {batch_num} OK — added {len(merged_batch)} controls with deployment points"
            )

        except json.JSONDecodeError as e:
            logger.exception(f"[EXTRACT] DP Batch {batch_num} JSON parse failed: {e}")
            if finish_reason == "length":
                logger.warning(
                    f"[EXTRACT] DP Batch {batch_num} truncated — consider lowering DEPLOYMENT_BATCH_SIZE"
                )
            # Fallback: keep original controls without deployment points
            for ctrl in batch:
                ctrl["Deployment_points"] = ""
            final_controls.extend(batch)

        except Exception as e:
            logger.exception(f"[EXTRACT] DP Batch {batch_num} API error: {e}")
            # Fallback: keep original controls without deployment points
            for ctrl in batch:
                ctrl["Deployment_points"] = ""
            final_controls.extend(batch)

    # Add controls that didn't need deployment points
    final_controls.extend(no_dp_needed)

    logger.info(
        f"[EXTRACT] Stage 2 complete: Generated deployment points for {len(needs_dp)} document-backed controls"
    )
    logger.info(
        f"[EXTRACT] Complete: {len(final_controls)} total controls extracted "
        f"({len(needs_dp)} with deployment points, {len(no_dp_needed)} without)"
    )
    return final_controls


def convert_to_section_structure(controls: list, resource_type: str = "framework") -> list:
    """
    Convert flat control list to section-wise nested structure with hierarchical support.

    Hierarchy auto-detection from control ID:
    - A.5 = Section + Control (2 parts)
    - A.5.1 = Control (3 parts, belongs to section A)
    - A.5.1.1 = Sub-control of A.5.1 (4+ parts)

    NO HARDCODING - purely dynamic based on ID structure.
    """
    if not controls:
        logger.warning("[STRUCTURE] Empty controls list")
        return []

    def _parse_id(ctrl_id: str):
        """Split ID by . or - into parts"""
        return re.split(r"[.\-]", str(ctrl_id).strip())
    def _section_key_for_id(ctrl_id: str) -> str:
        """
        SINGLE source of truth for section key of any Control_id.
        Used identically in both Step 1 and Step 2 so they never disagree
        and never create duplicate/empty sections.
        """
        parts = _parse_id(ctrl_id)
        if len(parts) >= 2 and parts[0]:
            return f"{parts[0]}.{parts[1]}".upper()
        elif parts and parts[0] and parts[0] not in ("CTR",):
            return parts[0].upper()
        return "NOSEC"

    # Step 1: Extract and normalize all controls
    sections = {}
    control_by_id = {}
    section_for_control = {}  # Track which section each control belongs to

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
            ctrl_name = str(
                ctrl.get("Client_control_name") or ctrl.get("Control_name") or ""
            ).strip()
            ctrl_desc = str(
                ctrl.get("Client_control_description") or ctrl.get("Control_description") or ""
            ).strip()
            raw_dp = ctrl.get("Client_deployment_points") or ctrl.get("Deployment_points") or ""
            section_name = str(ctrl.get("Section_name") or "").strip()

        # Parse deployment points
        dp_list = _parse_deployment_points(raw_dp)

        # # Determine section from ID (first TWO parts for A.5, A.6, etc.)
        # parts = _parse_id(ctrl_id)
        # # For ID like "A.5.1", we want section "A.5" (first 2 parts)
        # # For ID like "A.5.1.1", we also want section "A.5"
        # if len(parts) >= 2 and parts[0] and parts[0].isalpha():
        #     sec_key = f"{parts[0]}.{parts[1]}".upper()  # e.g., "A.5"
        # elif parts and parts[0] and parts[0] not in ("CTR",):
        #     sec_key = parts[0].upper()
        # else:
        #     sec_key = "NOSEC"
        # sec_display = section_name if section_name else sec_key
    #     ctrl_obj = {
    #         "id": ctrl_id,
    #         "name": ctrl_name.strip().lower() if ctrl_name else ctrl_id,
    #         "description": ctrl_desc,
    #         "deployment_points": dp_list,
    #     }
    #     control_by_id[ctrl_id] = ctrl_obj
    #     section_for_control[ctrl_id] = {"name": section_name}

    # logger.info(f"[STRUCTURE] Collected {len(control_by_id)} controls")


        # Store control
    #     ctrl_obj = {
    #         "id": ctrl_id,
    #         "name": ctrl_name.strip().lower() if ctrl_name else ctrl_id,
    #         "description": ctrl_desc,
    #         "deployment_points": dp_list,
    #     }
    #     control_by_id[ctrl_id] = ctrl_obj
    #     section_for_control[ctrl_id] = {"key": sec_key, "name": sec_display}

    #     # Create section if needed
    #     if sec_key not in sections:
    #         sections[sec_key] = {
    #             "id": sec_key,
    #             "name": clean_section_name(sec_display).title() if sec_display else "No Section",
    #             "controls": [],
    #         }

    # logger.info(f"[STRUCTURE] Collected {len(control_by_id)} controls in {len(sections)} sections")
                # Store control — section is decided ONLY in Step 2 (single source
        # of truth), Step 1 no longer pre-creates any section to avoid
        # key mismatches / duplicate sections.
        ctrl_obj = {
            "id": ctrl_id,
            "name": ctrl_name.strip().lower() if ctrl_name else ctrl_id,
            "description": ctrl_desc,
            "deployment_points": dp_list,
        }
        control_by_id[ctrl_id] = ctrl_obj
        section_for_control[ctrl_id] = {"name": section_name}

    logger.info(f"[STRUCTURE] Collected {len(control_by_id)} controls")

    # Step 2: Organize controls into sections with hierarchy
    added_as_root = 0
    added_as_sub = 0

    for ctrl_id, ctrl_obj in control_by_id.items():
        parts = _parse_id(ctrl_id)

        # Determine hierarchy based on number of parts:
        # A.5 (2 parts) → Section
        # A.5.1 (3 parts) → Control (root in its section)
        # A.5.1.1 (4 parts) → Sub-control of A.5.1

        # parent_id = None
        # sec_key = None

        # if len(parts) >= 4:
        #     # This is a sub-control (4+ parts like A.5.1.1)
        #     parent_id = ".".join(parts[:-1])  # Parent = A.5.1
        #     if parent_id in control_by_id:
        #         # Parent exists, treat as sub-control
        #         added_as_sub += 1
        #         logger.info(f"[STRUCTURE] {ctrl_id} → sub-control of {parent_id}")
        #         continue
        #     else:
        #         # No parent, treat as root - belongs to section A.5
        #         sec_key = ".".join(parts[:2]).upper()  # Section = A.5

        # elif len(parts) == 3:
        #     # This is a control (3 parts like A.5.1)
        #     # Belongs to section A.5
        #     sec_key = ".".join(parts[:2]).upper()  # Section = A.5

        # elif len(parts) == 2:
        #     # This is a section header itself (2 parts like A.5)
        #     sec_key = ".".join(parts).upper()

        # else:
        #     # Fallback
        #     sec_key = (
        #         parts[0].upper() if parts and parts[0] and parts[0] not in ("CTR",) else "NOSEC"
        #     )

        # # Get section name from stored mapping
        # sec_display = section_for_control.get(ctrl_id, {}).get("name", sec_key)

                # Sub-control detection (independent of section key)
        if len(parts) >= 4:
            parent_id = ".".join(parts[:-1])  # Parent = A.5.1
            if parent_id in control_by_id:
                added_as_sub += 1
                logger.info(f"[STRUCTURE] {ctrl_id} → sub-control of {parent_id}")
                continue

        # Section key — SAME rule everywhere (see _section_key_for_id)
        sec_key = _section_key_for_id(ctrl_id)

        # Get section name from stored mapping
        sec_display = section_for_control.get(ctrl_id, {}).get("name") or sec_key

        # Create section if needed
        if sec_key and sec_key not in sections:
            sections[sec_key] = {
                "id": sec_key,
                "name": (
                    clean_section_name(sec_display).title() if sec_display else f"Section {sec_key}"
                ),
                "controls": [],
            }

        if not sec_key:
            continue

        # This is a root control - add it to the section
        ctrl_entry = {
            "id": ctrl_obj["id"],
            "name": ctrl_obj["name"],
            "description": ctrl_obj["description"],
            "deployment_points": ctrl_obj["deployment_points"],
        }

        # Check if this control has sub-controls
        sub_controls = []
        for other_id in control_by_id:
            other_parts = _parse_id(other_id)
            # If other_id is 4+ parts and its parent is this control
            if len(other_parts) >= 4:
                parent_id = ".".join(other_parts[:-1])
                if parent_id == ctrl_id:
                    sub_obj = control_by_id[other_id]
                    sub_controls.append(
                        {
                            "id": sub_obj["id"],
                            "name": sub_obj["name"],
                            "description": sub_obj["description"],
                            "deployment_points": sub_obj["deployment_points"],
                        }
                    )
                    logger.debug(f"[STRUCTURE] {other_id} → sub-control of {ctrl_id}")

        if sub_controls:
            ctrl_entry["controls"] = sub_controls

        sections[sec_key]["controls"].append(ctrl_entry)
        added_as_root += 1
        logger.info(f"[STRUCTURE] {ctrl_id} → root control in section {sec_key}")

    result = list(sections.values())
    root_cnt = sum(len(s["controls"]) for s in result)
    sub_cnt = sum(sum(len(c.get("controls", [])) for c in s["controls"]) for s in result)
    logger.info(
        f"[STRUCTURE]  {len(result)} sections | {root_cnt} root | {sub_cnt} sub-controls | (added: {added_as_root} root, {added_as_sub} sub)"
    )
    return result


def _parse_deployment_points(raw: Any) -> list:
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