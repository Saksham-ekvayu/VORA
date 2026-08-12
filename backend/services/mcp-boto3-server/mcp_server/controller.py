import asyncio
import logging
from vora_shared.database import session_scope
from db.queries import (
    get_live_framework,
    get_framework_merge,
    is_processed,
    mark_processed,
)
from pipeline.helpers import extract_source_paths
from collectors.collector_manager import collect_files
from services.downloader import download_file
from services.agent_client import call_agent
from utils.live_logs import add_live_log


def run_pipeline(source: str = "aws"):
    asyncio.run(_run_pipeline(source))


async def _run_pipeline(source: str):
    # STEP 1: Check LIVE framework
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

    logging.info(f"LIVE package found: {framework['package_version']}")
    add_live_log(f"LIVE package found: {framework['package_version']}")

    # STEP 2: Deployment data from framework_merges
    deployment_data = merge_data["controls"]

    # STEP 3: Extract paths for selected source
    source_paths = extract_source_paths(deployment_data, source)

    logging.info(f"Source paths: {source_paths}")
    add_live_log(f"Source paths: {source_paths}")

    if not source_paths:
        logging.info(f"No paths found for source: {source}")
        add_live_log(f"No paths found for source: {source}")
        return

    # STEP 4: Collect files
    files = collect_files(source, {"paths": source_paths})

    logging.info(f"Total files fetched: {len(files)}")
    add_live_log(f"Total files fetched: {len(files)}")

    # STEP 5: Process files
    async with session_scope() as db:
        for f in files:
            path = f["file_path"]

            if await is_processed(db, path):
                continue

            try:
                logging.info(f"Processing: {path}")
                add_live_log(f"Processing: {path}")

                if path.startswith("s3://"):
                    local_path = download_file(path)
                else:
                    local_path = path

                payload = {
                    "id": framework["framework_id"],
                    "framework_name": framework["framework_name"],
                    "package_version": framework["package_version"],
                    "merge_document": merge_id,
                    "deployment_framework": deployment_data,
                    "file_path": local_path,
                }

                response = call_agent(payload, "Compliance_Audit_Agent")

                logging.info(f"Agent Response: {response}")
                add_live_log(f"Agent Response: {response}")

                await mark_processed(db, path)

            except Exception as e:
                logging.error(f"Error processing {path}: {e}")
                add_live_log(f"Error processing {path}: {e}")