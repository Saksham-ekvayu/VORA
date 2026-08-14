
import asyncio
import logging
import os

from vora_shared.database import session_scope

from app.db.queries import (
    get_live_framework,
    get_framework_merge,
    is_processed,
    mark_processed,
    save_deployment_document,
)

from app.collectors.collector_manager import collect_files
from app.services.downloader import download_file
from app.services.agent_client import call_agent
from app.services.ai_extractor import trigger_ai_extraction
from app.utils.live_logs import add_live_log
from app.pipeline.helpers import (
    extract_deployment_points,
    save_file_to_uploads,
)


def run_pipeline(source: str = "local"):
    asyncio.run(_run_pipeline(source))


async def _run_pipeline(source: str):
    # ------------------------------------------------
    # STEP 1: GET LIVE FRAMEWORK
    # ------------------------------------------------
    async with session_scope() as db:
        framework = await get_live_framework(db)

        if not framework:
            logging.info("No LIVE deployment framework found")
            add_live_log("No LIVE deployment framework found")
            return

        merge_id = framework.get("merge_document")

        if not merge_id:
            logging.info("LIVE package has no merge document")
            add_live_log("LIVE package has no merge document")
            return

        merge_data = await get_framework_merge(db, merge_id)

        if not merge_data:
            logging.info(f"Merge document not found: {merge_id}")
            add_live_log(f"Merge document not found: {merge_id}")
            return

    logging.info(
        f"LIVE package found: {framework['package_version']}"
    )
    add_live_log(
        f"LIVE package found: {framework['package_version']}"
    )

    # ------------------------------------------------
    # STEP 2: EXTRACT DEPLOYMENT POINTS
    # ------------------------------------------------
    deployment_data = merge_data["controls"]

    deployment_points = extract_deployment_points(deployment_data)

    logging.info(
        f"Deployment points found: {len(deployment_points)}"
    )
    add_live_log(
        f"Deployment points found: {len(deployment_points)}"
    )

    if not deployment_points:
        logging.info(
            "No deployment points with path and source found"
        )
        add_live_log(
            "No deployment points with path and source found"
        )
        return

    # ------------------------------------------------
    # STEP 3: FILTER PATHS FOR CURRENT SOURCE
    # ------------------------------------------------
    source_paths = [
        dp["path"]
        for dp in deployment_points
        if dp["source"].lower() == source.lower()
    ]
    print("checkking the file is working or not")
    logging.info(f"Source paths: {source_paths}")
    add_live_log(f"Source paths: {source_paths}")

    if not source_paths:
        logging.info(f"No paths found for source: {source}")
        add_live_log(f"No paths found for source: {source}")
        return

    # ------------------------------------------------
    # STEP 4: COLLECT FILES
    # ------------------------------------------------
    files = collect_files(
        source,
        {"paths": source_paths},
    )

    logging.info(f"Total files fetched: {len(files)}")
    add_live_log(f"Total files fetched: {len(files)}")

    if not files:
        logging.info("No files collected")
        add_live_log("No files collected")
        return

    # ------------------------------------------------
    # STEP 5: PROCESS FILES
    # ------------------------------------------------
    async with session_scope() as db:
        for f in files:
            path = f.get("file_path")

            if not path:
                logging.warning(
                    f"Skipping invalid file entry: {f}"
                )
                continue

            # Skip already processed files
            if await is_processed(db, path):
                logging.info(f"Already processed: {path}")
                continue

            try:
                logging.info(f"Processing: {path}")
                add_live_log(f"Processing: {path}")

                # ------------------------------------------------
                # DOWNLOAD IF S3
                # ------------------------------------------------
                if path.startswith("s3://"):
                    local_path = download_file(path)
                else:
                    local_path = path

                # ------------------------------------------------
                # SAVE FILE INTO uploads/deployment_document
                # ------------------------------------------------
                saved_path = save_file_to_uploads(local_path)

                logging.info(f"Saved file: {saved_path}")
                add_live_log(f"Saved file: {saved_path}")
            
                # ------------------------------------------------
                # SAVE INTO deployment_documents TABLE
                # ------------------------------------------------
                deployment_document = await save_deployment_document(
                    db=db,
                    framework=framework,
                    file_path=saved_path,
                    uploaded_by="system",
                )

                document_id = deployment_document.id

                logging.info(
                    f"Deployment document id: {document_id}"
                )
                add_live_log(
                    f"Deployment document id: {document_id}"
                )

                # ------------------------------------------------
                # TRIGGER AI EXTRACTION
                # ------------------------------------------------
                print("checking")
                ai_response = trigger_ai_extraction(document_id)

                logging.info(
                    f"AI Extraction Response: {ai_response}"
                )
                add_live_log(
                    f"AI Extraction Response: {ai_response}"
                )

                # ------------------------------------------------
                # OPTIONAL: CALL COMPLIANCE AUDIT AGENT
                # ------------------------------------------------
                payload = {
                    "id": framework["framework_id"],
                    "framework_name": framework["framework_name"],
                    "package_version": framework["package_version"],
                    "merge_document": merge_id,
                    "deployment_framework": deployment_data,
                    "file_path": saved_path,
                    "source_path": path,
                    "deployment_document_id": document_id,
                }

                response = call_agent(
                    payload,
                    "Compliance_Audit_Agent",
                )

                logging.info(f"Agent Response: {response}")
                add_live_log(f"Agent Response: {response}")

                # ------------------------------------------------
                # MARK AS PROCESSED
                # ------------------------------------------------
                await mark_processed(db, path)

            except Exception as e:
                logging.exception(
                    f"Error processing {path}: {e}"
                )
                add_live_log(
                    f"Error processing {path}: {e}"
                )
