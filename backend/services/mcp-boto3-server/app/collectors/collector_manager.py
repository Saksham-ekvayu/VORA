from app.collectors.aws_collector import fetch_s3_files
from app.collectors.local_collector import fetch_local_files
from app.collectors.gitlab_collector import fetch_gitlab_files


def collect_files(source, config):
    if source == "aws":
        return fetch_s3_files(
            bucket_name=config.get("bucket"),
            prefix=config.get("prefix", "")
        )

    elif source == "local":
        return fetch_local_files(
            directory=config.get("directory"),
            allowed_extensions=config.get("extensions")
        )

    elif source == "gitlab":
        return fetch_gitlab_files(
            project_id=config.get("project_id"),
            token=config.get("token")
        )

    else:
        raise ValueError(f"Unknown source: {source}")