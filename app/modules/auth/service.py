import hashlib
import random
import string
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.constants import (
    OTP_EXPIRE_SECONDS,
    ROLE_STUDENT,
)
from app.core.exceptions import (
    AppException,
    ConflictException,
    ErrorCode,
    UnauthorizedException,
    ValidationException,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.modules.auth.repository import AuthRepository
from app.modules.auth.schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    AccessTokenResponse,
    UserBrief,
)
from app.modules.profile.repository import ProfileRepository
from app.modules.profile.models import StudentProfile


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _generate_otp() -> str:
    return "".join(random.choices(string.digits, k=6))


class AuthService:
    def __init__(self, db: AsyncSession, redis) -> None:
        self.db = db
        self.redis = redis
        self.repo = AuthRepository(db)
        self.profile_repo = ProfileRepository(db)

    async def register(
        self,
        data: RegisterRequest,
        device_name: str | None = None,
        ip_address: str | None = None,
    ) -> TokenResponse:
        existing = await self.repo.get_user_by_email(data.email)
        if existing:
            raise ConflictException(
                error_code=ErrorCode.CONFLICT,
                message="A user with this email already exists",
            )

        user = await self.repo.create_user(
            email=data.email,
            full_name=data.full_name,
            password_hash=hash_password(data.password),
            role=ROLE_STUDENT,
            is_active=True,
        )

        # Create student profile
        await self.profile_repo.create(
            user_id=user.id,
            group_type=data.group_type,
            course_year=data.course_year,
            gpa=data.gpa,
            ielts_passed=data.ielts_passed,
            ielts_score=data.ielts_score,
            sat_passed=data.sat_passed,
            sat_score=data.sat_score,
        )

        await self.db.commit()
        await self.db.refresh(user)

        return await self._issue_tokens(user, device_name=device_name, ip_address=ip_address)

    async def login(
        self,
        data: LoginRequest,
        device_name: str | None = None,
        ip_address: str | None = None,
    ) -> TokenResponse:
        user = await self.repo.get_user_by_email(data.email)
        if not user or not verify_password(data.password, user.password_hash):
            raise AppException(
                401, ErrorCode.INVALID_CREDENTIALS, "Invalid email or password"
            )
        if not user.is_active:
            raise AppException(403, ErrorCode.FORBIDDEN, "Account is deactivated")

        return await self._issue_tokens(user, device_name=device_name, ip_address=ip_address)

    async def refresh_tokens(self, data: RefreshRequest) -> AccessTokenResponse:
        token_hash = _hash_token(data.refresh_token)
        stored = await self.repo.get_refresh_token_by_hash(token_hash)

        if not stored:
            raise UnauthorizedException("Refresh token not found or already used")
        if stored.expires_at < datetime.now(tz=timezone.utc):
            await self.repo.delete_refresh_token(token_hash)
            await self.db.commit()
            raise AppException(401, ErrorCode.TOKEN_EXPIRED, "Refresh token has expired")

        user = await self.repo.get_user_by_id(stored.user_id)
        if not user or not user.is_active:
            raise UnauthorizedException("User not found or deactivated")

        # Rotate — delete old, issue new
        await self.repo.delete_refresh_token(token_hash)

        access_token = create_access_token(user.id, user.role, user.email)
        new_refresh = create_refresh_token(user.id)
        new_hash = _hash_token(new_refresh)
        expires_at = datetime.now(tz=timezone.utc) + timedelta(
            days=settings.jwt_refresh_token_expire_days
        )
        await self.repo.save_refresh_token(user.id, new_hash, expires_at)
        await self.db.commit()

        return AccessTokenResponse(access_token=access_token, refresh_token=new_refresh)

    async def logout(self, data: LogoutRequest) -> None:
        token_hash = _hash_token(data.refresh_token)
        await self.repo.delete_refresh_token(token_hash)
        await self.db.commit()

    async def forgot_password(self, data: ForgotPasswordRequest) -> None:
        user = await self.repo.get_user_by_email(data.email)
        if not user:
            # Silent — don't reveal user existence
            return

        otp = _generate_otp()
        redis_key = f"otp:{data.email}"
        await self.redis.setex(redis_key, OTP_EXPIRE_SECONDS, otp)

        # Fire email task (imported lazily to avoid circular dep)
        from app.workers.email_tasks import send_email_task
        send_email_task.delay(
            to=data.email,
            subject="Password Reset OTP",
            template="password_reset.html",
            context={"full_name": user.full_name, "otp": otp},
        )

    async def reset_password(self, data: ResetPasswordRequest) -> None:
        redis_key = f"otp:{data.email}"
        stored_otp = await self.redis.get(redis_key)

        if not stored_otp:
            raise AppException(400, ErrorCode.OTP_EXPIRED, "OTP has expired or was not requested")
        if stored_otp != data.otp:
            raise AppException(400, ErrorCode.INVALID_OTP, "Invalid OTP")

        user = await self.repo.get_user_by_email(data.email)
        if not user:
            raise ValidationException("User not found")

        await self.repo.update_user_password(user.id, hash_password(data.new_password))
        await self.repo.delete_all_user_tokens(user.id)
        await self.redis.delete(redis_key)
        await self.db.commit()

    async def change_password(self, user_id: UUID, data: ChangePasswordRequest) -> None:
        user = await self.repo.get_user_by_id(user_id)
        if not user:
            raise UnauthorizedException("User not found")
        if not verify_password(data.old_password, user.password_hash):
            raise AppException(400, ErrorCode.INVALID_CREDENTIALS, "Current password is incorrect")

        await self.repo.update_user_password(user.id, hash_password(data.new_password))
        await self.db.commit()

    async def list_sessions(self, user_id: UUID):
        return await self.repo.list_sessions(user_id)

    async def delete_session(self, session_id: UUID, user_id: UUID) -> None:
        session = await self.repo.get_session_by_id(session_id, user_id)
        from app.core.exceptions import NotFoundException
        if not session:
            raise NotFoundException("Session not found")
        await self.repo.delete_session_by_id(session_id, user_id)
        await self.db.commit()

    async def delete_all_sessions(self, user_id: UUID) -> None:
        await self.repo.delete_all_user_tokens(user_id)
        await self.db.commit()

    # ─── Internal ────────────────────────────────────────────────────────────

    async def _issue_tokens(
        self,
        user,
        device_name: str | None = None,
        ip_address: str | None = None,
    ) -> TokenResponse:
        access_token = create_access_token(user.id, user.role, user.email)
        refresh_token = create_refresh_token(user.id)
        token_hash = _hash_token(refresh_token)
        expires_at = datetime.now(tz=timezone.utc) + timedelta(
            days=settings.jwt_refresh_token_expire_days
        )
        await self.repo.save_refresh_token(
            user.id, token_hash, expires_at,
            device_name=device_name,
            ip_address=ip_address,
        )
        await self.db.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserBrief.model_validate(user),
        )
