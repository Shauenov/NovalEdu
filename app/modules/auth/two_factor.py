"""Two-factor authentication (TOTP).

Self-contained: model + schemas + service + router for
GET/POST /auth/2fa/{status,setup,verify,disable}.
Login integration lives in AuthService.login (uses TwoFactorService.verify_login_code).
"""
import uuid
from datetime import datetime

import pyotp
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, DateTime, ForeignKey, String, func, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.exceptions import AppException, ErrorCode
from app.core.permissions import CurrentUser, get_current_user
from app.core.security import verify_password
from app.database import Base, get_db

TOTP_ISSUER = "Nobal Education"


# ── Model ──────────────────────────────────────────────────────────────────────

class UserTwoFactor(Base):
    __tablename__ = "user_2fa"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    secret: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ── Schemas ─────────────────────────────────────────────────────────────────────

class TwoFactorSetupOut(BaseModel):
    secret: str
    otpauth_uri: str


class TwoFactorStatusOut(BaseModel):
    is_enabled: bool


class TwoFactorVerifyRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=10)


class TwoFactorDisableRequest(BaseModel):
    password: str


class TwoFactorSetupResponse(BaseModel):
    success: bool = True
    data: TwoFactorSetupOut


class TwoFactorStatusResponse(BaseModel):
    success: bool = True
    data: TwoFactorStatusOut


# ── Service ─────────────────────────────────────────────────────────────────────

class TwoFactorService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _get(self, user_id: uuid.UUID) -> UserTwoFactor | None:
        result = await self.db.execute(
            select(UserTwoFactor).where(UserTwoFactor.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def status(self, user_id: uuid.UUID) -> bool:
        rec = await self._get(user_id)
        return bool(rec and rec.is_enabled)

    async def setup(self, user_id: uuid.UUID, email: str) -> TwoFactorSetupOut:
        """Generate (or regenerate) a secret. Stays disabled until verified."""
        secret = pyotp.random_base32()
        rec = await self._get(user_id)
        if rec is None:
            rec = UserTwoFactor(user_id=user_id, secret=secret, is_enabled=False)
            self.db.add(rec)
        else:
            rec.secret = secret
            rec.is_enabled = False
        await self.db.commit()
        uri = pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=TOTP_ISSUER)
        return TwoFactorSetupOut(secret=secret, otpauth_uri=uri)

    async def verify_and_enable(self, user_id: uuid.UUID, code: str) -> None:
        rec = await self._get(user_id)
        if not rec or not rec.secret:
            raise AppException(400, ErrorCode.VALIDATION_ERROR, "Run 2FA setup first")
        if not pyotp.TOTP(rec.secret).verify(code, valid_window=1):
            raise AppException(400, ErrorCode.INVALID_2FA_CODE, "Invalid 2FA code")
        rec.is_enabled = True
        await self.db.commit()

    async def disable(self, user_id: uuid.UUID, password: str, password_hash: str) -> None:
        if not verify_password(password, password_hash):
            raise AppException(400, ErrorCode.INVALID_CREDENTIALS, "Password is incorrect")
        rec = await self._get(user_id)
        if rec:
            rec.is_enabled = False
            rec.secret = None
            await self.db.commit()

    async def verify_login_code(self, user_id: uuid.UUID, code: str | None) -> None:
        """Used by login. Raises if 2FA is enabled and the code is missing/invalid."""
        rec = await self._get(user_id)
        if not rec or not rec.is_enabled:
            return
        if not code:
            raise AppException(401, ErrorCode.TWO_FACTOR_REQUIRED, "Two-factor code required")
        if not rec.secret or not pyotp.TOTP(rec.secret).verify(code, valid_window=1):
            raise AppException(401, ErrorCode.INVALID_2FA_CODE, "Invalid two-factor code")


# ── Router ──────────────────────────────────────────────────────────────────────

router = APIRouter()


@router.get("/2fa/status", response_model=TwoFactorStatusResponse)
async def two_factor_status(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> TwoFactorStatusResponse:
    enabled = await TwoFactorService(db).status(uuid.UUID(current_user.user_id))
    return TwoFactorStatusResponse(data=TwoFactorStatusOut(is_enabled=enabled))


@router.post("/2fa/setup", response_model=TwoFactorSetupResponse)
async def two_factor_setup(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> TwoFactorSetupResponse:
    data = await TwoFactorService(db).setup(uuid.UUID(current_user.user_id), current_user.email)
    return TwoFactorSetupResponse(data=data)


@router.post("/2fa/verify", response_model=TwoFactorStatusResponse)
async def two_factor_verify(
    body: TwoFactorVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> TwoFactorStatusResponse:
    await TwoFactorService(db).verify_and_enable(uuid.UUID(current_user.user_id), body.code)
    return TwoFactorStatusResponse(data=TwoFactorStatusOut(is_enabled=True))


@router.post("/2fa/disable", response_model=TwoFactorStatusResponse)
async def two_factor_disable(
    body: TwoFactorDisableRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> TwoFactorStatusResponse:
    # Need the user's password hash to confirm
    from app.modules.users.repository import UsersRepository

    user = await UsersRepository(db).get_by_id(uuid.UUID(current_user.user_id))
    if not user:
        raise AppException(404, ErrorCode.NOT_FOUND, "User not found")
    await TwoFactorService(db).disable(uuid.UUID(current_user.user_id), body.password, user.password_hash)
    return TwoFactorStatusResponse(data=TwoFactorStatusOut(is_enabled=False))
