import logging

from app.collectors.collector_manager import collect_files
from app.db.queries import (
    get_framework_merge,
    get_live_frameworks,
    is_processed,
    mark_processed,
    save_deployment_document,
    update_document_ai_extraction,
)
from app.pipeline.helpers import count_deployment_points, group_paths_by_source
from app.services.agent_client import call_agent
from app.services.ai_extractor import trigger_ai_extraction
from app.services.downloader import download_file
from app.utils.live_logs import add_live_log
from vora_shared.database import session_scope

logger = logging.getLogger(__name__)


async def run_pipeline():
    await _run_pipeline()


async def _run_pipeline():
    # STEP 1: Check EVERY LIVE framework (not just the first one found). For each
    # one, log how many of its deployment points have path+source configured vs
    # not, and — if it has at least one configured point — keep it as a candidate
    # to process. Every LIVE framework with usable data gets processed, not just
    # the first match.
    async with session_scope() as db:
        live_frameworks = await get_live_frameworks(db)

        if not live_frameworks:
            logger.info("No LIVE deployment framework found")
            add_live_log("No LIVE deployment framework found")
            return

        usable_candidates = []

        for candidate in live_frameworks:
            candidate_merge_id = candidate.get("merge_document")

            if not candidate_merge_id:
                logger.info(f"LIVE package for '{candidate['framework_name']}' has no merge document")
                add_live_log(f"LIVE package for '{candidate['framework_name']}' has no merge document")
                continue

            candidate_merge_data = await get_framework_merge(db, candidate_merge_id)

            if not candidate_merge_data:
                logger.info(f"Merge document not found: {candidate_merge_id}")
                add_live_log(f"Merge document not found: {candidate_merge_id}")
                continue

            candidate_paths_by_source = group_paths_by_source(candidate_merge_data["controls"])
            candidate_total_points = count_deployment_points(candidate_merge_data["controls"])
            candidate_configured = sum(len(paths) for paths in candidate_paths_by_source.values())
            candidate_not_configured = candidate_total_points - candidate_configured

            logger.info(
                f"LIVE framework '{candidate['framework_name']}' v{candidate['package_version']}: "
                f"{candidate_configured}/{candidate_total_points} deployment points have path+source "
                f"configured ({candidate_not_configured} NOT configured)"
            )
            add_live_log(
                f"LIVE framework '{candidate['framework_name']}' v{candidate['package_version']}: "
                f"{candidate_configured}/{candidate_total_points} deployment points have path+source "
                f"configured ({candidate_not_configured} NOT configured)"
            )

            if candidate_paths_by_source:
                usable_candidates.append(
                    {
                        "framework": candidate,
                        "merge_id": candidate_merge_id,
                        "merge_data": candidate_merge_data,
                        "paths_by_source": candidate_paths_by_source,
                    }
                )
                logger.info(
                    f"LIVE framework '{candidate['framework_name']}' has usable deployment points, "
                    "including it in this run"
                )
                add_live_log(
                    f"LIVE framework '{candidate['framework_name']}' has usable deployment points, "
                    "including it in this run"
                )
            else:
                logger.info(
                    f"LIVE framework '{candidate['framework_name']}' has no deployment points with "
                    "path+source configured, checking other LIVE frameworks"
                )
                add_live_log(
                    f"LIVE framework '{candidate['framework_name']}' has no deployment points with "
                    "path+source configured, checking other LIVE frameworks"
                )

        if not usable_candidates:
            logger.info("No LIVE deployment framework has any deployment points with path+source")
            add_live_log("No LIVE deployment framework has any deployment points with path+source")
            return

    logger.info(
        f"{len(usable_candidates)}/{len(live_frameworks)} LIVE framework(s) have usable deployment "
        "points, processing each one"
    )
    add_live_log(
        f"{len(usable_candidates)}/{len(live_frameworks)} LIVE framework(s) have usable deployment "
        "points, processing each one"
    )

    # STEP 2: Process every usable LIVE framework in turn, each with its own
    # framework/merge context so files are saved under the correct tenant,
    # framework code/version, etc.
    for candidate in usable_candidates:
        await _process_framework_candidate(candidate)


