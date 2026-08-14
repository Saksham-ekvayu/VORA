from app.collectors.aws_collector import fetch_s3_files
from app.collectors.gitlab_collector import fetch_gitlab_files
from app.collectors.local_collector import fetch_local_files


def collect_files(source, config):
    if source == "aws":
        return fetch_s3_files(bucket_name=config.get("bucket"), prefix=config.get("prefix", ""))

    elif source == "local":
        paths = config.get("paths", [])
        if not paths and config.get("directory"):
            paths = [config.get("directory")]

        all_files = []
        for path in set(paths):
            all_files.extend(fetch_local_files(directory=path, allowed_extensions=config.get("extensions")))
        return all_files

    elif source == "gitlab":
        return fetch_gitlab_files(project_id=config.get("project_id"), token=config.get("token"))

    else:
        raise ValueError(f"Unknown source: {source}")
