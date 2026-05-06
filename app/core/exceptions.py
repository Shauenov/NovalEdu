from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    SLOT_ALREADY_BOOKED = "SLOT_ALREADY_BOOKED"
    DOCUMENT_TYPE_EXISTS = "DOCUMENT_TYPE_EXISTS"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    INVALID_FILE_TYPE = "INVALID_FILE_TYPE"
    INVALID_OTP = "INVALID_OTP"
    OTP_EXPIRED = "OTP_EXPIRED"
    APPOINTMENT_CANCEL_DENIED = "APPOINTMENT_CANCEL_DENIED"
    CONFLICT = "CONFLICT"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AppException(Exception):
    def __init__(
        self,
        status_code: int,
        error_code: ErrorCode,
        message: str,
        details: Any = None,
    ) -> None:
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.details = details
        super().__init__(message)


class NotFoundException(AppException):
    def __init__(self, message: str = "Resource not found", details: Any = None) -> None:
        super().__init__(404, ErrorCode.NOT_FOUND, message, details)


class ForbiddenException(AppException):
    def __init__(self, message: str = "Access denied", details: Any = None) -> None:
        super().__init__(403, ErrorCode.FORBIDDEN, message, details)


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Not authenticated", details: Any = None) -> None:
        super().__init__(401, ErrorCode.TOKEN_INVALID, message, details)


class ConflictException(AppException):
    def __init__(
        self,
        error_code: ErrorCode = ErrorCode.CONFLICT,
        message: str = "Conflict",
        details: Any = None,
    ) -> None:
        super().__init__(409, error_code, message, details)


class ValidationException(AppException):
    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(400, ErrorCode.VALIDATION_ERROR, message, details)


class FileTooLargeException(AppException):
    def __init__(self, message: str = "File is too large") -> None:
        super().__init__(413, ErrorCode.FILE_TOO_LARGE, message)


class InvalidFileTypeException(AppException):
    def __init__(self, message: str = "Invalid file type") -> None:
        super().__init__(400, ErrorCode.INVALID_FILE_TYPE, message)
