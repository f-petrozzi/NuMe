from __future__ import annotations

import hmac
from typing import Optional

from fastapi import Cookie, Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from clerk_auth import get_or_create_clerk_user, verify_clerk_session_token
from database import get_db
from models.user import User
from settings import settings

bearer_scheme = HTTPBearer(auto_error=False)
STAFF_ROLES = {"coordinator", "admin"}
DEMO_PRIVILEGED_EMAILS: frozenset[str] = frozenset({"petrozzi.fabrizio@gmail.com", "337401@gmail.com"})
INTERNAL_API_KEY_HEADER = "X-Internal-Api-Key"
INTERNAL_USER_ID_HEADER = "X-Internal-User-Id"


def can_use_demo(user: User) -> bool:
    return bool(user.email and user.email in DEMO_PRIVILEGED_EMAILS)


async def _resolve_internal_user(
    *,
    x_internal_api_key: str | None,
    x_internal_user_id: str | None,
    db: AsyncSession,
) -> User | None:
    if not x_internal_api_key and not x_internal_user_id:
        return None

    if not settings.internal_api_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Internal API auth is not configured",
        )

    if not x_internal_api_key or not hmac.compare_digest(x_internal_api_key, settings.internal_api_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid internal API token")

    if not x_internal_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing internal acting user")

    try:
        user_id = int(x_internal_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid internal acting user") from exc

    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Internal acting user not found")
    return user


async def get_real_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session_cookie: Optional[str] = Cookie(default=None, alias="__session"),
    x_internal_api_key: Optional[str] = Header(default=None, alias=INTERNAL_API_KEY_HEADER),
    x_internal_user_id: Optional[str] = Header(default=None, alias=INTERNAL_USER_ID_HEADER),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Returns the authenticated Clerk user, always ignoring demo impersonation."""
    internal_user = await _resolve_internal_user(
        x_internal_api_key=x_internal_api_key,
        x_internal_user_id=x_internal_user_id,
        db=db,
    )
    if internal_user is not None:
        return internal_user

    token = credentials.credentials if credentials is not None else session_cookie
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authentication token")
    claims = verify_clerk_session_token(token)
    return await get_or_create_clerk_user(claims, db)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session_cookie: Optional[str] = Cookie(default=None, alias="__session"),
    x_demo_as: Optional[str] = Header(default=None, alias="X-Demo-As"),
    x_internal_api_key: Optional[str] = Header(default=None, alias=INTERNAL_API_KEY_HEADER),
    x_internal_user_id: Optional[str] = Header(default=None, alias=INTERNAL_USER_ID_HEADER),
    db: AsyncSession = Depends(get_db),
) -> User:
    internal_user = await _resolve_internal_user(
        x_internal_api_key=x_internal_api_key,
        x_internal_user_id=x_internal_user_id,
        db=db,
    )
    if internal_user is not None:
        return internal_user

    token = credentials.credentials if credentials is not None else session_cookie
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authentication token")

    claims = verify_clerk_session_token(token)
    real_user = await get_or_create_clerk_user(claims, db)

    if x_demo_as and can_use_demo(real_user):
        result = await db.execute(select(User).where(User.email == x_demo_as))
        demo_user = result.scalar_one_or_none()
        if demo_user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Demo user not found: {x_demo_as}")
        return demo_user

    return real_user


def is_admin(user: User) -> bool:
    return user.role == "admin"


def is_staff(user: User) -> bool:
    return user.role in STAFF_ROLES


async def get_current_admin(user: User = Depends(get_current_user)) -> User:
    if not is_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    return user


async def get_current_coordinator(user: User = Depends(get_current_user)) -> User:
    if not is_staff(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Coordinator or admin required")
    return user
