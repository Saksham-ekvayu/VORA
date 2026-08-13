
import asyncio
import logging

from vora_shared.database import session_scope

from db.queries import (
    get_live_framework,
    get_framework_merge,
    is_processed,
    mark_processed,
)

from collectors.collector_manager import collect_files
from services.downloader import download_file
from services.agent_client import call_agent
from utils.live_logs import add_live_log

from pipeline.helpers import extract_deployment_points


def run_pipeline(source: str = "aws"):
    asyncio.run(_run_pipeline(source))


async def _run_pipeline(source: str):
    # ------------------------------------------------
    # STEP 1: CHECK LIVE PACKAGE
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
    # STEP 2: USE CANONICAL MERGED CONTROLS
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

                # Download S3 files locally
                if path.startswith("s3://"):
                    local_path = download_file(path)
                else:
                    local_path = path

                # Prepare payload for Compliance Audit Agent
                payload = {
                    "id": framework["framework_id"],
                    "framework_name": framework["framework_name"],
                    "package_version": framework["package_version"],
                    "merge_document": merge_id,
                    "deployment_framework": deployment_data,
                    "file_path": local_path,
                    "source_path": path,
                }

                response = call_agent(
                    payload,
                    "Compliance_Audit_Agent",
                )

                logging.info(f"Agent Response: {response}")
                add_live_log(f"Agent Response: {response}")

                # Mark as processed
                await mark_processed(db, path)

            except Exception as e:
                logging.exception(
                    f"Error processing {path}: {e}"
                )
                add_live_log(
                    f"Error processing {path}: {e}"
                )

