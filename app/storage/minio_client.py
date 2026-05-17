import io
from typing import BinaryIO
from urllib.parse import urlparse

from minio import Minio
from minio.error import S3Error

from app.config import settings
from app.core.constants import MINIO_BUCKETS, SIGNED_URL_EXPIRE_SECONDS

_client: Minio | None = None


def get_minio_client() -> Minio:
    global _client
    if _client is None:
        _client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_use_ssl,
        )
    return _client


async def init_buckets() -> None:
    """Create all required buckets on startup if they don't exist."""
    import json
    client = get_minio_client()
    for bucket_name, is_public in MINIO_BUCKETS.items():
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
        
        # Always set/update policy for public buckets
        if is_public:
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": ["*"]},
                        "Action": ["s3:GetObject"],
                        "Resource": [f"arn:aws:s3:::{bucket_name}/*"]
                    }
                ]
            }
            client.set_bucket_policy(bucket_name, json.dumps(policy))


def upload_file(
    bucket: str,
    key: str,
    data: BinaryIO,
    size: int,
    content_type: str,
) -> str:
    """Upload a file and return its object key."""
    client = get_minio_client()
    client.put_object(
        bucket_name=bucket,
        object_name=key,
        data=data,
        length=size,
        content_type=content_type,
    )
    return key


def get_signed_url(bucket: str, key: str, expires_in: int = SIGNED_URL_EXPIRE_SECONDS) -> str:
    """Generate a pre-signed GET URL for private documents."""
    from datetime import timedelta
    client = get_minio_client()
    return client.presigned_get_object(
        bucket_name=bucket,
        object_name=key,
        expires=timedelta(seconds=expires_in),
    )


def get_public_url(bucket: str, key: str) -> str:
    """Return a direct public URL for public buckets."""
    scheme = "https" if settings.minio_use_ssl else "http"
    return f"{scheme}://{settings.minio_public_endpoint}/{bucket}/{key}"


def resolve_public_url(bucket: str, value: str | None) -> str | None:
    """Return a public URL for stored object keys while keeping existing URLs intact."""
    if not value:
        return None

    parsed = urlparse(value)
    if parsed.scheme and parsed.netloc:
        return value

    return get_public_url(bucket, value.lstrip("/"))


def delete_file(bucket: str, key: str) -> None:
    client = get_minio_client()
    try:
        client.remove_object(bucket_name=bucket, object_name=key)
    except S3Error:
        pass  # Already deleted — idempotent
