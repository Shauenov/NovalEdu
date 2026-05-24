from datetime import datetime, timezone, timedelta
from uuid import UUID

from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    DEFAULT_PAGE_SIZE,
    ROLE_ADMIN,
    ROLE_ADVISER,
    ROLE_STUDENT,
)
from app.modules.users.models import User
from app.modules.admin.schemas import AdminStatsOut, GrowthPoint, RoleBreakdown


class AdminRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Users ─────────────────────────────────────────────────────────────────

    async def list_users(
        self,
        search: str | None = None,
        role: str | None = None,
        is_active: bool | None = None,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[User], int]:
        def _apply_filters(q):
            if search:
                pattern = f"%{search}%"
                q = q.where(
                    or_(User.full_name.ilike(pattern), User.email.ilike(pattern))
                )
            if role and role != "all":
                q = q.where(User.role == role)
            if is_active is not None:
                q = q.where(User.is_active == is_active)
            return q

        stmt = _apply_filters(select(User))
        count_stmt = _apply_filters(select(func.count(User.id)))

        total = (await self.db.execute(count_stmt)).scalar_one()

        # Sorting
        allowed_sort = {"full_name", "role", "created_at"}
        col_name = sort_by if sort_by in allowed_sort else "created_at"
        col = getattr(User, col_name)
        stmt = stmt.order_by(col.asc() if sort_dir == "asc" else col.desc())

        # Paginate
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create_user(self, **kwargs) -> User:
        user = User(**kwargs)
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def update_user(self, user: User, data: dict) -> User:
        for key, value in data.items():
            setattr(user, key, value)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def delete_user(self, user: User) -> None:
        await self.db.delete(user)
        await self.db.flush()

    # ── Stats ─────────────────────────────────────────────────────────────────

    async def get_stats(self) -> AdminStatsOut:
        # Role counts
        role_rows = await self.db.execute(
            select(User.role, func.count(User.id)).group_by(User.role)
        )
        by_role = RoleBreakdown()
        for role, count in role_rows.all():
            if role == ROLE_STUDENT:
                by_role.student = count
            elif role == ROLE_ADVISER:
                by_role.adviser = count
            elif role == ROLE_ADMIN:
                by_role.admin = count

        total = by_role.student + by_role.adviser + by_role.admin

        # Active count
        active = (
            await self.db.execute(
                select(func.count(User.id)).where(User.is_active == True)  # noqa: E712
            )
        ).scalar_one()

        # Growth: registrations per month for last 6 months
        six_months_ago = datetime.now(tz=timezone.utc) - timedelta(days=180)
        growth_rows = await self.db.execute(
            select(
                func.to_char(User.created_at, "Mon").label("month"),
                func.to_char(User.created_at, "YYYY-MM").label("ym"),
                func.count(User.id).label("cnt"),
            )
            .where(User.created_at >= six_months_ago)
            .group_by("month", "ym")
            .order_by("ym")
        )
        growth = [
            GrowthPoint(month=row.month.strip(), users=row.cnt)
            for row in growth_rows.all()
        ]

        return AdminStatsOut(
            total_users=total,
            by_role=by_role,
            active_users=active,
            inactive_users=total - active,
            growth=growth,
        )

    # ── Advisers ──────────────────────────────────────────────────────────────

    async def list_advisers(
        self,
        search: str | None = None,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[dict], int]:
        """Return advisers joined with their profile + review aggregates."""
        from app.modules.advisers.models import AdviserProfile
        from app.modules.reviews.repository import ReviewsRepository

        def _apply_filters(q):
            q = q.where(User.role == ROLE_ADVISER)
            if search:
                pattern = f"%{search}%"
                q = q.where(
                    or_(User.full_name.ilike(pattern), User.email.ilike(pattern))
                )
            return q

        stmt = _apply_filters(select(User)).order_by(User.full_name.asc())
        count_stmt = _apply_filters(select(func.count(User.id)))

        total = (await self.db.execute(count_stmt)).scalar_one()
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        users = list((await self.db.execute(stmt)).scalars().all())

        reviews_repo = ReviewsRepository(self.db)
        result = []
        for user in users:
            profile_row = await self.db.execute(
                select(AdviserProfile).where(AdviserProfile.user_id == user.id)
            )
            profile = profile_row.scalar_one_or_none()
            rating_avg, reviews_count = await reviews_repo.aggregate_for_adviser(user.id)

            result.append({
                "user_id": user.id,
                "full_name": user.full_name,
                "email": user.email,
                "avatar_url": user.avatar_url,
                "is_active": user.is_active,
                "created_at": user.created_at,
                "headline": profile.headline if profile else None,
                "students_placed": profile.students_placed if profile else None,
                "rating_avg": rating_avg,
                "reviews_count": reviews_count,
            })

        return result, total
