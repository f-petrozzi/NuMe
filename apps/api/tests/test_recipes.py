from __future__ import annotations

from datetime import datetime, timezone

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.recipes import Recipe
from routers.recipes import _extract_servings
from routers.recipes import DEFAULT_TEMPLATE_RECIPES


def test_extract_servings_handles_common_scraper_strings():
    assert _extract_servings("4 servings") == 4
    assert _extract_servings("Serves 6") == 6
    assert _extract_servings("Makes 12 cookies") == 12
    assert _extract_servings(3) == 3
    assert _extract_servings("unknown", 2) == 2


async def test_recommended_recipes_seeds_templates_for_current_user_without_duplicates(
    client: AsyncClient,
    db: AsyncSession,
):
    first = await client.get("/api/recipes/recommended?limit=20")
    assert first.status_code == 200, first.text

    second = await client.get("/api/recipes/recommended?limit=20")
    assert second.status_code == 200, second.text

    templates = (
        await db.execute(
            select(Recipe).where(
                Recipe.is_template.is_(True),
                Recipe.user_id == 1,
            )
        )
    ).scalars().all()

    assert len(templates) == len(DEFAULT_TEMPLATE_RECIPES)
    assert {recipe.user_id for recipe in templates} == {1}


async def test_recommended_recipes_excludes_foreign_templates_but_keeps_global_templates(
    client: AsyncClient,
    db: AsyncSession,
):
    db.add(
        Recipe(
            user_id=2,
            is_template=True,
            title="Foreign Template",
            description="Should not be visible",
            source_url="",
            our_way_notes="",
            prep_minutes=1,
            cook_minutes=1,
            servings=1,
            tags=["foreign"],
            ingredients=[],
            instructions="Nope",
            photo_filename="",
            created_at=datetime.now(timezone.utc),
        )
    )
    db.add(
        Recipe(
            user_id=None,
            is_template=True,
            title="Global Template",
            description="Legacy global template",
            source_url="",
            our_way_notes="",
            prep_minutes=1,
            cook_minutes=1,
            servings=1,
            tags=["global"],
            ingredients=[],
            instructions="Yep",
            photo_filename="",
            created_at=datetime.now(timezone.utc),
        )
    )
    await db.commit()

    resp = await client.get("/api/recipes/recommended?limit=20")
    assert resp.status_code == 200, resp.text

    titles = {item["title"] for item in resp.json()}
    assert "Foreign Template" not in titles
    assert "Global Template" in titles


async def test_get_recipe_rejects_foreign_template_but_allows_global_template(
    client: AsyncClient,
    db: AsyncSession,
):
    foreign_template = Recipe(
        user_id=2,
        is_template=True,
        title="Foreign Template",
        description="Should not be visible",
        source_url="",
        our_way_notes="",
        prep_minutes=1,
        cook_minutes=1,
        servings=1,
        tags=["foreign"],
        ingredients=[],
        instructions="Nope",
        photo_filename="",
        created_at=datetime.now(timezone.utc),
    )
    global_template = Recipe(
        user_id=None,
        is_template=True,
        title="Global Template",
        description="Legacy global template",
        source_url="",
        our_way_notes="",
        prep_minutes=1,
        cook_minutes=1,
        servings=1,
        tags=["global"],
        ingredients=[],
        instructions="Yep",
        photo_filename="",
        created_at=datetime.now(timezone.utc),
    )
    db.add(foreign_template)
    db.add(global_template)
    await db.commit()
    await db.refresh(foreign_template)
    await db.refresh(global_template)

    foreign_resp = await client.get(f"/api/recipes/{foreign_template.id}")
    assert foreign_resp.status_code == 404, foreign_resp.text

    global_resp = await client.get(f"/api/recipes/{global_template.id}")
    assert global_resp.status_code == 200, global_resp.text
    assert global_resp.json()["title"] == "Global Template"
