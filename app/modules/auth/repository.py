from datetime import datetime, timezone, timedelta
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import RefreshToken
from app.modules.users.models import User


class AuthRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ─── User helpers ────────────────────────────────────────────────────────

    async def get_user_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def create_user(self, **kwargs) -> User:
        user = User(**kwargs)
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def update_user_password(self, user_id: UUID, new_hash: str) -> None:
        user = await self.get_user_by_id(user_id)
        if user:
            user.password_hash = new_hash
            await self.db.flush()

    # ─── Refresh tokens ──────────────────────────────────────────────────────

    async def save_refresh_token(
        self,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        device_name: str | None = None,
        ip_address: str | None = None,
    ) -> RefreshToken:
        token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            device_name=device_name,
            ip_address=ip_address,
        )
        self.db.add(token)
        await self.db.flush()
        return token

    async def list_sessions(self, user_id: UUID) -> list[RefreshToken]:
        result = await self.db.execute(
            select(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.expires_at > datetime.now(tz=timezone.utc),
            )
            .order_by(RefreshToken.last_used_at.desc())
        )
        return result.scalars().all()

    async def get_session_by_id(self, session_id: UUID, user_id: UUID) -> RefreshToken | None:
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.id == session_id, RefreshToken.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def delete_session_by_id(self, session_id: UUID, user_id: UUID) -> None:
        await self.db.execute(
            delete(RefreshToken).where(
                RefreshToken.id == session_id, RefreshToken.user_id == user_id
            )
        )

    async def get_refresh_token_by_hash(self, token_hash: str) -> RefreshToken | None:
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def delete_refresh_token(self, token_hash: str) -> None:
        await self.db.execute(
            delete(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )

    async def delete_all_user_tokens(self, user_id: UUID) -> None:
        await self.db.execute(
            delete(RefreshToken).where(RefreshToken.user_id == user_id)
        )

    async def delete_expired_tokens(self) -> int:
        result = await self.db.execute(
            delete(RefreshToken).where(
                RefreshToken.expires_at < datetime.now(tz=timezone.utc)
            )
        )
        return result.rowcount
