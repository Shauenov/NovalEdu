import json
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import CACHE_TTL_FAQS, ROLE_ADMIN, ROLE_ADVISER
from app.core.exceptions import ForbiddenException, NotFoundException
from app.modules.faq.repository import FAQRepository
from app.modules.faq.schemas import FAQCreate, FAQUpdate, FAQOut, ReorderRequest


class FAQService:
    def __init__(self, db: AsyncSession, redis=None) -> None:
        self.db = db
        self.redis = redis
        self.repo = FAQRepository(db)
        self.cache_key = "faqs:active"

    async def list_faqs(self) -> list[FAQOut]:
        if self.redis:
            cached = await self.redis.get(self.cache_key)
            if cached:
                items = json.loads(cached)
                return [FAQOut.model_validate(i) for i in items]

        faqs = await self.repo.list_active()
        results = [FAQOut.model_validate(f) for f in faqs]

        if self.redis:
            payload = [r.model_dump(mode="json") for r in results]
            await self.redis.setex(self.cache_key, CACHE_TTL_FAQS, json.dumps(payload))

        return results

    async def create_faq(self, data: FAQCreate, created_by: UUID, requester_role: str) -> FAQOut:
        if requester_role not in (ROLE_ADMIN, ROLE_ADVISER):
            raise ForbiddenException("Only ADVISER or admin can create FAQs")
        faq = await self.repo.create(created_by=created_by, **data.model_dump())
        await self.db.commit()
        await self._invalidate_cache()
        return FAQOut.model_validate(faq)

    async def update_faq(self, faq_id: UUID, data: FAQUpdate, requester_role: str) -> FAQOut:
        if requester_role not in (ROLE_ADMIN, ROLE_ADVISER):
            raise ForbiddenException("Only ADVISER or admin can update FAQs")
        faq = await self.repo.get_by_id(faq_id)
        if not faq:
            raise NotFoundException("FAQ not found")
        updated = await self.repo.update(faq, data.model_dump(exclude_unset=True))
        await self.db.commit()
        await self._invalidate_cache()
        return FAQOut.model_validate(updated)

    async def delete_faq(self, faq_id: UUID, requester_role: str) -> None:
        if requester_role not in (ROLE_ADMIN, ROLE_ADVISER):
            raise ForbiddenException("Only ADVISER or admin can delete FAQs")
        faq = await self.repo.get_by_id(faq_id)
        if not faq:
            raise NotFoundException("FAQ not found")
        await self.repo.deactivate(faq)
        await self.db.commit()
        await self._invalidate_cache()

    async def reorder(self, data: ReorderRequest, requester_role: str) -> None:
        if requester_role not in (ROLE_ADMIN, ROLE_ADVISER):
            raise ForbiddenException("Only ADVISER or admin can reorder FAQs")
        items = [(i.id, i.order_index) for i in data.items]
        await self.repo.reorder(items)
        await self.db.commit()
        await self._invalidate_cache()

    async def _invalidate_cache(self) -> None:
        if self.redis:
            await self.redis.delete(self.cache_key)
