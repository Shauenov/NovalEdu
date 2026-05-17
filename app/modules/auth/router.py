from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import get_current_user, CurrentUser
from app.core.response import SuccessResponse
from app.database import get_db
from app.modules.auth.schemas import (
    AccessTokenEnvelope,
    AccessTokenResponse,
    TokenEnvelope,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    SessionOut,
    SessionsResponse,
    TokenResponse,
)
from app.modules.auth.service import AuthService
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()


def _get_service(
    db: AsyncSession = Depends(get_db),
    request: Request = None,
) -> AuthService:
    return AuthService(db=db, redis=request.app.state.redis)


@router.post("/register", response_model=TokenEnvelope, status_code=201)
async def register(
    body: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenEnvelope:
    service = AuthService(db=db, redis=request.app.state.redis)
    device_name = request.headers.get("X-Device-Name") or request.headers.get("User-Agent", "")[:100]
    ip_address = request.client.host if request.client else None
    result = await service.register(body, device_name=device_name, ip_address=ip_address)
    return TokenEnvelope(data=result)


@router.post("/login", response_model=TokenEnvelope)
@limiter.limit("5/minute")
async def login(
    body: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenEnvelope:
    service = AuthService(db=db, redis=request.app.state.redis)
    device_name = request.headers.get("X-Device-Name") or request.headers.get("User-Agent", "")[:100]
    ip_address = request.client.host if request.client else None
    result = await service.login(body, device_name=device_name, ip_address=ip_address)
    return TokenEnvelope(data=result)


@router.post("/refresh", response_model=AccessTokenEnvelope)
async def refresh(
    body: RefreshRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AccessTokenEnvelope:
    service = AuthService(db=db, redis=request.app.state.redis)
    result = await service.refresh_tokens(body)
    return AccessTokenEnvelope(data=result)


@router.post("/logout", response_model=SuccessResponse)
async def logout(
    body: LogoutRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    request: Request = None,
) -> SuccessResponse:
    service = AuthService(db=db, redis=request.app.state.redis)
    await service.logout(body)
    return SuccessResponse()


@router.post("/forgot-password", response_model=SuccessResponse)
@limiter.limit("3/minute")
async def forgot_password(
    body: ForgotPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    service = AuthService(db=db, redis=request.app.state.redis)
    await service.forgot_password(body)
    return SuccessResponse()


@router.post("/reset-password", response_model=SuccessResponse)
async def reset_password(
    body: ResetPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    service = AuthService(db=db, redis=request.app.state.redis)
    await service.reset_password(body)
    return SuccessResponse()


@router.post("/change-password", response_model=SuccessResponse)
async def change_password(
    body: ChangePasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> SuccessResponse:
    service = AuthService(db=db, redis=request.app.state.redis)
    await service.change_password(UUID(current_user.user_id), body)
    return SuccessResponse()


@router.get("/sessions", response_model=SessionsResponse)
async def list_sessions(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> SessionsResponse:
    service = AuthService(db=db, redis=request.app.state.redis)
    sessions = await service.list_sessions(UUID(current_user.user_id))
    return SessionsResponse(data=[SessionOut.model_validate(s) for s in sessions])


@router.delete("/sessions", response_model=SuccessResponse)
async def close_all_sessions(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> SuccessResponse:
    service = AuthService(db=db, redis=request.app.state.redis)
    await service.delete_all_sessions(UUID(current_user.user_id))
    return SuccessResponse()


@router.delete("/sessions/{session_id}", response_model=SuccessResponse)
async def close_session(
    session_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> SuccessResponse:
    service = AuthService(db=db, redis=request.app.state.redis)
    await service.delete_session(session_id, UUID(current_user.user_id))
    return SuccessResponse()
