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
from app.services.pdf_loader_patch import load_pdf_document

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

# How many extra "did I miss anything?" verification rounds to run after the
# initial extraction. This catches the well-known LLM failure mode where,
# while generating a very long list of similar structured items in one
# shot, the model silently skips a couple of items in the middle of a run
# of closely-numbered siblings (not a truncation — finish_reason=stop, well
# under the token limit — just an omission). Each round only asks about
# whatever is still missing, so cost stays small and it naturally stops
# early once the model confirms nothing more is missing.
COMPLETENESS_MAX_ROUNDS = 2

# How many times to retry a single LLM call if it comes back truncated
# (finish_reason == "content_filter" or "length") before giving up and
# falling back to whatever was salvaged. content_filter truncation is
# NOT a token-limit issue — it can happen even on short, benign responses
# — so a retry is worth attempting even after a successful salvage,
# because the retry may return the FULL response cleanly instead of a
# partial one.
TRUNCATION_RETRY_ATTEMPTS = 3

# How many of the original text chunks (from document loading) go into a
# single Stage-1 extraction call. This is the fix for a real, observed
# failure mode: when ALL chunks of a long document are joined into one
# giant text and extracted in a SINGLE LLM call, the model has to
# enumerate a very long list of similar structured items (100+ controls)
# in one shot — and it silently drops a contiguous run of items somewhere
# in the middle of that long list (a documented LLM behavior, not a
# token-limit/truncation issue: finish_reason=stop, well under max_tokens).
# On a real ISO 27001:2005 extraction this dropped a cluster of controls
# each run, in a DIFFERENT part of the document each time, even though
# Stage 1 was otherwise perfect.
#
# The fix: split the chunks into smaller batches and run Stage-1
# independently on each batch, then merge the results. Each batch only
# has to enumerate a much shorter list, so the "long-list omission"
# failure mode has far less opportunity to occur. This is purely a
# document-chunking strategy — no framework/version/ID is referenced, so
# it applies identically to any document (ISO 27001:2005, :2013, :2022,
# ISO 9001, or anything else).
EXTRACTION_CHUNK_BATCH_SIZE = 15

# How many chunks from the END of one batch are repeated at the START of
# the next batch. This overlap guards against a control's ID and its
# requirement text being split across a batch boundary (e.g. the ID ends
# up as the last line of batch N while its description starts the first
# line of batch N+1) — without overlap, that control could be missed by
# both batches. Duplicate extractions caused by the overlap are removed
# automatically by _merge_by_control_id (dedup by Control_id).
EXTRACTION_CHUNK_OVERLAP = 2


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
        elif finish_reason == "content_filter":
            logger.warning(
                f"[{tag}] Response truncated by OpenAI's content filter mid-generation "
                f"— will attempt to salvage any complete JSON objects already generated"
            )
        return finish_reason
    except Exception:
        logger.info(f"[{tag}] LLM call done in {elapsed:.1f}s")
        return None


def _salvage_json_array(raw_text: str) -> list:
    """
    Best-effort recovery for a JSON array that got cut off mid-generation
    (e.g. finish_reason == "content_filter" or "length" truncating the
    response before the closing "]"). Rather than discarding every control
    the model already produced, walk backwards to the last COMPLETE "}"
    object boundary, close the array there, and parse just that valid
    prefix. Returns [] if nothing salvageable is found.

    This never invents data — it only recovers objects that were already
    fully generated by the model before the cutoff.
    """
    if not raw_text:
        return []

    text = raw_text.strip()

    start = text.find("[")
    if start == -1:
        return []

    depth = 0
    last_complete_end = -1
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                last_complete_end = i

    if last_complete_end == -1:
        return []

    salvaged = text[start : last_complete_end + 1] + "]"
    try:
        result = json.loads(salvaged)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass
    return []


def _merge_by_control_id(*lists: list) -> list:
    """
    Merge several candidate-control lists into one, deduplicated by
    Control_id (first occurrence wins). Used to combine salvaged results
    across multiple retry attempts — and now also across multiple
    Stage-1 batches — so a partial win from one batch/attempt and a
    different partial win from another aren't wasted; the union is kept.
    """
    seen = set()
    merged = []
    for lst in lists:
        for item in lst:
            if not isinstance(item, dict):
                continue
            cid = str(item.get("Control_id", "")).strip()
            key = cid or id(item)
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
    return merged


# ---------------------------------------------------------------------------
# Structural safety nets (version-agnostic — no framework/version/ID is ever
# hardcoded below; everything is derived from the SHAPE/CONTENT of the
# IDs/text, never from a fixed "depth" number, because real standards mix
# depths freely — e.g. in ISO 9001, "4.1" IS a leaf control (own requirement
# text) while "4.2" is NOT (pure heading; its real requirements live one
# level deeper, under 4.2.1..4.2.4). Depth alone can never tell these apart
# — only CONTENT (does this ID have its own requirement text, or only
# child headings?) can.
# ---------------------------------------------------------------------------
_OBJECTIVE_LEAD_RE = re.compile(
    r"^\s*(objective\s*:|to\s+(provide|establish|manage|ensure|maintain|prevent|achieve|support|reduce|control))",
    re.IGNORECASE,
)
_CONTROL_VERB_RE = re.compile(r"\b(shall|must|should)\b", re.IGNORECASE)


def _split_id(ctrl_id: str) -> list:
    """Split an ID like 'A.5.1.1' or 'B-12-3' into parts by '.' or '-'."""
    return [p for p in re.split(r"[.\-]", str(ctrl_id).strip()) if p != ""]


def _natural_sort_key(ctrl_id: str):
    """
    Sort key that orders hierarchical IDs the way a human expects
    (A.6.1.1, A.6.1.2, A.6.1.3, A.6.1.4, ... A.6.2.1, ...) instead of the
    accidental insertion order they were produced/merged in.

    Purely structural — splits on '.'/'-' and treats numeric parts as
    numbers (so "10" sorts after "9", not between "1" and "2") and
    non-numeric parts as text. No framework/version/ID is hardcoded here;
    this works identically for "A.5.1", "4.2.1", or any other scheme.

    This is a COSMETIC fix only — it changes the ORDER controls are
    logged/grouped in, never which controls are extracted or dropped.
    """
    parts = _split_id(ctrl_id)
    key = []
    for p in parts:
        if p.isdigit():
            key.append((0, int(p), ""))
        else:
            key.append((1, 0, p.upper()))
    return key


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

    has_control_verb = _CONTROL_VERB_RE.search(d)
    if has_control_verb:
        return False

    if _OBJECTIVE_LEAD_RE.match(d) and not has_control_verb:
        return True

    return False


def _drop_objective_only_controls(controls: list) -> list:
    """
    Structural safety net #1 (content-based, depth-agnostic, framework-agnostic).

    THIS is the primary signal for telling a heading/category apart from an
    actual control — not the ID's depth, and not proximity to a label word
    in scrambled text. Removes any extracted item whose description is
    purely an objective/purpose statement (see _looks_like_objective_only)
    rather than an enforceable requirement.

    Examples this generalizes across:
      - ISO 27001 (older editions): "A.5.1" carries only "Objective: ..."
        text -> dropped. "A.5.1.1" carries "Control: ... shall ..." -> kept.
      - Any numeric-clause standard where a heading has no requirement text
        of its own -> dropped by the same rule, regardless of its depth.
    """
    kept, dropped = [], []
    for c in controls:
        if not isinstance(c, dict):
            kept.append(c)
            continue
        desc = str(c.get("Control_description", ""))
        if _looks_like_objective_only(desc):
            dropped.append(str(c.get("Control_id", "")))
            continue
        kept.append(c)

    if dropped:
        logger.info(
            f"[EXTRACT] Objective-only safety net dropped {len(dropped)} "
            f"category/heading IDs (objective/purpose text, not a control): {dropped}"
        )
    return kept


