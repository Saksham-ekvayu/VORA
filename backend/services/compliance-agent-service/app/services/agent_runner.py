"""Postgres-based compliance agent runner supporting LLM & similarity matching."""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import UTC, datetime
from typing import Any

from sentence_transformers import SentenceTransformer, util
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified
from vora_shared.config import get_settings
from vora_shared.database import session_scope
from vora_shared.ids import new_id
from vora_shared.models import (
    DeploymentDocument,
    DeploymentFramework,
    DocumentExtraction,
    EvidenceOutput,
    FrameworkAssignment,
    UploadedFile,
)

logger = logging.getLogger(__name__)


# Lazy-loaded embedding model to avoid startup slowdown
_embed_model = None


def get_embed_model():
    global _embed_model
    if _embed_model is None:
        try:

            settings = get_settings()
            model_name = getattr(settings, "sentence_transformer_model", "all-MiniLM-L6-v2")
            logger.info(f"Loading embedding model: {model_name}")
            _embed_model = SentenceTransformer(model_name)
        except Exception:
            logger.exception("Failed to load sentence-transformers model")
            raise
    return _embed_model


def _extract_pdf_text(file_path: str) -> str:
    import fitz

    doc = fitz.open(file_path)
    try:
        return "".join(page.get_text() or "" for page in doc)
    finally:
        doc.close()


def _extract_docx_text(file_path: str) -> str:
    from docx import Document

    doc = Document(file_path)
    paragraphs = [para.text.strip() for para in doc.paragraphs if para.text.strip()]
    for table in doc.tables:
        for row in table.rows:
            paragraphs.extend(cell.text.strip() for cell in row.cells if cell.text.strip())
    return "\n".join(paragraphs)


