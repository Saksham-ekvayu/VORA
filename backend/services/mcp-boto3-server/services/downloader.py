import boto3
import os

aws_folder = "aws_files"

os.makedirs(aws_folder, exist_ok=True)

s3 = boto3.client("s3")


def download_file(s3_path):

    if s3_path.startswith("s3://"):

        parts = s3_path.replace("s3://", "").split("/", 1)

        bucket = parts[0]
        key = parts[1]

        filename = os.path.basename(key)

        local_path = os.path.join(
            aws_folder,
            filename
        )

        s3.download_file(
            bucket,
            key,
            local_path
        )

        return local_path

    return s3_path