def _drop_parent_prefix_duplicates(controls: list) -> list:
    """
    Structural safety net #2 (version-agnostic, works for ANY numbering scheme).

    In hierarchical IDs (4, 4.1, 4.2, 4.2.1 ... or A.5, A.5.1, A.5.1.1 ...),
    if ID X is a STRICT PREFIX of another extracted ID Y (i.e. Y == X + "."
    + something), then X is by definition an ancestor/heading node — never
    a real leaf control — no matter what framework/version/edition it came
    from, and no matter its own depth.

    This also catches cases where OCR/LLM mis-attaches a child control's
    real text to its parent's shorter ID, when the description-based
    filter above can't catch it (because the description itself is genuine
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
        if any(
            _looks_like_objective_only(str(g.get("Control_description", "")))
            for g in group
        ):
            continue
        first_id = str(group[0].get("Control_id", "")).strip()
        anchor_parts = _split_id(first_id)
        if len(anchor_parts) != 3:
            continue
        anchor_prefix = f"{anchor_parts[0]}.{anchor_parts[1]}".upper()
        if anchor_prefix != prefix:
            continue
        if first_id.upper() != f"{prefix}.{anchor_parts[2]}".upper():
            continue
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


def _flag_singleton_fabricated_children(controls: list) -> list:
    """
    Structural safety net #4 (version-agnostic, LOG-ONLY — does not modify data).

    Targets the failure mode where the model sees one sibling in a numbered
    family that genuinely needs fabricated child IDs and then WRONGLY
    copies that same pattern onto neighboring siblings that actually had
    their own complete text.

    LOG-ONLY by design: this is a heuristic, not a certainty, so it must
    never delete or rewrite a control on its own — only flag it for a
    human to spot-check.
    """
    ids = {
        str(c.get("Control_id", "")).strip()
        for c in controls
        if isinstance(c, dict) and c.get("Control_id")
    }

    by_parent = defaultdict(list)
    for cid in ids:
        parts = _split_id(cid)
        if len(parts) >= 2:
            parent = ".".join(parts[:-1])
            by_parent[parent].append(cid)

    suspicious = []
    for parent, children in by_parent.items():
        if len(children) == 1 and parent not in ids:
            only_child = children[0]
            if only_child.endswith(".1"):
                suspicious.append(only_child)

    if suspicious:
        logger.warning(
            f"[EXTRACT] ⚠️ POSSIBLE MISCLASSIFICATION — {len(suspicious)} control(s) look like they "
            f"may be a fabricated lone '.1' child of a parent that should have been a leaf control "
            f"itself (pattern copied from a neighboring sibling that genuinely needed children): "
            f"{sorted(suspicious)}. This is a heuristic, not a certainty — spot-check these IDs "
            f"against the source document."
        )
    return controls


def _drop_ids_with_whitespace(controls: list) -> list:
    """
    Structural safety net #7 (deterministic, shape-based, framework-agnostic).

    A genuine Control_id — numeric clause style ("9.1.2") OR letter-prefixed
    Annex style ("A.5.1.1") — is always ONE contiguous token, never
    containing a space. IDs with whitespace (e.g. "ISO 10002",
    "ISO/TR 10013") are not real clause/control IDs — they are citations
    to OTHER standards pulled from a Bibliography/Annex B reference list,
    which the LLM can misread as a control because it's followed by
    description-like prose. Pure shape check — never touches a real ID
    in any document/version.
    """
    kept, dropped = [], []
    for c in controls:
        if not isinstance(c, dict):
            kept.append(c)
            continue
        cid = str(c.get("Control_id", "")).strip()
        if cid and re.search(r"\s", cid):
            dropped.append(cid)
            continue
        kept.append(c)

    if dropped:
        logger.info(
            f"[EXTRACT] Whitespace-ID safety net dropped {len(dropped)} "
            f"non-clause reference IDs (space in ID → citation to another "
            f"standard, e.g. Bibliography entry, not a real control): {dropped}"
        )
    return kept


# ---------------------------------------------------------------------------
# DETERMINISTIC, TEXT-VERIFIED safety nets #5 and #6.
#
# These cross-check the LLM's output directly against the raw source
# `text`, so they behave identically every run. Both are driven purely by
# what is actually PRINTED in the document at runtime, never by a
# framework name/version, so they only activate for documents that
# genuinely show the corresponding structural signal.
# ---------------------------------------------------------------------------

_STANDALONE_CONTROL_LABEL_RE = re.compile(r"(?<![A-Za-z])Control(?![A-Za-z])", re.IGNORECASE)
_STANDALONE_OBJECTIVE_LABEL_RE = re.compile(r"(?<![A-Za-z])Objective\s*:", re.IGNORECASE)
_ANNEX_A_HEADING_RE = re.compile(r"\bAnnex\s+A\b", re.IGNORECASE)
_LETTER_PREFIXED_ID_RE = re.compile(r"\b[A-Z]\.\d+(?:\.\d+){1,3}\b")

# How far (in characters) to look around an ID's occurrence in the raw text
# when checking for a nearby "Control" label. This is intentionally wide
# because pdfplumber's column-linearization can push a control's own label
# well past a few hundred characters away — but since this check is now
# LOG-ONLY (see note below), the window size only affects the accuracy of
# the diagnostic warning, never whether a control is kept or dropped.
_LABEL_PROXIMITY_WINDOW = 1500


def _detect_label_based_document(text: str) -> bool:
    """
    Deterministic detection of whether this document uses the explicit
    "Control" / "Objective:" labelling convention (some Annex-catalog
    editions print this literally, e.g. ISO/IEC 27001:2005 and :2013).

    Requires BOTH markers to occur repeatedly (not just once) so an
    incidental, ordinary use of the English word "control" somewhere in
    prose can never trigger this by itself.
    """
    control_hits = len(_STANDALONE_CONTROL_LABEL_RE.findall(text))
    objective_hits = len(_STANDALONE_OBJECTIVE_LABEL_RE.findall(text))
    is_label_based = control_hits >= 5 and objective_hits >= 3
    logger.info(
        f"[EXTRACT] Document style check — literal 'Control' label occurrences={control_hits}, "
        f"literal 'Objective:' label occurrences={objective_hits} -> "
        f"{'LABEL-BASED document' if is_label_based else 'no explicit label convention detected'}"
    )
    return is_label_based


def _verify_against_control_labels(text: str, controls: list) -> list:
    """
    Diagnostic-only check (does NOT modify the controls list) — only run
    when _detect_label_based_document(text) is True.

    Historically this function DROPPED any Control_id for which the
    literal word "Control" wasn't found within a fixed window right after
    the ID's position in the raw source text. That approach caused a real
    production incident: pdfplumber's column-linearization of Annex-style
    tables can put a control's own "Control" label much farther from its
    ID than any fixed window can reliably cover, so genuine controls were
    being deleted purely because of this proximity check.

    This function is now LOG-ONLY: it still reports which IDs it could not
    verify nearby a "Control" label, purely for visibility/debugging, but
    it NEVER removes anything from the list. Real filtering for this
    document type is handled by the deterministic, content-based safety
    nets (_drop_objective_only_controls, _drop_parent_prefix_duplicates)
    and the structural annex-catalog check below, none of which depend on
    character distance in text that may have been reordered by PDF
    column-linearization.
    """
    if not controls:
        return controls

    unverified = []
    for c in controls:
        if not isinstance(c, dict):
            continue
        cid = str(c.get("Control_id", "")).strip()
        if not cid:
            continue

        idx = text.find(cid)
        if idx == -1:
            # ID doesn't appear verbatim (OCR noise, etc.) — can't verify,
            # not evidence of anything wrong. Skip silently.
            continue

        start = max(0, idx - _LABEL_PROXIMITY_WINDOW)
        end = idx + _LABEL_PROXIMITY_WINDOW
        window = text[start:end]
        if not _STANDALONE_CONTROL_LABEL_RE.search(window):
            unverified.append(cid)

    if unverified:
        logger.info(
            f"[EXTRACT] Label-proximity diagnostic (LOG-ONLY, nothing dropped): {len(unverified)} "
            f"candidate(s) had no literal 'Control' label within {_LABEL_PROXIMITY_WINDOW} chars of "
            f"their ID in the source text — likely due to column-reordering in PDF text extraction, "
            f"not a sign these are actually invalid: {unverified}"
        )
    return controls


def _detect_annex_style_document(text: str) -> bool:
    """
    Deterministic detection of an Annex-style, letter-prefixed control
    catalog — the structural pattern shared by ISO/IEC 27001 Annex A across
    ALL of its editions (2005, 2013, 2022), independent of whether that
    particular edition also happens to print literal "Objective:"/"Control"
    labels.

    Two structural signals, both checked directly against the raw text:
      1. The literal heading "Annex A" appears somewhere in the document.
      2. Letter-prefixed multi-part IDs (A.5.1, A.5.1.1, ...) appear
         repeatedly (a density threshold, so one incidental reference
         elsewhere doesn't trigger this).
    """
    has_annex_heading = bool(_ANNEX_A_HEADING_RE.search(text))
    letter_id_count = len(_LETTER_PREFIXED_ID_RE.findall(text))
    is_annex_style = has_annex_heading and letter_id_count >= 8
    logger.info(
        f"[EXTRACT] Annex-style catalog check — 'Annex A' heading found={has_annex_heading}, "
        f"letter-prefixed multi-part ID occurrences={letter_id_count} -> "
        f"{'ANNEX-STYLE CATALOG document' if is_annex_style else 'not an annex-style catalog'}"
    )
    return is_annex_style


def _restrict_to_letter_prefixed_catalog(controls: list) -> list:
    """
    Safety net #6 (deterministic, SAFE to drop with) — only applied when
    _detect_annex_style_document(text) is True.

    In a confirmed Annex-style catalog document, only letter-prefixed,
    3+ part IDs (A.5.1, A.5.1.1, ...) are genuine catalog controls. Any
    purely numeric ID (e.g. "4.1", "5.3" — from an un-labelled main clause
    body sitting alongside the Annex) is dropped here.

    This is SAFE to act on (unlike the proximity check above) because it
    depends only on the SHAPE of the ID itself — never on character
    distance in text that may have been reordered by PDF column
    linearization. A genuine ID like "A.5.1.1" is unaffected by column
    scrambling; it is either present in the extracted candidate list or
    it isn't.
    """
    if not controls:
        return controls

    kept, dropped = [], []
    for c in controls:
        if not isinstance(c, dict):
            kept.append(c)
            continue
        cid = str(c.get("Control_id", "")).strip()
        parts = _split_id(cid)
        if parts and parts[0] and parts[0][0].isalpha() and len(parts) >= 3:
            kept.append(c)
        else:
            dropped.append(cid)

    if dropped:
        logger.info(
            f"[EXTRACT] Annex-catalog safety net dropped {len(dropped)} non-lettered/shallow "
            f"candidate(s) — this document uses an Annex-style letter-prefixed catalog, so only "
            f"A.X.Y(.Z)-style controls count here: {dropped}"
        )
    return kept


def _run_completeness_check(text: str, controls: list, structural_rule: str) -> list:
    """
    Dynamic, framework-agnostic gap-fill pass (no ID/section/framework name
    is ever hardcoded here). Re-scans the same text against the
    already-found IDs to catch any controls the extraction still skipped
    (a known long-list omission pattern, not a truncation/token-limit
    issue). Acts as a second-layer safety net on top of the batched
    Stage-1 extraction — most gaps should already be closed by batching,
    but this still catches anything a batch boundary might have missed.
    """
    if not controls:
        return controls

    all_controls = list(controls)
    seen_ids = {
        str(c.get("Control_id", "")).strip()
        for c in all_controls
        if isinstance(c, dict) and c.get("Control_id")
    }

    if not seen_ids:
        return all_controls

    schema_fields = (
        '{"Control_id": "","Control_name": "","Control_type":"","Control_description": "","Section_name": ""}'
    )

    for round_num in range(1, COMPLETENESS_MAX_ROUNDS + 1):
        existing_ids_str = ", ".join(sorted(seen_ids))

        completeness_prompt = f"""You are auditing a compliance-control extraction for COMPLETENESS — checking
whether anything was missed, not re-doing the extraction from scratch.
{structural_rule}

Below is the SAME source text, and the list of Control_ids ALREADY extracted from it so far.

ALREADY EXTRACTED IDs ({len(seen_ids)} total):
{existing_ids_str}

YOUR TASK: Re-scan the ENTIRE text below, start to finish, and find any control whose ID is NOT
already in the list above. Pay special attention to runs of closely-numbered siblings — e.g. if
"5.6.1" and "5.6.3" are in the list but "5.6.2" is not, that is very likely a missed control; check
the text for it specifically. Apply the exact same rules as before to decide whether something is a
control (its own requirement text, phrased with "shall"/"must"/"should", directly attached to that
ID) versus a heading (no own requirement text, only introduces deeper sub-headings).

Do NOT re-list anything already in the "ALREADY EXTRACTED" list above — return ONLY items that are
genuinely missing. If, after careful re-scanning, nothing is missing, return an empty JSON list: []

Use JSON list ONLY, same schema as before:
[{schema_fields}]

TEXT:
{text}

Return ONLY JSON. No markdown. No text outside JSON."""

        round_missing = None
        for round_attempt in range(1, TRUNCATION_RETRY_ATTEMPTS + 1):
            try:
                t_start = datetime.now()
                response = get_openai_client().chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": completeness_prompt}],
                    temperature=0,
                    max_tokens=CONTROL_EXTRACTION_MAX_TOKENS,
                    timeout=3600,
                )
                elapsed = (datetime.now() - t_start).total_seconds()
                finish_reason = _log_llm_call(
                    f"EXTRACT-COMPLETENESS-round{round_num}"
                    f"{'' if round_attempt == 1 else f'-retry{round_attempt}'}",
                    response,
                    elapsed,
                )
                raw_content = response.choices[0].message.content

                try:
                    round_missing = json.loads(raw_content)
                    break
                except json.JSONDecodeError:
                    salvaged = _salvage_json_array(raw_content)
                    if salvaged:
                        round_missing = salvaged
                        if round_attempt < TRUNCATION_RETRY_ATTEMPTS:
                            logger.info(
                                f"[EXTRACT] Completeness round {round_num} attempt {round_attempt}: "
                                f"salvaged {len(salvaged)} item(s) from truncated response "
                                f"(finish_reason={finish_reason}) — retrying for a fuller result..."
                            )
                            continue
                        break
                    if round_attempt < TRUNCATION_RETRY_ATTEMPTS:
                        logger.warning(
                            f"[EXTRACT] Completeness round {round_num} attempt {round_attempt}: "
                            f"unparsable and nothing salvageable (finish_reason={finish_reason}) — retrying..."
                        )
                        continue
                    logger.info(
                        f"[EXTRACT] Completeness round {round_num}: all {TRUNCATION_RETRY_ATTEMPTS} "
                        f"attempts unparsable — stopping completeness check"
                    )
                    round_missing = None
                    break

            except Exception as e:
                logger.exception(
                    f"[EXTRACT] Completeness round {round_num} attempt {round_attempt} API error: {e}"
                )
                if round_attempt < TRUNCATION_RETRY_ATTEMPTS:
                    continue
                round_missing = None
                break

        if round_missing is None:
            break

        if not isinstance(round_missing, list) or not round_missing:
            logger.info(
                f"[EXTRACT] Completeness round {round_num}: model found nothing missing — "
                f"extraction confirmed complete"
            )
            break

        new_items = []
        for item in round_missing:
            if not isinstance(item, dict):
                continue
            cid = str(item.get("Control_id", "")).strip()
            if cid and cid not in seen_ids:
                new_items.append(item)
                seen_ids.add(cid)

        if not new_items:
            logger.info(
                f"[EXTRACT] Completeness round {round_num}: model returned items but all were "
                f"already-known duplicates — stopping check"
            )
            break

        logger.info(
            f"[EXTRACT] Completeness round {round_num}: found {len(new_items)} previously-missed "
            f"control(s): {[str(i.get('Control_id', '')) for i in new_items]}"
        )
        all_controls.extend(new_items)

    return all_controls


def _make_chunk_batches(chunks: Any, batch_size: int, overlap: int) -> list:
    """
    Split the document's text chunks into overlapping batches for Stage-1
    extraction, instead of joining everything into one giant string for a
    single LLM call. Purely mechanical (index-based) — no content
    inspection, no framework/version awareness, so it applies identically
    to any document regardless of size or structure.

    If `chunks` isn't a list (e.g. already a single string) or is small
    enough to fit in one batch, returns a single batch — behavior is
    unchanged for short documents (e.g. a short ISO 9001 excerpt with
    fewer than `batch_size` chunks still goes through exactly one call,
    exactly like before).
    """
    if not isinstance(chunks, list):
        return [str(chunks)]

    n = len(chunks)
    if n <= batch_size:
        return [" ".join(chunks)]

    step = max(1, batch_size - overlap)
    batches = []
    i = 0
    while i < n:
        batch_chunks = chunks[i : i + batch_size]
        batches.append(" ".join(batch_chunks))
        if i + batch_size >= n:
            break
        i += step
    return batches


def _build_stage1_prompt(batch_text: str, is_deployment: bool, structural_rule: str) -> str:
    """
    Build the Stage-1 extraction prompt for a given slice of document text.
    Used identically for every batch, so every batch is judged by exactly
    the same TIER 0 / TIER 1 structural rules as the old single-call
    version used for the whole document.
    """
    if is_deployment:
        return f"""You are a strict JSON generator extracting from compliance/management-system standards.
Extract ALL compliance controls, policy statements, procedures, and key directives from the following text.
Do NOT skip ANY important directive.
{structural_rule}

Rules for Control IDs and Section IDs:
1. If explicit Section and Control IDs exist in the document text, you MUST extract and use them EXACTLY as they appear — whether numeric, letter-prefixed, or any other scheme. Do NOT reject an ID because it is numeric-only or letter-only.
2. If the document does NOT contain explicit IDs, generate them sequentially starting strictly from A.1.
3. Control IDs MUST be based on their Section ID (e.g. section A.1 → controls A.1.1, A.1.2...).
4. NEVER invent or generate IDs not explicitly shown when explicit IDs already exist in the text.
5. If this document uses explicit "Control"/"Objective:" labels (TIER 0 above), ONLY extract items literally labelled "Control". Otherwise apply TIER 1.

Extract the NAME and detailed DESCRIPTION for each item.

For Section_name: Extract the EXACT section/category heading this item belongs to, without IDs or numbering.

NOTE: The text below may be a PARTIAL slice of a larger document (extraction is done in batches for
reliability on long documents). Extract everything that qualifies as a control WITHIN this slice —
do not worry about controls that might belong to text outside this slice.

Use JSON list ONLY:
[{{"Control_id": "","Control_name": "","Control_type":"","Control_description": "","Section_name": ""}}]

TEXT:
{batch_text}

Return ONLY JSON. No markdown. No text outside JSON."""
    else:
        return f"""You are a strict JSON generator extracting from compliance/management-system standards.
Extract ALL compliance controls from the following text.
{structural_rule}

EXTRACT ONLY if all three are present: an ID (numeric or letter-prefixed), a NAME/heading, and an actual
CONTROL requirement (not just an Objective/purpose statement) with wording like "shall"/"must"/"should"
attached DIRECTLY to that ID.

Rules for Control IDs and Section IDs:
1. If explicit Section and Control IDs exist in the document text, you MUST extract and use them EXACTLY as they appear — numeric, letter-prefixed, or any other scheme, and regardless of ID depth relative to other controls in the same document.
2. If the document does NOT contain explicit IDs, generate them sequentially starting strictly from A.1.
3. Control IDs MUST be based on their Section ID.
4. NEVER invent or generate IDs not explicitly shown when explicit IDs already exist in the text.
5. If this document uses explicit "Control"/"Objective:" labels (TIER 0 above), ONLY extract items literally labelled "Control". Otherwise apply TIER 1.

For Section_name: Extract the EXACT section heading, NOT the ID. When TIER 0 applies, use the nearest parent heading's title.

NOTE: The text below may be a PARTIAL slice of a larger document (extraction is done in batches for
reliability on long documents). Extract everything that qualifies as a control WITHIN this slice —
do not worry about controls that might belong to text outside this slice.

Use JSON list ONLY:
[{{"Control_id": "","Control_name": "","Control_type":"","Control_description": "","Section_name": ""}}]

TEXT:
{batch_text}

Return ONLY JSON. No markdown. No text outside JSON."""


def _run_stage1_call(prompt: str, tag: str) -> list:
    """
    Run one Stage-1 LLM call for a single batch, with the same
    truncation-retry/salvage behavior the old single-call code had.
    Returns a list of candidate control dicts (possibly empty on total
    failure — callers should treat an empty list from one batch as "no
    controls found in this slice", not as a fatal error for the whole
    extraction, since other batches may still succeed).
    """
    best_salvage: list = []

    for attempt in range(1, TRUNCATION_RETRY_ATTEMPTS + 1):
        t_start = datetime.now()
        try:
            response = get_openai_client().chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=CONTROL_EXTRACTION_MAX_TOKENS,
                timeout=3600,
            )
            elapsed = (datetime.now() - t_start).total_seconds()
            finish_reason = _log_llm_call(
                f"{tag}{'' if attempt == 1 else f'-retry{attempt}'}", response, elapsed
            )
            raw_content = response.choices[0].message.content

            try:
                parsed = json.loads(raw_content)
                if isinstance(parsed, list):
                    return parsed
                logger.warning(f"[EXTRACT] {tag} attempt {attempt}: parsed JSON was not a list — treating as empty")
                return []
            except json.JSONDecodeError as e:
                logger.warning(
                    f"[EXTRACT] {tag} attempt {attempt}: JSON decode failed "
                    f"(finish_reason={finish_reason}): {e}. Attempting salvage..."
                )
                salvaged = _salvage_json_array(raw_content)
                if salvaged:
                    best_salvage = _merge_by_control_id(best_salvage, salvaged)
                if attempt < TRUNCATION_RETRY_ATTEMPTS:
                    continue
                return best_salvage

        except Exception as e:
            logger.exception(f"[EXTRACT] {tag} attempt {attempt} API error: {e}")
            if attempt < TRUNCATION_RETRY_ATTEMPTS:
                continue
            return best_salvage

    return best_salvage


# ---------------------------------------------------------------------------
# Deployment-points guarantee helpers (THE FIX)
#
# Two related bugs this addresses:
#   1) Deployment point COUNT was inconsistent (sometimes 4, sometimes 5)
#      because the old Stage-2 prompt literally asked for "4-5 points".
#   2) Deployment points were sometimes 0/empty entirely, because any
#      control whose description was <=100 chars was SKIPPED from Stage 2
#      completely and hard-set to "" (see the old needs_dp/no_dp_needed
#      split). A control with an empty/short/low-quality description
#      would silently end up with zero deployment points in the UI.
#
# Fix: every control now goes through Stage 2, the prompt strictly
# requires exactly 5 points, and — regardless of what the LLM actually
# returns — _validate_deployment_points() deterministically pads/trims
# the result to guarantee exactly 5 points every single time. This never
# depends on the LLM "behaving"; it's enforced in code after the fact.
# ---------------------------------------------------------------------------


def _generate_default_deployment_points(control_name: str) -> str:
    """
    Generate 5 generic-but-sensible deployment points when the control's
    description is too thin/empty for the LLM to derive real steps from.
    Used as a guaranteed fallback so a control NEVER ends up with 0 points.
    """
    name = (control_name or "this control").strip() or "this control"
    points = [
        f"Assign clear ownership and responsibility for implementing {name}.",
        f"Document the policy or procedure required to operationalize {name}.",
        f"Communicate the requirements of {name} to all relevant personnel.",
        f"Establish periodic monitoring/review to verify {name} is being followed.",
        f"Maintain records or evidence demonstrating {name} is implemented and maintained.",
    ]
    return "\n".join(f"{i+1}. {p}" for i, p in enumerate(points))


def _validate_deployment_points(raw: Any, control_name: str = "") -> str:
    """
    Deterministic safety net: guarantees the returned string ALWAYS has
    EXACTLY 5 numbered deployment points, no matter what the LLM returned
    (0, 3, 4, 6, malformed, or empty). This is what actually fixes the
    "sometimes 4, sometimes 0" bug — it doesn't rely on the LLM behaving,
    it enforces the count in code after the fact.
    """
    if not raw or not str(raw).strip():
        return _generate_default_deployment_points(control_name)

    raw_str = str(raw).strip()
    points = re.split(r"\n?\s*\d+\.\s+", raw_str)
    points = [p.strip() for p in points if p.strip()]

    if not points:
        return _generate_default_deployment_points(control_name)

    if len(points) > 5:
        points = points[:5]
    elif len(points) < 5:
        default_texts = [
            re.sub(r"^\d+\.\s*", "", d)
            for d in _generate_default_deployment_points(control_name).split("\n")
        ]
        i = 0
        while len(points) < 5 and i < len(default_texts):
            if default_texts[i] not in points:
                points.append(default_texts[i])
            i += 1
        while len(points) < 5:
            points.append("Review and reinforce adherence to this control periodically.")

    return "\n".join(f"{i+1}. {p}" for i, p in enumerate(points))


def extract_framework_controls(
    chunks: list, framework_id: str, is_deployment: bool = False
) -> list:
    """
    Extract controls from framework document using AI.
    Three-stage extraction:
    1. Extract Control_id, Control_name, Control_description, Section_name
       — done in BATCHES across the document's chunks (see
       EXTRACTION_CHUNK_BATCH_SIZE) so no single LLM call ever has to
       enumerate the full control list at once. This is the fix for the
       "long-list omission" failure mode where a single giant call
       silently drops a cluster of items somewhere in the middle.
    2. Completeness check — re-scan for any control the batched pass
       still missed (second-layer safety net, catches batch-boundary
       edge cases).
    3. Generate Deployment_points for EVERY control (in batches) —
       guaranteed exactly 5 points per control, never 0, never 4/6.
    """
    if not chunks:
        logger.warning("[EXTRACT] No chunks provided")
        return []

    text = " ".join(chunks) if isinstance(chunks, list) else str(chunks)

    STRUCTURAL_RULE = """
