from __future__ import annotations
from functools import lru_cache
from typing import Any

import httpx
import jwt as pyjwt
from fastapi import HTTPException, status
from jwt import PyJWKClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from settings import settings


def clerk_enabled() -> bool:
    return bool(settings.clerk_jwt_key or settings.clerk_jwks_url or settings.clerk_frontend_api_url)


def _normalized_public_key() -> str:
    return settings.clerk_jwt_key.replace("\\n", "\n").strip()


def _authorized_parties() -> list[str]:
    return [item.strip() for item in settings.clerk_authorized_parties.split(",") if item.strip()]


def _jwks_url() -> str:
    if settings.clerk_jwks_url:
        return settings.clerk_jwks_url
    if settings.clerk_frontend_api_url:
        return f"{settings.clerk_frontend_api_url.rstrip('/')}/.well-known/jwks.json"
    return "https://api.clerk.com/v1/jwks"


@lru_cache(maxsize=4)
def _get_jwks_client(jwks_url: str) -> PyJWKClient:
    return PyJWKClient(jwks_url)


def verify_clerk_session_token(token: str) -> dict[str, Any]:
    if not clerk_enabled():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Clerk auth is not configured")

    try:
        header = pyjwt.get_unverified_header(token)
    except pyjwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token header") from exc

    if header.get("alg") != "RS256":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unexpected Clerk token algorithm")

    try:
        verification_key = _normalized_public_key() or _get_jwks_client(_jwks_url()).get_signing_key_from_jwt(token).key
        decode_kwargs: dict[str, Any] = {
            "key": verification_key,
            "algorithms": ["RS256"],
            "options": {"verify_aud": False},
        }
        if settings.clerk_frontend_api_url:
            decode_kwargs["issuer"] = settings.clerk_frontend_api_url.rstrip("/")
        claims = pyjwt.decode(token, **decode_kwargs)
    except pyjwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Clerk session token") from exc

    azp = claims.get("azp")
    if azp and _authorized_parties() and azp not in _authorized_parties():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized Clerk token origin")

    if claims.get("sts") == "pending":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Clerk session is pending")

    if not claims.get("sub"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Clerk token missing subject")

    return claims


def _extract_email_from_claims(claims: dict[str, Any]) -> str | None:
    for key in ("email", "email_address", "primaryEmail", "primary_email", "primary_email_address"):
        value = claims.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().lower()
    return None


def _extract_name_from_claims(claims: dict[str, Any]) -> str | None:
    for key in ("fullName", "full_name", "name"):
        value = claims.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


async def _fetch_clerk_user(clerk_user_id: str) -> dict[str, Any]:
    if not settings.clerk_secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Backend cannot provision first-time Clerk users without CLERK_SECRET_KEY or a custom email claim",
        )

    headers = {
        "Authorization": f"Bearer {settings.clerk_secret_key}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"https://api.clerk.com/v1/users/{clerk_user_id}", headers=headers)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Clerk user not found") from exc
        if exc.response.status_code in (401, 403):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Backend CLERK_SECRET_KEY could not fetch Clerk users",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to fetch Clerk user details",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to reach Clerk while syncing the signed-in user",
        ) from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Clerk returned an invalid user profile response",
        ) from exc

    primary_email_id = data.get("primary_email_address_id")
    primary_email = None
    for item in data.get("email_addresses", []):
        if item.get("id") == primary_email_id:
            primary_email = item.get("email_address")
            break
        if not primary_email and item.get("email_address"):
            primary_email = item.get("email_address")

    return {
        "email": (primary_email or "").lower(),
        "full_name": " ".join(part for part in [data.get("first_name"), data.get("last_name")] if part).strip(),
    }


async def get_or_create_clerk_user(claims: dict[str, Any], db: AsyncSession) -> User:
    clerk_user_id = str(claims["sub"])

    result = await db.execute(select(User).where(User.clerk_user_id == clerk_user_id))
    user = result.scalar_one_or_none()
    if user is not None:
        return user

    email = _extract_email_from_claims(claims)
    full_name = _extract_name_from_claims(claims)
    if not email:
        profile = await _fetch_clerk_user(clerk_user_id)
        email = profile["email"]
        full_name = full_name or profile.get("full_name") or ""

    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unable to resolve Clerk user email")

    existing_result = await db.execute(select(User).where(User.email == email))
    existing_user = existing_result.scalar_one_or_none()
    if existing_user is not None:
        if existing_user.clerk_user_id and existing_user.clerk_user_id != clerk_user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email is already linked to a different Clerk user")
        existing_user.clerk_user_id = clerk_user_id
        await db.commit()
        await db.refresh(existing_user)
        return existing_user

    user = User(
        clerk_user_id=clerk_user_id,
        email=email,
        role="member",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
