from __future__ import annotations

import logging
from pathlib import Path

import boto3

logger = logging.getLogger(__name__)


def _get_bucket_region(s3_client: object, bucket: str) -> str:
    """Get the actual region of an S3 bucket."""
    try:
        response = s3_client.get_bucket_location(Bucket=bucket)
        location = response.get("LocationConstraint")
        # AWS returns None for us-east-1
        return location or "us-east-1"
    except Exception:
        return s3_client.meta.region_name or "us-east-1"


def upload_to_s3(mp3_path: Path, bucket: str, key: str | None = None) -> str:
    """Upload MP3 to S3 and return the public URL."""
    s3 = boto3.client("s3")
    s3_key = key or f"veille-techno/{mp3_path.name}"

    s3.upload_file(
        str(mp3_path),
        bucket,
        s3_key,
        ExtraArgs={"ContentType": "audio/mpeg"},
    )

    region = _get_bucket_region(s3, bucket)
    url = f"https://{bucket}.s3.{region}.amazonaws.com/{s3_key}"
    logger.info("Uploaded %s to %s", mp3_path.name, url)
    return url


def cleanup_s3(bucket: str, prefix: str = "veille-techno/", keep_latest: int = 7) -> None:
    """Remove old briefings from S3, keeping the latest N."""
    s3 = boto3.client("s3")
    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
    objects = response.get("Contents", [])

    if len(objects) <= keep_latest:
        return

    sorted_objects = sorted(objects, key=lambda o: o["LastModified"], reverse=True)
    to_delete = sorted_objects[keep_latest:]

    for obj in to_delete:
        s3.delete_object(Bucket=bucket, Key=obj["Key"])
        logger.info("Deleted old S3 object: %s", obj["Key"])