CRITICAL STRUCTURAL RULE (applies to ANY version/edition of this framework — do not assume a fixed
numbering scheme, and NEVER decide control-vs-heading by counting ID depth/parts):

⚠️ NOTE ON EXAMPLES BELOW: Any ID like "X.Y" or "X.Y.1" used in this rule is a PLACEHOLDER, not a
real clause number. It does NOT refer to any actual section of the document you are about to read.
Even if the document below happens to contain a clause with a similar-looking number, that is pure
coincidence — judge that clause ONLY by reading its own text, never by matching it to a number
used in this instruction.

═══════════════════════════════════════════════════════════════════════════
STEP 0 — FIRST, CHECK WHICH STYLE THIS DOCUMENT ACTUALLY USES (do this before
anything else, by scanning the text itself — never assume, always check):
═══════════════════════════════════════════════════════════════════════════

Some standards (often Annex-style catalogs) print an EXPLICIT, literal label word directly before
each block of text — most commonly the literal words "Objective:" and "Control". Other standards
(plain numbered-clause standards) print NO such labels anywhere.

Scan the text below FIRST and determine which case applies:

TIER 0 — THIS DOCUMENT DOES USE EXPLICIT "Control" / "Objective:" LABELS. If YES:
  - Any ID whose attached text is explicitly labelled "Objective:" is NEVER a control — skip it
    entirely, regardless of how long or requirement-like its wording sounds.
  - Any ID whose attached text is explicitly labelled "Control" IS a control — extract it using
    EXACTLY the ID printed immediately next to/above that specific "Control"-labelled text, never
    the ID of its parent "Objective:" heading.
  - Do NOT extract a parent category ID as its own separate control when "Control"-labelled child
    IDs exist beneath it.
  - Apply this labelling convention CONSISTENTLY across the WHOLE document once detected.
  - Section_name for a "Control"-labelled item is the title of its NEAREST parent heading — strip
    the ID number and the words "Objective:"/"Control" from Section_name.
  - This ID style may be letter-prefixed, numeric, or any other scheme — decide control-vs-not
    purely by the presence of the literal "Control" label, never by the ID's shape.

