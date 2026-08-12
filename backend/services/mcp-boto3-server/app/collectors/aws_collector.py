# collectors/aws_collector.py

import boto3

def fetch_s3_files(bucket_name, prefix=""):
    s3 = boto3.client('s3')

    response = s3.list_objects_v2(
        Bucket=bucket_name,
        Prefix=prefix
    )

    files = []

    for obj in response.get('Contents', []):
        files.append({
            "source": "aws",
            "file_name": obj['Key'].split("/")[-1],
            "file_path": f"s3://{bucket_name}/{obj['Key']}",
            "type": "file"
        })

    return files


# all le