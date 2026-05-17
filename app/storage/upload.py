import io
import mimetypes
import uuid

from fastapi import UploadFile

from app.config import settings
from app.storage.file_validator import validate_image
from app.storage.minio_client import get_public_url, upload_file


async def process_and_upload_image(file: UploadFile, bucket: str, prefix: str) -> str:
    """
    Reads an uploaded file, validates it as an image, uploads to MinIO,
    and returns the public URL.
    """
    file_bytes = await file.read()
    mime_type = validate_image(file_bytes, settings.max_image_size_bytes)

    # Guess extension from mime type
    ext = mimetypes.guess_extension(mime_type) or ""
    # Some mimetypes.guess_extension return .jpe instead of .jpg
    if ext == ".jpe":
        ext = ".jpg"

    key = f"{prefix}/{uuid.uuid4().hex}{ext}"

    # upload_file is sync, so we can wrap it or just call it since it's fast enough
    # (or could use run_in_threadpool, but standard here seems to be direct call)
    upload_file(
        bucket=bucket,
        key=key,
        data=io.BytesIO(file_bytes),
        size=len(file_bytes),
        content_type=mime_type,
    )

    return get_public_url(bucket, key)
