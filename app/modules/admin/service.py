from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.core.security import hash_password
from app.modules.admin.repository import AdminRepository
from app.modules.admin.schemas import (
    AdminAdviserOut,
    AdminStatsOut,
    AdminUserOut,
    CreateAdminUserBody,
    PaginatedAdminAdvisers,
    PaginatedAdminUsers,
    PaginatedMeta,
    UpdateAdminUserBody,
)


class AdminService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AdminRepository(db)

    # ── Users ─────────────────────────────────────────────────────────────────

    async def list_users(
        self,
        search: str | None = None,
        role: str | None = None,
        status: str | None = None,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedAdminUsers:
        is_active: bool | None = None
        if status == "active":
            is_active = True
        elif status == "inactive":
            is_active = False

        users, total = await self.repo.list_users(
            search=search,
            role=role,
            is_active=is_active,
            sort_by=sort_by,
            sort_dir=sort_dir,
            page=page,
            page_size=page_size,
        )
        data = [AdminUserOut.model_validate(u) for u in users]
        return PaginatedAdminUsers(
            data=data,
            meta=PaginatedMeta(page=page, page_size=page_size, total=total),
        )

    async def get_user(self, user_id: UUID) -> AdminUserOut:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")
        return AdminUserOut.model_validate(user)

    async def create_user(self, body: CreateAdminUserBody) -> AdminUserOut:
        existing = await self.repo.get_by_email(body.email)
        if existing:
            raise ConflictException(message="Email already registered")
        user = await self.repo.create_user(
            email=body.email,
            full_name=body.full_name,
            role=body.role,
            password_hash=hash_password(body.password),
        )
        await self.db.commit()
        return AdminUserOut.model_validate(user)

    async def update_user(self, user_id: UUID, body: UpdateAdminUserBody) -> AdminUserOut:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")

        update_data = body.model_dump(exclude_unset=True)

        # Check email uniqueness if changing
        if "email" in update_data and update_data["email"] != user.email:
            existing = await self.repo.get_by_email(update_data["email"])
            if existing:
                raise ConflictException(message="Email already taken")

        updated = await self.repo.update_user(user, update_data)
        await self.db.commit()
        return AdminUserOut.model_validate(updated)

    async def reset_password(self, user_id: UUID, new_password: str) -> None:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")
        await self.repo.update_user(user, {"password_hash": hash_password(new_password)})
        await self.db.commit()

    async def delete_user(self, user_id: UUID, requester_id: str) -> None:
        """Hard-delete any user. Cannot delete yourself."""
        if str(user_id) == requester_id:
            raise ForbiddenException("Cannot delete your own account")
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")
        await self.repo.delete_user(user)
        await self.db.commit()

    # ── Stats ─────────────────────────────────────────────────────────────────

    async def get_stats(self) -> AdminStatsOut:
        return await self.repo.get_stats()

    # ── Advisers ──────────────────────────────────────────────────────────────

    async def list_advisers(
        self,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedAdminAdvisers:
        rows, total = await self.repo.list_advisers(
            search=search, page=page, page_size=page_size
        )
        data = [AdminAdviserOut.model_validate(r) for r in rows]
        return PaginatedAdminAdvisers(
            data=data,
            meta=PaginatedMeta(page=page, page_size=page_size, total=total),
        )
