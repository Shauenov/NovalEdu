import magic

from app.core.constants import ALLOWED_DOC_MIME_TYPES, ALLOWED_IMAGE_MIME_TYPES
from app.core.exceptions import FileTooLargeException, InvalidFileTypeException


def detect_mime_type(file_bytes: bytes) -> str:
    """Detect MIME type from magic bytes (not file extension)."""
    return magic.from_buffer(file_bytes, mime=True)


def validate_document(file_bytes: bytes, max_size: int) -> str:
    """
    Validate a student document upload.
    Returns detected MIME type on success.
    Raises FileTooLargeException or InvalidFileTypeException on failure.
    """
    if len(file_bytes) > max_size:
        raise FileTooLargeException(
            f"Document exceeds maximum size of {max_size // (1024 * 1024)} MB"
        )
    mime = detect_mime_type(file_bytes)
    if mime not in ALLOWED_DOC_MIME_TYPES:
        raise InvalidFileTypeException(
            f"File type '{mime}' is not allowed. "
            f"Allowed types: PDF, DOC, DOCX"
        )
    return mime


def validate_image(file_bytes: bytes, max_size: int) -> str:
    """
    Validate an image upload (avatar, cover, etc.).
    Returns detected MIME type on success.
    """
    if len(file_bytes) > max_size:
        raise FileTooLargeException(
            f"Image exceeds maximum size of {max_size // (1024 * 1024)} MB"
        )
    mime = detect_mime_type(file_bytes)
    if mime not in ALLOWED_IMAGE_MIME_TYPES:
        raise InvalidFileTypeException(
            f"Image type '{mime}' is not allowed. "
            f"Allowed types: JPEG, PNG, WebP"
        )
    return mime
