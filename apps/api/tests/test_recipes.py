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


async def test_create_recipe_accepts_nutrition_and_effort_fields(
    client: AsyncClient,
    db: AsyncSession,
):
    resp = await client.post(
        "/api/recipes",
        json={
            "title": "Protein Pasta",
            "description": "Simple weeknight dinner",
            "source_url": "https://example.com/pasta",
            "our_way_notes": "Double the vegetables if desired.",
            "prep_minutes": 12,
            "cook_minutes": 15,
            "servings": 2,
            "calories": 540,
            "protein_grams": 32.5,
            "carbs_grams": 58.0,
            "fat_grams": 14.0,
            "fiber_grams": 9.0,
            "prep_effort": "medium",
            "equipment_tags": ["pot", "colander"],
            "cost_level": "medium",
            "tags": ["high_protein", "quick"],
            "ingredients": [
                {"name": "pasta", "quantity": "8 oz", "category": "Pantry", "section": "Main"},
            ],
            "instructions": "Boil pasta.\nServe.",
            "photo_filename": "",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["calories"] == 540
    assert body["protein_grams"] == 32.5
    assert body["prep_effort"] == "medium"
    assert body["equipment_tags"] == ["pot", "colander"]
    assert body["cost_level"] == "medium"

    recipe = (await db.execute(select(Recipe).where(Recipe.id == body["id"]))).scalar_one()
    assert recipe.calories == 540
    assert recipe.protein_grams == 32.5
    assert recipe.carbs_grams == 58.0
    assert recipe.fat_grams == 14.0
    assert recipe.fiber_grams == 9.0
    assert recipe.prep_effort == "medium"
    assert recipe.equipment_tags == ["pot", "colander"]
    assert recipe.cost_level == "medium"


async def test_create_recipe_remains_backward_compatible_without_new_fields(
    client: AsyncClient,
):
    resp = await client.post(
        "/api/recipes",
        json={
            "title": "Basic Toast",
            "description": "Still works without Ticket 4 metadata",
            "source_url": "",
            "our_way_notes": "",
            "prep_minutes": 2,
            "cook_minutes": 1,
            "servings": 1,
            "tags": ["quick"],
            "ingredients": [
                {"name": "bread", "quantity": "2 slices", "category": "Bakery", "section": ""},
            ],
            "instructions": "Toast bread.",
            "photo_filename": "",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["title"] == "Basic Toast"
    assert body["calories"] is None
    assert body["prep_effort"] == "low"
    assert body["equipment_tags"] == []
    assert body["cost_level"] is None


async def test_recommended_recipes_include_new_metadata_fields(
    client: AsyncClient,
):
    resp = await client.get("/api/recipes/recommended?limit=20")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body
    assert "calories" in body[0]
    assert "protein_grams" in body[0]
    assert "equipment_tags" in body[0]
