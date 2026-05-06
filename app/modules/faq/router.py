from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser, get_current_user, require_conductor_or_admin
from app.core.response import SuccessResponse
from app.database import get_db
from app.modules.faq.schemas import FAQCreate, FAQListResponse, FAQOut, FAQResponse, FAQUpdate, ReorderRequest
from app.modules.faq.service import FAQService

router = APIRouter()


@router.get("/faqs", response_model=FAQListResponse)
async def list_faqs(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> FAQListResponse:
    service = FAQService(db, redis=request.app.state.redis)
    items = await service.list_faqs()
    return FAQListResponse(data=items)


@router.post("/faqs", response_model=FAQResponse, status_code=201)
async def create_faq(
    body: FAQCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_conductor_or_admin()),
) -> FAQResponse:
    service = FAQService(db, redis=request.app.state.redis)
    item = await service.create_faq(body, UUID(current_user.user_id), current_user.role)
    return FAQResponse(data=item)


@router.put("/faqs/{faq_id}", response_model=FAQResponse)
async def update_faq(
    faq_id: UUID,
    body: FAQUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_conductor_or_admin()),
) -> FAQResponse:
    service = FAQService(db, redis=request.app.state.redis)
    item = await service.update_faq(faq_id, body, current_user.role)
    return FAQResponse(data=item)


@router.delete("/faqs/{faq_id}", response_model=SuccessResponse)
async def delete_faq(
    faq_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_conductor_or_admin()),
) -> SuccessResponse:
    service = FAQService(db, redis=request.app.state.redis)
    await service.delete_faq(faq_id, current_user.role)
    return SuccessResponse()


@router.patch("/faqs/reorder", response_model=SuccessResponse)
async def reorder_faqs(
    body: ReorderRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_conductor_or_admin()),
) -> SuccessResponse:
    service = FAQService(db, redis=request.app.state.redis)
    await service.reorder(body, current_user.role)
    return SuccessResponse()
