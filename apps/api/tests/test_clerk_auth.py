from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from clerk_auth import get_or_create_clerk_user
from models.user import User


@pytest.mark.asyncio
async def test_get_or_create_clerk_user_accepts_username_only_claims(db):
    user = await get_or_create_clerk_user({"sub": "clerk_user_1", "username": "wellness_member"}, db)

    assert user.clerk_user_id == "clerk_user_1"
    assert user.username == "wellness_member"
    assert user.email is None
    assert user.role == "member"


@pytest.mark.asyncio
async def test_get_or_create_clerk_user_fetches_username_when_claims_have_no_identifier(db):
    with patch(
        "clerk_auth._fetch_clerk_user",
        new=AsyncMock(return_value={"email": None, "username": "profile_member", "full_name": ""}),
    ):
        user = await get_or_create_clerk_user({"sub": "clerk_user_2"}, db)

    assert user.clerk_user_id == "clerk_user_2"
    assert user.username == "profile_member"
    assert user.email is None


@pytest.mark.asyncio
async def test_get_or_create_clerk_user_links_existing_username_user(db):
    existing = User(username="seeded_member", role="coordinator")
    db.add(existing)
    await db.commit()

    user = await get_or_create_clerk_user({"sub": "clerk_user_3", "username": "seeded_member"}, db)

    assert user.id == existing.id
    assert user.clerk_user_id == "clerk_user_3"
    assert user.role == "coordinator"

    result = await db.execute(select(User).where(User.id == existing.id))
    refreshed = result.scalar_one()
    assert refreshed.clerk_user_id == "clerk_user_3"