def _extract_plain_text(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
        return file.read()


def extract_text_from_file(file_path: str) -> str:
    """Extract all text from PDF, DOCX, or text files."""
    if not file_path or not os.path.exists(file_path):
        logger.error(f"[EXTRACT-TEXT] File path does not exist: {file_path}")
        return ""

    ext = os.path.splitext(file_path)[1].lower()
    logger.info(f"[EXTRACT-TEXT] Extracting text from {file_path} (extension: {ext})")
    extractors = {
        ".pdf": _extract_pdf_text,
        ".docx": _extract_docx_text,
        ".doc": _extract_docx_text,
        ".txt": _extract_plain_text,
        ".log": _extract_plain_text,
        ".csv": _extract_plain_text,
    }
    extractor = extractors.get(ext)
    if not extractor:
        logger.error(f"[EXTRACT-TEXT] Unsupported file extension: {ext}")
        return ""
    try:
        return extractor(file_path).strip()
    except Exception:
        logger.exception(f"[EXTRACT-TEXT] Failed to extract text from {file_path}")
        return ""


async def compute_similarity_async(text: str, dp_text: str) -> float:
    """Compute similarity asynchronously by running encoder in a background thread."""
    try:

        model = get_embed_model()
        emb1 = await asyncio.to_thread(model.encode, text, convert_to_tensor=True)
        emb2 = await asyncio.to_thread(model.encode, dp_text, convert_to_tensor=True)
        score = round(util.cos_sim(emb1, emb2).item() * 100, 2)
        logger.info(f"[SIMILARITY-ASYNC] Computed score: {score}%")
        return score
    except Exception:
        logger.exception("Failed to compute similarity asynchronously")
        return 0.0


def compute_final_score(
    similarity: float,
    relevant: bool,
    sim_high: float,
    sim_medium: float,
    sim_low: float,
    score_high: float,
    score_medium: float,
    score_low: float,
    score_very_low: float,
) -> float:
    """Calculate the overall score based on relevance and similarity dynamically from settings."""
    if not relevant:
        return score_very_low

    if similarity >= sim_high:
        return score_high
    elif similarity >= sim_medium:
        # MIDPOINT: 0.85
        return round((score_high + score_medium) / 2.0, 2)
    elif similarity >= sim_low:
        return score_medium
    else:
        return score_low


def generate_recommendation(
    confidence: str,
    dp_text: str,
    reason: str,
    relevant: bool = True,
) -> str:
    """Generate solid, actionable recommendations based on compliance and confidence level."""
    confidence = (confidence or "low").lower().strip()

    if not relevant:
        return (
            f"REQUIRES ACTION: The deployment point is not satisfied. "
            f"Reason: {reason}. "
            f"Action: Implement the required control: '{dp_text}' and document it to ensure compliance."
        )

    if confidence == "high":
        # HIGH: Clear, actionable steps for immediate implementation
        return (
            f"APPROVED FOR IMPLEMENTATION: This deployment point is well-satisfied. "
            f"Action: Maintain and audit regularly. "
            f"Reason: {reason}."
        )
    elif confidence == "medium":
        # MEDIUM: Require thorough review before proceeding
        return (
            f"CONDITIONAL APPROVAL: This deployment point shows partial alignment. "
            f"Recommend review and validation. "
            f"Reason: {reason}."
        )
    else:
        # LOW: Require expert analysis
        return (
            f"REQUIRES EXPERT REVIEW: This deployment point shows weak alignment. "
            f"Reason: {reason}. "
            f"Action: Escalate to compliance officer for detailed assessment before implementing: {dp_text}"
        )


def _map_iso27001_agent(control_id: str) -> str | None:
    prefix_agents = {
        "A.5": "Organizational Controls Agent",
        "A.6": "People Controls Agent",
        "A.7": "Physical Controls Agent",
    }
    for prefix, agent in prefix_agents.items():
        if control_id.startswith(prefix):
            return agent
    groups = {
        "Access Control Agent": ("A.8.2", "A.8.3", "A.8.4", "A.8.5", "A.8.18"),
        "Logging & Monitoring Agent": ("A.8.9", "A.8.10", "A.8.15", "A.8.16"),
        "Network Security Agent": ("A.8.20", "A.8.21", "A.8.22"),
        "Secure Development Agent": ("A.8.25", "A.8.26", "A.8.27", "A.8.28"),
    }
    if control_id.startswith("A.8"):
        for agent, controls in groups.items():
            if any(control_id.startswith(control) for control in controls):
                return agent
        return "Technical Controls Agent"
    return None


def _map_iso9001_agent(control_id: str) -> str | None:
    prefix_agents = (
        (("5", "A.5"), "Leadership Agent"),
        (("6", "A.6"), "Planning Agent"),
        (("7", "A.7"), "Support & Resources Agent"),
        (("8", "A.8"), "Operational Controls Agent"),
        (("9", "A.9"), "Performance Evaluation Agent"),
    )
    for prefixes, agent in prefix_agents:
        if control_id.startswith(prefixes):
            return agent
    return None


def _map_keyword_agent(control_id: str) -> str:
    keyword_agents = (
        (("access", "auth"), "Access Control Agent"),
        (("log", "monitor"), "Logging & Monitoring Agent"),
        (("change", "patch"), "Change Management Agent"),
        (("incident", "breach"), "Incident Response Agent"),
    )
    control_lower = control_id.lower()
    for keywords, agent in keyword_agents:
        if any(keyword in control_lower for keyword in keywords):
            return agent
    return "General Compliance Agent"


def get_agent_name_for_control(control_id: str, framework_code: str | None) -> str:
    """Dynamically map controls to specific compliance sub-agents."""
    normalized_id = str(control_id).upper().strip()
    framework = str(framework_code or "").lower().strip()
    if "27001" in framework:
        return _map_iso27001_agent(normalized_id) or _map_keyword_agent(normalized_id)
    if "9001" in framework:
        return _map_iso9001_agent(normalized_id) or _map_keyword_agent(normalized_id)
    return _map_keyword_agent(normalized_id)


async def analyze_with_llm_async(
    openai_key: str,
    openai_base: str | None,
    model_name: str | None,
    text: str,
    control_id: str,
    control_name: str,
    control_desc: str,
    dp_text: str,
    agent_name: str,
) -> dict[str, Any]:
    """Call OpenAI or custom local LLM asynchronously to check if the text satisfies the deployment point."""
    target_model = model_name or "gpt-4o-mini"
    base_url_log = openai_base or "https://api.openai.com/v1"

    logger.info("--------------------------------------------------------------------------------")
    logger.info(f"[LLM-ASYNC] [START] Request to Model: '{target_model}' | API Base: '{base_url_log}'")
    logger.info(f"[LLM-ASYNC] [REQUEST] Control: {control_id} ('{control_name}') | Agent: '{agent_name}'")
    logger.info(f"[LLM-ASYNC] [REQUEST] Deployment Point: '{dp_text}'")
    logger.info(
        f"[LLM-ASYNC] [REQUEST] Matched Evidence Length: {len(text)} chars | Snippet: '{text[:150]}...'"
    )
    logger.info("--------------------------------------------------------------------------------")

    try:
        import json
        import re

        from openai import AsyncOpenAI

        # Build client args dynamically to support local models like Qwen 7B
        client_args = {"api_key": openai_key or "dummy-key"}
        if openai_base:
            client_args["base_url"] = openai_base

        client = AsyncOpenAI(**client_args)

        system_prompt = (
            f"You are the {agent_name}, responsible for evaluating compliance. "
            "Evaluate if the deployment point is satisfied by the document evidence and provide an appropriate recommendation. "
            "Return only valid JSON."
        )
        user_prompt = f"""
You are a strict compliance evaluator.

Your job is to decide whether the document satisfies the given control and deployment point.

Return ONLY valid JSON.

Schema:
{{
 "agent_name": "string",
 "relevant": true or false,
 "reason": "string",
 "confidence": "high" | "medium" | "low",
 "recommendation": "string"
}}

Decision Rules:
1. Mark "relevant": true ONLY if the document CLEARLY contains evidence matching the deployment point.
2. If the match is partial, vague, or indirect → relevant = false
3. Do NOT assume or infer missing information
4. Be conservative — false positive is worse than false negative

Confidence Rules:
high → strong, explicit match
medium → partial but reasonable match
low → weak or unclear match

Recommendation Rules:
1. Provide a custom, actionable recommendation in the "recommendation" field.
2. If relevant = true, write: "APPROVED FOR IMPLEMENTATION: [actionable maintenance steps or immediate deployment steps for {dp_text}]."
3. If relevant = false, write: "REQUIRES ACTION: [steps to document or implement the required controls to satisfy the {dp_text} requirement]."

Strict Rules:
Return ONLY JSON
No explanation outside JSON
No markdown
All fields must be present

---

Control Name:
{control_name}

Control Description:
{control_desc}

Deployment Point:
{dp_text}

Document (Snippet):
{text[:3000]}
"""
        requested_max_tokens = 250

        logger.info(f"[LLM-ASYNC] [SENDING] Dispatching request payload to model '{target_model}'...")
        resp = await client.chat.completions.create(
            model=target_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            max_tokens=requested_max_tokens,
            response_format={"type": "json_object"},
        )

        raw_output = resp.choices[0].message.content.strip()
        logger.info(f"[LLM-ASYNC] [RESPONSE] Received raw text output: '{raw_output}'")

        # Pre-process raw output in case Qwen/local model wraps it in markdown backticks
        cleaned = raw_output
        if cleaned.startswith("```"):
            logger.info("[LLM-ASYNC] [PARSING] Stripping markdown wrapper from response...")
            cleaned = re.sub(r"^```(?:json)?\n", "", cleaned)
            cleaned = re.sub(r"\n```$", "", cleaned)
            cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
            logger.info(
                f"[LLM-ASYNC] [SUCCESS] Parsed output: relevant={data.get('relevant')} | agent='{data.get('agent_name')}' | reason='{data.get('reason')}'"
            )
            return data
        except json.JSONDecodeError:
            logger.exception(
                "[LLM-ASYNC] [PARSE-ERROR] Failed to parse JSON from cleaned string. Cleaned string: '%s'",
                cleaned,
            )
            raise

    except Exception as e:
        logger.exception(f"[LLM-ASYNC] [ERROR] LLM analysis failed for control {control_id}")
        return {
            "agent_name": agent_name,
            "relevant": False,
            "reason": f"Fallback: LLM analysis failed ({e!s})",
            "confidence": "low",
        }


async def _resolve_deployment_document(session, dd_id: str):
    dd = await session.get(DeploymentDocument, dd_id)
    if dd:
        return dd
    extraction = await session.get(DocumentExtraction, dd_id)
    if not extraction or not extraction.fileHash:
        return None
    all_dds = (await session.execute(select(DeploymentDocument))).scalars().all()
    for candidate in all_dds:
        if candidate.document and candidate.document.get("fileHash") == extraction.fileHash:
            logger.info(
                f"[COMPLIANCE-TASK] Resolved DocumentExtraction '{dd_id}' to DeploymentDocument "
                f"'{candidate.id}' via fileHash '{extraction.fileHash}'"
            )
            return candidate
    return None


def _active_file_version(fa):
    active = fa.currentFileVersion or "1.0.0"
    versions = [fv if isinstance(fv, dict) else getattr(fv, "__dict__", {}) for fv in fa.fileVersions]
    return next(
        (fv for fv in versions if fv.get("fileVersion") == active), versions[-1] if versions else None
    )


def _file_path(document: dict[str, Any]) -> str | None:
    file_url = document.get("fileUrl")
    if not file_url:
        return document.get("file_path")
    if not file_url.startswith("/uploads/"):
        return file_url
    from pathlib import Path

    from vora_shared.file_storage import UPLOAD_BASE_PATH

    return str((Path(UPLOAD_BASE_PATH) / file_url.replace("/uploads/", "", 1)).resolve())


def _flatten_extracted_dps(doc_ext) -> list[dict[str, Any]]:
    if not doc_ext or not doc_ext.aiExtraction:
        return []
    controls = (doc_ext.aiExtraction or {}).get("controls", {}).get("controls_data") or []
    return [
        {
            "id": dp.get("id"),
            "name": dp.get("name"),
            "control_id": ctrl.get("id"),
            "control_name": ctrl.get("name"),
        }
        for section in controls
        for ctrl in section.get("controls", [])
        for dp in ctrl.get("deployment_points", [])
    ]


async def _load_evidence_context(session, dd):
    file_hash = dd.document.get("fileHash")
    if not file_hash:
        logger.error("[COMPLIANCE-TASK] No fileHash in DeploymentDocument document field.")
        return None
    doc_ext = (
        await session.execute(select(DocumentExtraction).where(DocumentExtraction.fileHash == file_hash))
    ).scalar_one_or_none()
    extracted = _flatten_extracted_dps(doc_ext)
    if extracted:
        logger.info(
            f"[COMPLIANCE-TASK] Loaded structured extraction from DB for fileHash={file_hash} "
            f"| total_extracted_dps={len(extracted)}"
        )
    else:
        logger.warning(
            f"[COMPLIANCE-TASK] No structured DocumentExtraction found for fileHash={file_hash}. "
            "Falling back to raw file text."
        )
    embeddings = None
    if extracted:
        try:
            model = get_embed_model()
            texts = [item.get("name", "") for item in extracted]
            if texts:
                embeddings = model.encode(texts, convert_to_tensor=True)
                logger.info(
                    f"[COMPLIANCE-TASK] Pre-encoded {len(texts)} extracted deployment points for fast semantic matching."
                )
        except Exception:
            logger.exception("Failed to pre-encode extracted texts")
    path = _file_path(dd.document)
    raw_text = extract_text_from_file(path) if not extracted and path else ""
    if not extracted and path and not raw_text:
        logger.error("[COMPLIANCE-TASK] Extraction missing and raw file text extraction failed.")
        return None
    return file_hash, extracted, embeddings, path, raw_text


def _evaluation_settings() -> dict[str, Any]:
    settings = get_settings()
    base = getattr(settings, "compliance_api_base", None) or os.environ.get("COMPLIANCE_API_BASE")
    model = getattr(settings, "compliance_model_name", "qwen7b") or os.environ.get("COMPLIANCE_MODEL_NAME")
    return {
        "openai_key": None,
        "openai_base": base or None,
        "model_name": model,
        "score_threshold": getattr(settings, "compliance_score_threshold", 0.7),
        "sim_high": getattr(settings, "compliance_sim_high", 80.0),
        "sim_medium": getattr(settings, "compliance_sim_medium", 60.0),
        "sim_low": getattr(settings, "compliance_sim_low", 40.0),
        "score_high": getattr(settings, "compliance_score_high", 0.95),
        "score_medium": getattr(settings, "compliance_score_medium", 0.75),
        "score_low": getattr(settings, "compliance_score_low", 0.60),
        "score_very_low": getattr(settings, "compliance_score_very_low", 0.30),
    }


async def _find_evidence(dp_id, dp_text, control_id, extracted, embeddings, raw_text):
    evidence, score = None, 0.0
    for item in extracted:
        if item.get("control_id") == control_id and item.get("id") == dp_id:
            evidence = item.get("name")
            score = await compute_similarity_async(evidence, dp_text)
            logger.info(
                f"[COMPLIANCE-TASK] [MATCH-EXACT] Found exact ID & Control match for {dp_id} (Similarity: {score}%)"
            )
            break
    if not evidence and embeddings is not None:
        try:
            model = get_embed_model()
            target = await asyncio.to_thread(model.encode, dp_text, convert_to_tensor=True)
            scores = util.cos_sim(target, embeddings)[0]
            index = scores.argmax().item()
            best_score = round(scores[index].item() * 100, 2)
            best = extracted[index]
            if best and best_score >= 50.0:
                evidence, score = best.get("name"), best_score
                logger.info(
                    f"[COMPLIANCE-TASK] [MATCH-SEMANTIC] Matched target '{dp_id}' (control '{control_id}') "
                    f"with extracted DP '{best.get('id')}' (control '{best.get('control_id')}') (similarity: {score}%)"
                )
                logger.info(f"[COMPLIANCE-TASK] [MATCH-SEMANTIC] Matched snippet: '{evidence[:150]}...'")
        except Exception:
            logger.exception(
                "[COMPLIANCE-TASK] [MATCH-ERROR] Failed semantic search using pre-encoded embeddings"
            )
    if evidence or not raw_text:
        return evidence or "", score
    logger.info(
        f"[COMPLIANCE-TASK] [FALLBACK-RAW] No extracted match found for {dp_id}. Performing fallback match on raw document text."
    )
    return raw_text, await compute_similarity_async(raw_text, dp_text)


async def _evaluate_dp(dp, control, agent_name, context, config, dd, file_path):
    dp_id, dp_text = dp.get("id"), dp.get("name")
    if not dp_id or not dp_text:
        return None
    control_id = control.get("id")
    logger.info(f"[COMPLIANCE-TASK] [DP-CHECK] Target Requirement: {dp_id} | '{dp_text}'")
    _, extracted, embeddings, _, raw_text = context
    evidence, similarity = await _find_evidence(dp_id, dp_text, control_id, extracted, embeddings, raw_text)
    if not evidence:
        relevant, reason, confidence = (
            False,
            "This deployment point was not found/extracted in the uploaded deployment document.",
            "high",
        )
        recommendation = f"REQUIRES ACTION: The deployment point is not satisfied because no matching evidence was found in the document. Action: Document and implement: {dp_text}"
        logger.info(f"[COMPLIANCE-TASK] [DECISION] Target: {dp_id} -> NOT COMPLIANT (No Evidence)")
    else:
        logger.info(f"[COMPLIANCE-TASK] [LLM-CALL] Invoking Qwen LLM for control {control_id} | DP: {dp_id}")
        result = await analyze_with_llm_async(
            config["openai_key"],
            config["openai_base"],
            config["model_name"],
            evidence,
            control_id,
            control.get("name"),
            control.get("description", ""),
            dp_text,
            agent_name,
        )
        relevant = result.get("relevant", False)
        reason, confidence = result.get("reason", "No reason provided"), result.get("confidence", "low")
        recommendation = result.get("recommendation") or generate_recommendation(
            confidence, dp_text, reason, relevant
        )
    status = "Compliant" if similarity >= config["sim_medium"] else "Non-Compliant"
    logger.info(
        f"[COMPLIANCE-TASK] [DP-STATUS] Target: {dp_id} | Similarity: {similarity}% | LLM Relevant: {relevant} | Status: {status} | Reason: {reason}"
    )
    return {
        "dp_id": dp_id,
        "deployment_point": dp_text,
        "file": dd.document.get("originalFileName") or os.path.basename(file_path or "document"),
        "file_id": dd.document.get("fileId") or "N/A",
        "match_percentage": f"{similarity}%",
        "similarity_score": similarity,
        "compliance_status": status,
        "llm_analysis": {
            "agent_name": agent_name,
            "relevant": relevant,
            "reason": reason,
            "confidence": confidence,
            "recommendation": recommendation,
        },
        "agent_name": agent_name,
        "timestamp": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }


async def _save_control(session, control, records, dd, fa, file_hash, file_path):
    control_id = control.get("id")
    filename = dd.document.get("originalFileName") or os.path.basename(file_path or "document")
    output = {
        "document_uuid": dd.id,
        "filename": filename,
        "frameworkCode": fa.frameworkCode,
        "frameworkName": fa.frameworkName,
        "frameworkVersion": fa.frameworkVersion,
        "fileVersions": [
            {
                "fileVersion": fa.frameworkVersion or "1.0.0",
                "status": "processed",
                "processed_at": datetime.now(UTC).isoformat(),
                "data": {
                    str(control_id): {
                        "control_id": control_id,
                        "records": records,
                        "document_source": filename,
                        "file_hash": file_hash,
                    }
                },
            }
        ],
    }
    key = f"{control_id}#{dd.id}"
    existing = (
        await session.execute(select(EvidenceOutput).where(EvidenceOutput.control_id == key).limit(1))
    ).scalar_one_or_none()
    if existing:
        existing.output = output
        flag_modified(existing, "output")
    else:
        session.add(EvidenceOutput(id=new_id(), control_id=key, output=output))
    await session.commit()
    logger.info(
        f"[COMPLIANCE-TASK] [DATABASE-SAVE] Saved compliance output successfully for Control: {control_id} ({len(records)} records)"
    )


async def _process_control(control, sem, context, config, dd, fa):
    async with sem, session_scope() as session:
        control_id, dps = control.get("id"), control.get("deployment_points") or []
        logger.info(
            f"[COMPLIANCE-TASK] [CONTROL-START] Evaluating Control: {control_id} - '{control.get('name')}' | Total Target DPs: {len(dps)}"
        )
        if not control_id or not dps:
            logger.warning(
                f"[COMPLIANCE-TASK] [CONTROL-SKIP] Skipping {control_id} - No deployment points configured."
            )
            return
        agent = get_agent_name_for_control(control_id, fa.frameworkCode)
        logger.info(f"[COMPLIANCE-TASK] [CONTROL-AGENT] Mapped to Agent: '{agent}'")
        results = await asyncio.gather(
            *(_evaluate_dp(dp, control, agent, context, config, dd, context[3]) for dp in dps)
        )
        await _save_control(
            session, control, [item for item in results if item], dd, fa, context[0], context[3]
        )


async def _mark_uploaded_file(file_id: str | None) -> None:
    if not file_id:
        return
    async with session_scope() as session:
        uploaded = await session.get(UploadedFile, str(file_id))
        if not uploaded:
            return
        meta = dict(uploaded.meta or {})
        meta.update({"status": "processed", "processed_at": datetime.now(UTC).isoformat()})
        uploaded.meta = meta
        flag_modified(uploaded, "meta")
        session.add(uploaded)
        await session.commit()
        logger.info(f"[COMPLIANCE-TASK] Marked UploadedFile '{file_id}' as processed in database.")


async def _run_compliance_evaluation(dd_id: str) -> None:
    """Evaluate compliance of a deployment document against finalized assignment controls."""
    logger.info(f"[COMPLIANCE-TASK] Started compliance check for DeploymentDocument: {dd_id}")
    try:
        async with session_scope() as session:
            dd = await _resolve_deployment_document(session, dd_id)
            if not dd:
                logger.error(
                    f"[COMPLIANCE-TASK] Deployment Document (or matching extraction file) not found for: {dd_id}"
                )
                return
            df = await session.get(DeploymentFramework, dd.deploymentFrameworkId)
            if not df:
                logger.error(f"[COMPLIANCE-TASK] Deployment Framework not found: {dd.deploymentFrameworkId}")
                return
            fa = await session.get(FrameworkAssignment, df.assignedFrameworkId)
            file_version = _active_file_version(fa) if fa else None
            if not fa:
                logger.error(f"[COMPLIANCE-TASK] Framework Assignment not found: {df.assignedFrameworkId}")
                return
            if not file_version or not file_version.get("aiExtraction"):
                logger.error(
                    f"[COMPLIANCE-TASK] No finalized controls/aiExtraction found in FrameworkAssignment {fa.id}"
                )
                return
            context = await _load_evidence_context(session, dd)
            if not context:
                return
            config = _evaluation_settings()
            sections = file_version.get("aiExtraction") or []
            sem = asyncio.Semaphore(10)
            controls = [control for section in sections for control in section.get("controls") or []]
            logger.info(f"[COMPLIANCE-TASK] Spawning parallel evaluation tasks for {len(controls)} controls.")
            await asyncio.gather(
                *(_process_control(control, sem, context, config, dd, fa) for control in controls)
            )
            await _mark_uploaded_file(dd.document.get("fileId"))
            logger.info(f"[COMPLIANCE-TASK] Compliance evaluation completed successfully for dd_id: {dd_id}")
    except Exception:
        logger.exception(f"[COMPLIANCE-TASK] Compliance check failed for dd_id {dd_id}")


async def evaluate_compliance_task(dd_id: str) -> None:
    """Evaluate a deployment document in the background."""
    await _run_compliance_evaluation(dd_id)
