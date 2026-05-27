from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # App
    app_env: str = Field("development", alias="APP_ENV")
    app_secret_key: str = Field(..., alias="APP_SECRET_KEY")
    app_host: str = Field("http://localhost:8000", alias="APP_HOST")
    # Public browser-facing frontend URL. Used for CORS and links in emails.
    # In production set FRONTEND_URL=https://nobal.tech
    frontend_url: str = Field("http://localhost:3000", alias="FRONTEND_URL")

    # JWT
    jwt_access_token_expire_minutes: int = Field(60, alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    jwt_refresh_token_expire_days: int = Field(30, alias="JWT_REFRESH_TOKEN_EXPIRE_DAYS")
    jwt_algorithm: str = Field("HS256", alias="JWT_ALGORITHM")

    # Database
    database_url: str = Field(..., alias="DATABASE_URL")

    # Redis
    redis_url: str = Field("redis://redis:6379/0", alias="REDIS_URL")

    # MinIO
    minio_endpoint: str = Field("minio:9000", alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(..., alias="MINIO_ROOT_USER")
    minio_secret_key: str = Field(..., alias="MINIO_ROOT_PASSWORD")
    minio_use_ssl: bool = Field(False, alias="MINIO_USE_SSL")
    # SSL for the PUBLIC endpoint only (browser-facing URLs / presigning).
    # Kept separate from minio_use_ssl so the internal client can stay on
    # plain http to minio:9000 while public URLs use https (files.nobal.tech).
    minio_public_use_ssl: bool = Field(False, alias="MINIO_PUBLIC_USE_SSL")

    # Email
    email_host: str = Field("smtp.college.edu.kz", alias="EMAIL_HOST")
    email_port: int = Field(587, alias="EMAIL_PORT")
    email_use_tls: bool = Field(True, alias="EMAIL_USE_TLS")
    email_host_user: str = Field("", alias="EMAIL_HOST_USER")
    email_host_password: str = Field("", alias="EMAIL_HOST_PASSWORD")
    email_from_name: str = Field("eduadviser", alias="EMAIL_FROM_NAME")
    # Actual "From" address. Needed for relays (SMTP2GO/SendGrid) where the SMTP
    # username is NOT an email. Falls back to email_host_user if unset.
    email_from_address: str = Field("", alias="EMAIL_FROM_ADDRESS")

    # File limits
    max_document_size_mb: int = Field(10, alias="MAX_DOCUMENT_SIZE_MB")
    max_image_size_mb: int = Field(5, alias="MAX_IMAGE_SIZE_MB")

    # MinIO public endpoint (for frontend access)
    minio_public_endpoint: str = Field("localhost:9000", alias="MINIO_PUBLIC_ENDPOINT")

    # Adviser bootstrap account
    adviser_email: str = Field("adviser@college.edu.kz", alias="ADVISER_EMAIL")
    adviser_initial_password: str = Field("change_immediately", alias="ADVISER_INITIAL_PASSWORD")

    model_config = {"env_file": ".env", "populate_by_name": True, "extra": "ignore"}

    @property
    def max_document_size_bytes(self) -> int:
        return self.max_document_size_mb * 1024 * 1024

    @property
    def max_image_size_bytes(self) -> int:
        return self.max_image_size_mb * 1024 * 1024


settings = Settings()
