from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.permissions import CurrentUser, get_current_user, require_ADVISER_or_admin, require_student
from app.core.response import SuccessResponse
from app.modules.messages.service import MessagesService
from app.modules.messages.schemas import (
    BroadcastResponse,
    BroadcastResult,
    ConversationResponse,
    ConversationsResponse,
    MessageResponse,
    MessagesResponse,
    MessageOut,
    ConversationOut,
    SendMessageRequest,
    BroadcastRequest,
)

router = APIRouter()


@router.get("/conversations", response_model=ConversationsResponse)
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    svc = MessagesService(db)
    is_adviser = current_user.role != "student"
    convos = await svc.list_conversations_for_user(UUID(current_user.user_id), is_adviser)
    return ConversationsResponse(data=[ConversationOut.model_validate(c) for c in convos])


@router.get("/conversations/my", response_model=ConversationResponse)
async def get_my_conversation(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_student()),
):
    svc = MessagesService(db)
    convo = await svc.get_or_create_my_conversation(UUID(current_user.user_id))
    return ConversationResponse(data=ConversationOut.model_validate(convo))


@router.get("/conversations/{convo_id}/messages", response_model=MessagesResponse)
async def get_messages(
    convo_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    svc = MessagesService(db)
    msgs = await svc.list_messages(convo_id, limit=limit, offset=offset)
    return MessagesResponse(data=[MessageOut.model_validate(m) for m in msgs])


@router.patch("/conversations/{convo_id}/read", response_model=SuccessResponse)
async def mark_read(
    convo_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> SuccessResponse:
    svc = MessagesService(db)
    await svc.mark_conversation_read(convo_id, UUID(current_user.user_id))
    return SuccessResponse()


@router.post("/conversations/{convo_id}/messages", response_model=MessageResponse, status_code=201)
async def send_message(
    convo_id: UUID,
    body: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    svc = MessagesService(db)
    msg = await svc.send_message(convo_id, UUID(current_user.user_id), body.body)
    return MessageResponse(data=MessageOut.model_validate(msg))


@router.post("/conversations/{convo_id}/messages/image", response_model=MessageResponse, status_code=201)
async def send_image_message(
    convo_id: UUID,
    image: UploadFile = File(...),
    body: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    svc = MessagesService(db)
    msg = await svc.send_message_with_image(
        convo_id,
        UUID(current_user.user_id),
        image=image,
        body=body,
    )
    return MessageResponse(data=MessageOut.model_validate(msg))


@router.post("/broadcast", response_model=BroadcastResponse, status_code=201)
async def broadcast_message(
    body: BroadcastRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_ADVISER_or_admin()),
):
    svc = MessagesService(db)
    if body.filter_group or body.ielts_passed is not None:
        convo_ids = await svc.list_conversation_ids_for_broadcast(
            adviser_id=UUID(current_user.user_id),
            group_type=body.filter_group,
            ielts_passed=body.ielts_passed,
        )
    else:
        convos = await svc.list_conversations_for_user(UUID(current_user.user_id), is_adviser=True)
        convo_ids = [c.id for c in convos]
    msgs = await svc.broadcast(body.body, convo_ids, UUID(current_user.user_id))
    return BroadcastResponse(
        data=BroadcastResult(
            sent=len(convo_ids),
            message_ids=[m.id for m in msgs],
        )
    )


@router.post("/broadcast/image", response_model=BroadcastResponse, status_code=201)
async def broadcast_image_message(
    image: UploadFile = File(...),
    body: str | None = Form(None),
    filter_group: str | None = Form(None),
    ielts_passed: bool | None = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_ADVISER_or_admin()),
):
    svc = MessagesService(db)
    if filter_group or ielts_passed is not None:
        convo_ids = await svc.list_conversation_ids_for_broadcast(
            adviser_id=UUID(current_user.user_id),
            group_type=filter_group,
            ielts_passed=ielts_passed,
        )
    else:
        convos = await svc.list_conversations_for_user(UUID(current_user.user_id), is_adviser=True)
        convo_ids = [c.id for c in convos]

    msgs = await svc.broadcast_with_image(body, convo_ids, UUID(current_user.user_id), image)
    return BroadcastResponse(
        data=BroadcastResult(
            sent=len(convo_ids),
            message_ids=[m.id for m in msgs],
        )
    )
