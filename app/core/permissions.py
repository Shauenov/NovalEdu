from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import decode_access_token
from app.core.constants import ROLE_ADMIN, ROLE_CONDUCTOR, ROLE_STUDENT
from app.database import AsyncSession, get_db

bearer_scheme = HTTPBearer(scheme_name="BearerAuth")


class CurrentUser:
    """Lightweight user container populated from JWT claims (no DB hit)."""

    def __init__(self, user_id: str, role: str, email: str) -> None:
        self.user_id = user_id
        self.role = role
        self.email = email


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> CurrentUser:
    if credentials.scheme.lower() != "bearer":
        raise UnauthorizedException("Invalid auth scheme")

    payload = decode_access_token(credentials.credentials)
    user_id: str | None = payload.get("sub")
    role: str | None = payload.get("role")
    email: str | None = payload.get("email")

    if not user_id or not role or not email:
        raise UnauthorizedException("Malformed token payload")

    return CurrentUser(user_id=user_id, role=role, email=email)


def require_roles(*roles: str):
    """Dependency factory: checks that current user has one of the allowed roles."""

    async def _check(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.role not in roles:
            raise ForbiddenException(
                f"Requires role(s): {', '.join(roles)}. Got: {current_user.role}"
            )
        return current_user

    return _check


def require_student():
    return require_roles(ROLE_STUDENT)


def require_conductor():
    return require_roles(ROLE_CONDUCTOR)


def require_admin():
    return require_roles(ROLE_ADMIN)


def require_conductor_or_admin():
    return require_roles(ROLE_CONDUCTOR, ROLE_ADMIN)


def require_any_authenticated():
    return require_roles(ROLE_STUDENT, ROLE_CONDUCTOR, ROLE_ADMIN)
