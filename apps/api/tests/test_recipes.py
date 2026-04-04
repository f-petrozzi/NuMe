from __future__ import annotations

from datetime import datetime, timezone

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.agents import Intervention
from models.personalization import PersonalizationStateSnapshot
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


async def test_recommended_recipes_use_snapshot_ranking_not_only_latest_intervention_constraints(
    client: AsyncClient,
    db: AsyncSession,
):
    db.add_all(
        [
            Recipe(
                user_id=1,
                is_template=True,
                title="Constraint Match Walnut Bake",
                description="Matches the old intervention tag but ignores low-prep and allergy context.",
                source_url="",
                our_way_notes="",
                prep_minutes=18,
                cook_minutes=22,
                servings=1,
                calories=640,
                protein_grams=14.0,
                carbs_grams=48.0,
                fat_grams=31.0,
                fiber_grams=5.0,
                prep_effort="high",
                equipment_tags=["oven"],
                cost_level="medium",
                tags=["comforting"],
                ingredients=[
                    {"name": "Walnuts", "quantity": "1/3 cup", "category": "Pantry", "section": "Top"},
                ],
                instructions="Bake and serve.",
                photo_filename="",
                created_at=datetime.now(timezone.utc),
            ),
            Recipe(
                user_id=1,
                is_template=True,
                title="Low Prep Safe Bowl",
                description="Aligned with the snapshot: quick, nut-safe, and higher protein.",
                source_url="",
                our_way_notes="",
                prep_minutes=6,
                cook_minutes=0,
                servings=1,
                calories=330,
                protein_grams=26.0,
                carbs_grams=27.0,
                fat_grams=10.0,
                fiber_grams=6.0,
                prep_effort="low",
                equipment_tags=["bowl"],
                cost_level="medium",
                tags=["low_prep", "avoid_nuts", "high_protein", "light"],
                ingredients=[
                    {"name": "Greek yogurt", "quantity": "1 cup", "category": "Dairy", "section": "Base"},
                    {"name": "Blueberries", "quantity": "1/2 cup", "category": "Produce", "section": "Top"},
                ],
                instructions="Combine and serve.",
                photo_filename="",
                created_at=datetime.now(timezone.utc),
            ),
            Intervention(
                user_id=1,
                meal_suggestion="Comforting meal",
                empathy_message="Keep it simple.",
                meal_constraints=["comforting"],
                created_at=datetime.now(timezone.utc),
            ),
            PersonalizationStateSnapshot(
                user_id=1,
                run_id=None,
                source="live",
                profile_static={
                    "goal": "stress_reduction",
                    "dietary_style": "balanced",
                    "allergies": ["peanuts"],
                    "persona_type": "student",
                    "accessibility": {"low_energy_mode": True},
                },
                dynamic_state={
                    "stress_load": 0.2,
                    "sleep_debt": 0.1,
                    "activity_capacity": 0.3,
                    "prep_capacity": 0.2,
                    "calorie_balance": 320,
                    "protein_gap": 0.4,
                },
                archetype_scores={"low_energy_recovery": 0.62},
                feature_windows={},
                inputs_summary={},
                created_at=datetime.now(timezone.utc),
            ),
        ]
    )
    await db.commit()

    resp = await client.get("/api/recipes/recommended?limit=2")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert [item["title"] for item in body] == ["Low Prep Safe Bowl", "Constraint Match Walnut Bake"]