TIER 1 — THIS DOCUMENT DOES NOT USE "Control"/"Objective:" LABELS. Fall back to the general rule:

Standards of this type organize content in nested numbered headings. Under any given heading you
will find ONE of these:

  (a) ONLY a category/purpose description (sometimes explicitly labelled "Objective:", sometimes
      just a general framing sentence) with NO enforceable requirement of its own — followed by
      one or more DEEPER numbered sub-headings that carry the real requirements.
      -> This heading is NEVER a control, no matter what ID number it has, and no matter how many
         parts its ID has. Example (placeholder only, not a real clause number): a heading
         "X.Y Example heading" has no "shall" text directly under it — it only introduces
         sub-headings "X.Y.1", "X.Y.2" etc. which DO have real requirement text. In that case
         "X.Y" is a heading, NOT a control; "X.Y.1", "X.Y.2" etc. are the controls.

  (b) An actual, enforceable requirement statement directly under it, almost always phrased with
      "shall"/"must"/"should" (e.g. "The organization shall establish, document, implement and
      maintain a quality management system..."), and NOT further split into deeper numbered
      sub-headings for that same requirement.
      -> This IS a control, and this stays true REGARDLESS of how many parts its ID has. Example
         (placeholder only, not a real clause number): "X.Z Example clause" has its own full
         requirement text directly under it (not spread across "X.Z.1", "X.Z.2"...) — so "X.Z" IS
         a control, even though it is a shorter ID than "X.Y.1".

  THE RULE, IN ONE LINE: decide control-vs-heading purely by asking "does THIS ID have its own
  requirement text directly attached to it, or does it only introduce deeper sub-headings that
  carry the real text?" — NEVER by comparing ID depth across different IDs in the document.

  ⚠️ SIBLINGS ARE INDEPENDENT — DO NOT GENERALIZE ACROSS THEM: Clauses at the same numbering depth
  under the same parent (e.g. 4.1, 4.2, 4.3, 4.4 all under parent "4") are structurally INDEPENDENT
  of each other. It is completely normal for SOME siblings in a family to be leaf controls with
  their own text (e.g. 4.1, 4.2, 4.3 each have their own requirement text) while ONE sibling
  (e.g. 4.4) is a pure heading needing fabricated child IDs (4.4.1, 4.4.2). Finding that one
  sibling needs child IDs tells you NOTHING about whether its neighboring siblings also need child
  IDs, and vice versa. You MUST re-read each sibling's own paragraph independently before
  deciding — never assume a pattern found in one clause of a numbered family applies to the rest
  of that family.

  ⚠️ SELF-CHECK BEFORE FINALIZING — WATCH FOR SINGLETON FABRICATED CHILDREN: This is the single
  most common mistake: after drafting your list, scan it specifically for any parent ID (e.g.
  "4.1") that ended up appearing ONLY as one fabricated child ending in ".1" (i.e. you wrote
  "4.1.1") with NO sibling child anywhere else in your list (no "4.1.2", "4.1.3", ...). This
  usually means you saw a NEIGHBORING clause (e.g. "4.4") that genuinely needed multiple child IDs
  ("4.4.1", "4.4.2") and then wrongly copied that same ".1" habit onto a DIFFERENT, unrelated
  parent that actually had complete text of its own. For every such lone ".1" case: go back and
  re-read THAT PARENT'S OWN paragraph in the source text one more time, independently, ignoring
  what you decided for any other clause. If that paragraph already contains a full
  shall/must/should requirement (not merely a lead-in sentence before real sub-headings), you MUST
  output the ID WITHOUT the fabricated ".1" suffix — i.e. output "4.1", not "4.1.1". Only keep a
  ".1" suffix when the source document itself does NOT attach a complete requirement to the parent
  ID directly, and instead only introduces the requirement through an explicitly printed deeper
  sub-heading in the source text.

  ⚠️ THIS SELF-CHECK NEVER OVERRIDES A LITERALLY PRINTED ID: This self-check exists only to catch
  IDs YOU fabricated yourself with no textual basis (you added the ".1" purely by copying a pattern
  from a different, unrelated clause). If the source document text ITSELF explicitly prints a
  deeper heading or ID label (e.g. the text literally contains "4.1.1" as its own printed heading,
  even with siblings like "4.1.2", "4.1.3" nearby, or even standing alone), you MUST keep that ID
  exactly as printed — never strip or alter an ID that genuinely appears in the source text. This
  self-check is about catching your OWN invented IDs, never about second-guessing what the document
  actually prints.

BULLETED/LETTERED SUB-ITEMS ARE NOT SEPARATE CONTROLS: an internal lettered list (a, b, c...) under
one control belongs to that ONE control's description — never invent a new dotted ID level for
each bullet unless the source document itself explicitly prints that deeper numbering as a real
heading.

ID INTEGRITY: A heading whose own text is purely an objective/purpose statement must NEVER have
its ID reused as a Control_id, even if the actual control IDs that follow look faint/truncated due
to OCR. Reconstruct them as <heading_id>.1, <heading_id>.2, ... (APPEND a depth level), never reuse
or increment the heading's own ID at its existing depth.

COMPLETENESS: Do not stop early and do not skip any control just because it looks repetitive —
extract every single one that has its own requirement text, all the way to the end of the text
slice you were given.
"""

    logger.info(f"[EXTRACT] Starting framework extraction | framework_id={framework_id}")
    logger.info("[OPENAI] Client initialized")
    get_openai_client()

    # ------------------------------------------------------------------
    # STAGE 1 — BATCHED extraction.
    #
    # Instead of joining ALL chunks into one giant `text` and making a
    # SINGLE LLM call asking for the entire control list at once (the
    # "long-list omission" failure mode — the model silently drops a
    # contiguous run of items somewhere in the middle of a very long
    # structured list, non-deterministically), the document is split
    # into smaller overlapping batches. Each batch only has to enumerate
    # a much shorter list, so omission has far less room to occur.
    #
    # For short documents (chunk count <= EXTRACTION_CHUNK_BATCH_SIZE),
    # _make_chunk_batches returns exactly ONE batch containing all the
    # text — i.e. behavior is IDENTICAL to the old single-call approach
    # in that case. Nothing changes for small documents.
    #
    # NOTE: Stage 1 (extraction accuracy) is UNCHANGED by this fix —
    # only Stage 2 (deployment points) below was modified.
    # ------------------------------------------------------------------
    batches = _make_chunk_batches(chunks, EXTRACTION_CHUNK_BATCH_SIZE, EXTRACTION_CHUNK_OVERLAP)
    logger.info(
        f"[EXTRACT] Stage 1: document split into {len(batches)} batch(es) "
        f"(batch_size={EXTRACTION_CHUNK_BATCH_SIZE} chunks, overlap={EXTRACTION_CHUNK_OVERLAP} chunks)"
    )

    all_batch_results = []
    for i, batch_text in enumerate(batches, start=1):
        prompt = _build_stage1_prompt(batch_text, is_deployment, STRUCTURAL_RULE)
        batch_controls = _run_stage1_call(prompt, f"EXTRACT-STAGE1-batch{i}-of-{len(batches)}")
        logger.info(
            f"[EXTRACT] Stage 1 batch {i}/{len(batches)}: {len(batch_controls)} candidate(s) | "
            f"IDs: {[str(c.get('Control_id','')) for c in batch_controls if isinstance(c, dict)]}"
        )
        all_batch_results.append(batch_controls)

    controls = _merge_by_control_id(*all_batch_results)
    logger.info(
        f"[EXTRACT] Stage 1 raw: {len(controls)} unique candidates extracted across "
        f"{len(batches)} batch(es) (deduplicated by Control_id)"
    )

    if not controls:
        logger.error("[EXTRACT] Stage 1: no controls extracted from any batch — aborting")
        return []

    # Stage 1b: Completeness check (second-layer safety net — catches
    # anything that might still have slipped through a batch boundary)
    controls = _run_completeness_check(text, controls, STRUCTURAL_RULE)
    logger.info(f"[EXTRACT] After completeness check: {len(controls)} candidates total")

    # NEW — drop reference-list citations before any other structural filter
    controls = _drop_ids_with_whitespace(controls)
    logger.info(f"[EXTRACT] After whitespace-ID safety net: {len(controls)} candidates total")

    # Deterministic document-style detection — drives which safety nets apply
    is_label_based_doc = _detect_label_based_document(text)
    is_annex_style_doc = _detect_annex_style_document(text)

    if is_label_based_doc:
        # LOG-ONLY now — see _verify_against_control_labels docstring for
        # why this must never delete controls (pdfplumber column-scrambling
        # incident). controls list is returned unchanged.
        _verify_against_control_labels(text, controls)

    if is_annex_style_doc:
        # SAFE to filter with — shape-based, not text-distance-based.
        controls = _restrict_to_letter_prefixed_catalog(controls)
        logger.info(f"[EXTRACT] After annex-catalog safety net: {len(controls)} candidates total")

    # Content/structure-based safety nets — none of these depend on
    # character distance in possibly-reordered text, so all are safe to
    # act on (drop/repair), unlike the proximity check above.
    controls = _drop_objective_only_controls(controls)
    controls = _drop_parent_prefix_duplicates(controls)
    controls = _fix_flattened_category_ids(controls)
    controls = _flag_singleton_fabricated_children(controls)
    logger.info(f"[EXTRACT] After structural filters: {len(controls)} controls")

    # Cosmetic ordering fix: sort by natural (hierarchical) ID order so
    # logs and downstream processing read sequentially (A.6.1.1, A.6.1.2,
    # A.6.1.3, ...) instead of whatever order extraction/completeness
    # rounds/batches happened to produce them in. Does not change which
    # controls exist — only their order.
    controls.sort(key=lambda c: _natural_sort_key(str(c.get("Control_id", ""))) if isinstance(c, dict) else [])

    # ------------------------------------------------------------------
    # STAGE 2 — Deployment points. Generated for EVERY control, no
    # skipping based on description length. Guaranteed exactly 5 points
    # per control via _validate_deployment_points(), regardless of what
    # the LLM actually returns.
    # ------------------------------------------------------------------
    logger.info(
        f"[EXTRACT] Stage 2: Generating deployment points in batches of {DEPLOYMENT_BATCH_SIZE} "
        f"(every control gets exactly 5 points — no skipping based on description length)"
    )

    final_controls = []
    total_dp_batches = (len(controls) + DEPLOYMENT_BATCH_SIZE - 1) // DEPLOYMENT_BATCH_SIZE

    for batch_idx in range(0, len(controls), DEPLOYMENT_BATCH_SIZE):
        batch = controls[batch_idx : batch_idx + DEPLOYMENT_BATCH_SIZE]
        batch_num = batch_idx // DEPLOYMENT_BATCH_SIZE + 1

        batch_ids = [str(c.get("Control_id", "")) for c in batch]
        logger.info(
            f"[EXTRACT] DP Batch {batch_num}/{total_dp_batches}: {len(batch)} controls | IDs: {batch_ids}"
        )

        prompt_stage2 = f"""You are an analyser of framework controls.

CRITICAL RULES (no exceptions):
- EVERY control MUST have EXACTLY 5 deployment points. NOT 4, NOT 6, NEVER empty.
- If the control description is vague, short, or minimal, you MUST still generate 5
  sensible, generic deployment points based on the control's NAME and general best
  practice for that type of control. Do NOT return an empty string under any circumstance.

Deployment points must describe:
- How to implement this control based on what the document says (or general best
  practice if the description lacks detail)
- Specific actions/steps required
- How to operationalize it
- Important implementation details

Every point must be numbered: 1. 2. 3. 4. 5.
Store all 5 points as a SINGLE string with newlines between them.

IMPORTANT: Keep Section_name exactly as provided. Do NOT change it.

Input JSON:
{json.dumps(batch)}

Add Deployment_points field to each control (a string with EXACTLY 5 numbered points).
Use JSON list ONLY:
[{{"Control_id": "","Control_name": "","Control_type":"","Control_description": "","Section_name": "","Deployment_points": "1. ...\\n2. ...\\n3. ...\\n4. ...\\n5. ..."}}]

Return ONLY JSON. No markdown."""

        t_start = datetime.now()
        finish_reason = None
        try:
            response = get_openai_client().chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt_stage2}],
                temperature=0,
                max_tokens=DEPLOYMENT_MAX_TOKENS,
                timeout=3600,
            )
            elapsed = (datetime.now() - t_start).total_seconds()
            finish_reason = _log_llm_call(
                f"EXTRACT-STAGE2-batch{batch_num}", response, elapsed
            )

            batch_result = json.loads(response.choices[0].message.content)

            dp_map = {}
            for res_ctrl in batch_result:
                if isinstance(res_ctrl, dict):
                    c_id = str(res_ctrl.get("Control_id", "")).strip()
                    if c_id:
                        dp_map[c_id] = res_ctrl.get("Deployment_points", "")

            merged_batch = []
            for orig_ctrl in batch:
                c_id = str(orig_ctrl.get("Control_id", "")).strip()
                c_name = str(orig_ctrl.get("Control_name", "")).strip()
                raw_dp = dp_map.get(c_id, orig_ctrl.get("Deployment_points", ""))
                # Deterministic safety net — guarantees exactly 5 points
                # regardless of what the LLM actually returned.
                orig_ctrl["Deployment_points"] = _validate_deployment_points(raw_dp, c_name)
                merged_batch.append(orig_ctrl)

            final_controls.extend(merged_batch)
            logger.info(
                f"[EXTRACT] DP Batch {batch_num} OK — added {len(merged_batch)} controls, "
                f"all guaranteed exactly 5 deployment points"
            )

        except json.JSONDecodeError as e:
            logger.exception(f"[EXTRACT] DP Batch {batch_num} JSON parse failed: {e}")
            if finish_reason == "length":
                logger.warning(
                    f"[EXTRACT] DP Batch {batch_num} truncated — consider lowering DEPLOYMENT_BATCH_SIZE"
                )
            # Even on total failure, every control still gets 5 default points.
            for ctrl in batch:
                ctrl["Deployment_points"] = _validate_deployment_points(
                    "", str(ctrl.get("Control_name", ""))
                )
            final_controls.extend(batch)

        except Exception as e:
            logger.exception(f"[EXTRACT] DP Batch {batch_num} API error: {e}")
            for ctrl in batch:
                ctrl["Deployment_points"] = _validate_deployment_points(
                    "", str(ctrl.get("Control_name", ""))
                )
            final_controls.extend(batch)

    # Final cosmetic sort by natural ID order
    final_controls.sort(key=lambda c: _natural_sort_key(str(c.get("Control_id", ""))) if isinstance(c, dict) else [])

    logger.info(
        f"[EXTRACT] Stage 2 complete: {len(final_controls)} controls — every single one has "
        f"exactly 5 deployment points guaranteed"
    )
    logger.info(f"[EXTRACT] Complete: {len(final_controls)} total controls extracted")
    return final_controls


def extract_deployment_controls(
    chunks: list, framework_id: str, is_deployment: bool = True
) -> list:
    """
    Extract deployment controls from deployment documents/frameworks using AI.
    This function is SPECIFICALLY for deployment-framework and deployment-document resource types.
    
    Two-stage extraction:
    1. Extract Control_id, Control_name, Control_description, Section_name
    2. Generate Deployment_points for each control (in batches)
    
    This uses the same extraction logic as extract_framework_controls but specifically
    for deployment-related documents.
    """
    if not chunks:
        logger.warning("[DEPLOYMENT-EXTRACT] No chunks provided")
        return []

    text = " ".join(chunks) if isinstance(chunks, list) else str(chunks)
    REGEX = r"\b(?:[A-Z]+(?:\.[A-Z]+)*[-.]?)?\d+(?:\.\d+)*\b"

    # Stage 1: Extract controls
    logger.info(f"[DEPLOYMENT-EXTRACT] Starting deployment extraction | framework_id={framework_id}")

    # Always use deployment-style prompt for deployment extraction
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

    t_start = datetime.now()
    try:
        logger.info("[OPENAI] Client initialized for deployment extraction")
        response = get_openai_client().chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt_stage1}],
            temperature=0,
            max_tokens=CONTROL_EXTRACTION_MAX_TOKENS,
            timeout=3600,  # 1 hour timeout
        )
        elapsed = (datetime.now() - t_start).total_seconds()
        _log_llm_call("DEPLOYMENT-EXTRACT-STAGE1", response, elapsed)

        controls = json.loads(response.choices[0].message.content)
        logger.info(f"[DEPLOYMENT-EXTRACT] Stage 1 complete: {len(controls)} controls extracted")

    except json.JSONDecodeError as e:
        logger.exception(f"[DEPLOYMENT-EXTRACT] JSON decode failed: {e}")
        return []
    except Exception as e:
        logger.exception(f"[DEPLOYMENT-EXTRACT] OpenAI API error: {e}", exc_info=True)
        return []

    # Stage 2: Generate deployment points (batched)
    logger.info(
        f"[DEPLOYMENT-EXTRACT] Stage 2: Generating deployment points in batches of {DEPLOYMENT_BATCH_SIZE}"
    )

    final_controls = []
    total_batches = (
        (len(controls) + DEPLOYMENT_BATCH_SIZE - 1) // DEPLOYMENT_BATCH_SIZE if controls else 0
    )

    for batch_idx in range(0, len(controls), DEPLOYMENT_BATCH_SIZE):
        batch = controls[batch_idx : batch_idx + DEPLOYMENT_BATCH_SIZE]
        batch_num = batch_idx // DEPLOYMENT_BATCH_SIZE + 1

        logger.info(f"[DEPLOYMENT-EXTRACT] Batch {batch_num}/{total_batches}: {len(batch)} controls")

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
                timeout=3600,  # 1 hour timeout
            )
            elapsed = (datetime.now() - t_start).total_seconds()
            finish_reason = _log_llm_call(f"DEPLOYMENT-EXTRACT-STAGE2-batch{batch_num}", response, elapsed)

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
            logger.info(f"[DEPLOYMENT-EXTRACT] Batch {batch_num}/{total_batches} OK")

        except json.JSONDecodeError as e:
            logger.exception(f"[DEPLOYMENT-EXTRACT] Batch {batch_num} JSON parse failed: {e}")
            if finish_reason == "length":
                logger.warning(
                    f"[DEPLOYMENT-EXTRACT] Batch {batch_num} truncated — consider lowering DEPLOYMENT_BATCH_SIZE"
                )
            # Fallback: keep original controls without deployment points
            final_controls.extend(batch)

        except Exception as e:
            logger.exception(f"[DEPLOYMENT-EXTRACT] Batch {batch_num} API error: {e}")
            final_controls.extend(batch)

    logger.info(f"[DEPLOYMENT-EXTRACT] Complete: {len(final_controls)} controls extracted")
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

        - Letter-prefixed schemes (ISO 27001 Annex A style: A.5.1.1) ->
          section is the first TWO parts (e.g. "A.5").
        - Purely numeric clause schemes (ISO 9001 style: 4.2.1) -> section
          is just the FIRST part (e.g. "4").
        """
        parts = _parse_id(ctrl_id)
        if not parts or not parts[0]:
            return "NOSEC"

        first = parts[0]
        if first == "CTR":
            return "NOSEC"

        if first.isdigit():
            return first
        else:
            if len(parts) >= 2:
                return f"{first}.{parts[1]}".upper()
            return first.upper()

    sections = {}
    control_by_id = {}
    section_for_control = {}

    for idx, ctrl in enumerate(controls):
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

        dp_list = _parse_deployment_points(raw_dp)

        ctrl_obj = {
            "id": ctrl_id,
            "name": ctrl_name.strip().lower() if ctrl_name else ctrl_id,
            "description": ctrl_desc,
            "deployment_points": dp_list,
        }
        control_by_id[ctrl_id] = ctrl_obj
        section_for_control[ctrl_id] = {"name": section_name}

    logger.info(f"[STRUCTURE] Collected {len(control_by_id)} controls")

    # Iterate in natural (hierarchical) ID order so logs and the resulting
    # section['controls'] lists read sequentially — cosmetic only, does
    # not change which section/parent a control ends up under.
    ordered_ids = sorted(control_by_id.keys(), key=_natural_sort_key)

    added_as_root = 0
    added_as_sub = 0

    for ctrl_id in ordered_ids:
        ctrl_obj = control_by_id[ctrl_id]
        parts = _parse_id(ctrl_id)

        if len(parts) >= 4:
            parent_id = ".".join(parts[:-1])
            if parent_id in control_by_id:
                added_as_sub += 1
                logger.info(f"[STRUCTURE] {ctrl_id} → sub-control of {parent_id}")
                continue

        sec_key = _section_key_for_id(ctrl_id)
        sec_display = section_for_control.get(ctrl_id, {}).get("name") or sec_key

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

        ctrl_entry = {
            "id": ctrl_obj["id"],
            "name": ctrl_obj["name"],
            "description": ctrl_obj["description"],
            "deployment_points": ctrl_obj["deployment_points"],
        }

        sub_controls = []
        for other_id in ordered_ids:
            other_parts = _parse_id(other_id)
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