async def _process_framework_candidate(candidate: dict):
    framework = candidate["framework"]
    merge_id = candidate["merge_id"]
    merge_data = candidate["merge_data"]
    paths_by_source = candidate["paths_by_source"]
    deployment_data = merge_data["controls"]

    logger.info(f"Processing LIVE framework '{framework['framework_name']}' v{framework['package_version']}")
    add_live_log(f"Processing LIVE framework '{framework['framework_name']}' v{framework['package_version']}")

    # Collect files per source for this framework
    files = []

    for source, source_paths in paths_by_source.items():
        try:
            source_files = collect_files(source, {"paths": source_paths})
        except Exception as e:
            logger.exception(f"Failed to collect files for source: {source}")
            add_live_log(f"Failed to collect files for source: {source}: {e}")
            continue

        logger.info(f"Fetched {len(source_files)} files for source: {source}")
        add_live_log(f"Fetched {len(source_files)} files for source: {source}")

        files.extend(source_files)

    logger.info(f"Total files fetched for '{framework['framework_name']}': {len(files)}")
    add_live_log(f"Total files fetched for '{framework['framework_name']}': {len(files)}")

    # Process files for this framework
    async with session_scope() as db:
        for f in files:
            path = f["file_path"]

            if await is_processed(db, path):
                continue

            try:
                logger.info(f"Processing: {path}")
                add_live_log(f"Processing: {path}")

                if path.startswith("s3://"):
                    local_path = download_file(path)
                else:
                    local_path = path

                # use the saved_path from collectors when available
                saved_path = f.get("saved_path") or local_path

                # persist into deployment_documents table
                try:
                    deployment_document = await save_deployment_document(
                        db=db,
                        framework=framework,
                        file_path=saved_path,
                        uploaded_by="system-pipeline",
                    )

                    document_id = deployment_document.id

                    logger.info(f"Deployment document id: {document_id}")
                    add_live_log(f"Deployment document id: {document_id}")

                    # trigger AI extraction (sync call)
                    ai_response = trigger_ai_extraction(document_id)

                    logger.info(f"AI Extraction Response: {ai_response}")
                    add_live_log(f"AI Extraction Response: {ai_response}")

                    extraction_id = (ai_response or {}).get("data", {}).get("extraction_id")

                    if extraction_id:
                        await update_document_ai_extraction(db, document_id, extraction_id)
                        logger.info(f"Stored AI extraction id on document: {extraction_id}")
                        add_live_log(f"Stored AI extraction id on document: {extraction_id}")

                except Exception as e:
                    logger.exception("Failed to save deployment document")
                    add_live_log(f"Failed to save deployment document: {e}")
                    # continue processing but mark as error
                    await mark_processed(db, path)
                    continue

                payload = {
                    "id": framework["framework_id"],
                    "framework_name": framework["framework_name"],
                    "package_version": framework["package_version"],
                    "merge_document": merge_id,
                    "deployment_framework": deployment_data,
                    "file_path": saved_path,
                    "deployment_document_id": document_id,
                }

                try:
                    response = call_agent(payload, "Compliance_Audit_Agent")
                    logger.info(f"Agent Response: {response}")
                    add_live_log(f"Agent Response: {response}")
                except Exception as e:
                    logger.exception(f"Compliance agent call failed for {path}")
                    add_live_log(f"Compliance agent call failed for {path}: {e}")

                # Mark processed regardless of the agent-call outcome above, so this
                # file (and its AI extraction) is never re-triggered on future runs.
                await mark_processed(db, path)

            except Exception as e:  # noqa: BLE001
                logger.error(f"Error processing {path}: {e}")
                add_live_log(f"Error processing {path}: {e}")
