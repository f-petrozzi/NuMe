"""
Recipe endpoints.
Adapted from Nest homelab — same parsing logic, adapted for SQLAlchemy async + PostgreSQL.
"""
from __future__ import annotations

import ipaddress
import json
import logging
import re
import socket
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, unquote as _url_unquote, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from dependencies.rate_limit import COST_LIGHT, enforce_ai_rate_limit, require_ai_enabled
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db, get_rate_limit_db
from models.agents import Intervention
from models.recipes import MealPlanSlot, Recipe
from models.user import User
from openai_client import generate_text
from schemas.recipes import (
    MealPlanSlotIn,
    MealPlanSlotOut,
    ParsedRecipe,
    RecipeIn,
    RecipeOut,
    RecipeParseTextRequest,
    RecipeParseUrlRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/recipes", tags=["recipes"])

# ---------------------------------------------------------------------------
# Ingredient quantity regex — matches leading "amount + unit" in ingredient strings
# ---------------------------------------------------------------------------
_QTY_RE = re.compile(
    r'^([\d\s½⅓¼¾⅔⅛⅜⅝⅞./,-]+\s*'
    r'(?:cups?|tbsp\.?|tsp\.?|tablespoons?|teaspoons?|oz\.?|fl\.?\s*oz\.?|'
    r'ounces?|lbs?\.?|pounds?|grams?|g(?=\b)|kg|ml|'
    r'liters?|litres?|l(?=\b)|pt\.?|qt\.?|'
    r'cloves?|cans?|bunches?|slices?|pieces?|heads?|stalks?|sprigs?|'
    r'pinch|dash|handful|large|medium|small|whole|'
    r'c(?=[.\s]))'
    r'\.?\s*)',
    re.IGNORECASE,
)

_UNIT_NORMALIZATIONS = [
    (re.compile(r'\bteaspoons?\b|\bteas?\.\b|\btsp\.\b', re.I), 'tsp'),
    (re.compile(r'\btablespoons?\b|\btbsp?\.\b|\btbs\.\b', re.I), 'tbsp'),
    (re.compile(r'\bounces?\b|\boz\.\b', re.I), 'oz'),
    (re.compile(r'\bpounds?\b|\blbs?\.\b', re.I), 'lb'),
    (re.compile(r'\bgrams?\b', re.I), 'g'),
    (re.compile(r'\bmilliliters?\b|\bmillilitres?\b', re.I), 'ml'),
]

_PRINT_WRAPPERS = {'printfriendly.com', 'print.it', 'easyprint.me', 'printpage.me'}
_ALLOWED_SCHEMES = {"http", "https"}
_MAX_HTML_BYTES = 15 * 1024 * 1024
_MAX_REDIRECTS = 5

VALID_CATEGORIES = {"Produce", "Meat", "Dairy", "Pantry", "Frozen", "Bakery", "Beverages", "Other"}

DEFAULT_TEMPLATE_RECIPES = [
    {
        "title": "Spinach Yogurt Bowl",
        "description": "A quick, high-protein bowl with magnesium-rich greens and almost no prep.",
        "tags": ["high_protein", "low_prep", "comforting", "hydration_support"],
        "prep_minutes": 8,
        "cook_minutes": 0,
        "servings": 1,
        "ingredients": [
            {"name": "Greek yogurt", "quantity": "1 cup", "category": "Dairy", "section": "Base"},
            {"name": "Baby spinach", "quantity": "1 cup", "category": "Produce", "section": "Base"},
            {"name": "Walnuts", "quantity": "2 tbsp", "category": "Pantry", "section": "Toppings"},
            {"name": "Blueberries", "quantity": "1/2 cup", "category": "Produce", "section": "Toppings"},
        ],
        "instructions": "Blend spinach into yogurt until smooth.\nTop with walnuts and blueberries.\nServe cold.",
    },
    {
        "title": "Comforting Lentil Rice Cup",
        "description": "A warm, gentle meal built for high-stress days when energy is low.",
        "tags": ["comforting", "low_prep", "light", "vegetarian"],
        "prep_minutes": 5,
        "cook_minutes": 12,
        "servings": 1,
        "ingredients": [
            {"name": "Microwave rice", "quantity": "1 cup", "category": "Pantry", "section": "Main"},
            {"name": "Cooked lentils", "quantity": "3/4 cup", "category": "Pantry", "section": "Main"},
            {"name": "Olive oil", "quantity": "1 tbsp", "category": "Pantry", "section": "Finish"},
            {"name": "Salt", "quantity": "1 pinch", "category": "Pantry", "section": "Finish"},
        ],
        "instructions": "Warm the rice and lentils.\nCombine in a bowl with olive oil and salt.\nEat as a low-effort recovery meal.",
    },
    {
        "title": "Hydration Citrus Oats",
        "description": "Soft oats with fruit and chia for recovery after poor sleep or elevated stress.",
        "tags": ["hydration_support", "high_protein", "light", "breakfast"],
        "prep_minutes": 5,
        "cook_minutes": 10,
        "servings": 1,
        "ingredients": [
            {"name": "Rolled oats", "quantity": "1/2 cup", "category": "Pantry", "section": "Oats"},
            {"name": "Milk or soy milk", "quantity": "1 cup", "category": "Dairy", "section": "Oats"},
            {"name": "Orange slices", "quantity": "1/2 cup", "category": "Produce", "section": "Toppings"},
            {"name": "Chia seeds", "quantity": "1 tbsp", "category": "Pantry", "section": "Toppings"},
        ],
        "instructions": "Cook oats in milk until soft.\nTop with orange slices and chia seeds.\nServe warm.",
    },
    {
        "title": "Dairy-Free Recovery Smoothie",
        "description": "A fast dairy-free option for low-energy days with basic protein and hydration support.",
        "tags": ["low_prep", "hydration_support", "high_protein", "avoid_dairy"],
        "prep_minutes": 5,
        "cook_minutes": 0,
        "servings": 1,
        "ingredients": [
            {"name": "Soy milk", "quantity": "1 cup", "category": "Beverages", "section": "Smoothie"},
            {"name": "Banana", "quantity": "1", "category": "Produce", "section": "Smoothie"},
            {"name": "Frozen berries", "quantity": "1/2 cup", "category": "Frozen", "section": "Smoothie"},
            {"name": "Protein powder", "quantity": "1 scoop", "category": "Pantry", "section": "Smoothie"},
        ],
        "instructions": "Blend all ingredients until smooth.\nDrink immediately.",
    },
    {
        "title": "Nut-Free Chickpea Toast",
        "description": "A simple savory option with protein that works well for stress-support lunch.",
        "tags": ["high_protein", "low_prep", "avoid_nuts", "light"],
        "prep_minutes": 10,
        "cook_minutes": 5,
        "servings": 1,
        "ingredients": [
            {"name": "Bread", "quantity": "2 slices", "category": "Bakery", "section": "Toast"},
            {"name": "Chickpeas", "quantity": "1/2 cup", "category": "Pantry", "section": "Topping"},
            {"name": "Olive oil", "quantity": "1 tsp", "category": "Pantry", "section": "Topping"},
            {"name": "Lemon juice", "quantity": "1 tsp", "category": "Produce", "section": "Topping"},
        ],
        "instructions": "Toast the bread.\nMash chickpeas with olive oil and lemon juice.\nSpread on toast and serve.",
    },
]


def _template_recipe_scope(user_id: int):
    return or_(Recipe.user_id == user_id, Recipe.user_id.is_(None))


async def _ensure_template_recipes(db: AsyncSession, *, user_id: int) -> None:
    existing = (
        await db.execute(
            select(Recipe)
            .where(Recipe.is_template.is_(True), _template_recipe_scope(user_id))
            .limit(1)
        )
    ).scalar_one_or_none()
    if existing is not None:
        return

    for template in DEFAULT_TEMPLATE_RECIPES:
        db.add(
            Recipe(
                user_id=user_id,
                is_template=True,
                title=template["title"],
                description=template["description"],
                source_url="",
                our_way_notes="",
                prep_minutes=template["prep_minutes"],
                cook_minutes=template["cook_minutes"],
                servings=template["servings"],
                tags=template["tags"],
                ingredients=template["ingredients"],
                instructions=template["instructions"],
                photo_filename="",
            )
        )
    await db.commit()


# ---------------------------------------------------------------------------
# URL safety helpers
# ---------------------------------------------------------------------------

def _unwrap_url(url: str) -> str:
    try:
        p = urlparse(url)
        host = (p.hostname or '').lstrip('www.')
        if host in _PRINT_WRAPPERS:
            params = parse_qs(p.query)
            if 'url' in params:
                return _url_unquote(params['url'][0])
    except Exception:
        pass
    return url


def _is_forbidden_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (
        ip.is_private or ip.is_loopback or ip.is_link_local
        or ip.is_multicast or ip.is_reserved or ip.is_unspecified
        or getattr(ip, "is_site_local", False)
    )


def _validate_url(url: str) -> str:
    """Validate URL scheme, hostname, and that it doesn't resolve to a private IP."""
    url = _unwrap_url(url.strip())
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise HTTPException(400, "URL must use http or https")
    hostname = parsed.hostname or ""
    if not hostname:
        raise HTTPException(400, "URL has no hostname")
    if hostname.lower() in {"localhost", "localhost.localdomain", "host.docker.internal"}:
        raise HTTPException(400, "URL hostname not allowed")
    try:
        addr = socket.getaddrinfo(hostname, None)[0][4][0]
        ip = ipaddress.ip_address(addr)
        if _is_forbidden_ip(ip):
            raise HTTPException(400, "URL resolves to a private/reserved address")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, f"Could not resolve hostname: {hostname}")
    return url


# ---------------------------------------------------------------------------
# Ingredient extraction helpers
# ---------------------------------------------------------------------------

def _normalize_qty(qty: str) -> str:
    for pattern, replacement in _UNIT_NORMALIZATIONS:
        qty = pattern.sub(replacement, qty)
    return qty.strip()


def _split_ingredient(raw: str) -> tuple[str, str]:
    """Split 'quantity name' into (quantity, name)."""
    m = _QTY_RE.match(raw)
    if m:
        qty = _normalize_qty(m.group(1).strip())
        name = raw[m.end():].strip()
        return qty, name
    return "", raw.strip()


def _normalize_instructions(raw: Any) -> str:
    """Normalize instructions to one-step-per-line text with ## section headers."""
    if isinstance(raw, list):
        lines = []
        for item in raw:
            s = str(item).strip()
            if not s:
                continue
            # Strip leading step numbers: "1. ", "Step 1:", "1)"
            s = re.sub(r'^(?:step\s*)?\d+[.):\s]+', '', s, flags=re.I).strip()
            lines.append(s)
        return "\n".join(lines)
    if isinstance(raw, str):
        text = raw.strip()
        # Already formatted with ## headers — return as-is
        if "\n" in text:
            return text
        # Try to split on numbered patterns
        parts = re.split(r'(?<=[.!?])\s+(?=\d+[.):\s])', text)
        if len(parts) > 1:
            return "\n".join(re.sub(r'^\d+[.):\s]+', '', p).strip() for p in parts)
        return text
    return ""


def _extract_ingredients_from_html(html_str: str) -> list[dict] | None:
    """Try to extract grouped ingredients from Tasty Recipes or WP Recipe Maker HTML."""
    soup = BeautifulSoup(html_str, "lxml")

    # Tasty Recipes
    tasty = soup.select(".tasty-recipes-ingredients")
    if tasty:
        ingredients = []
        for block in tasty:
            section_el = block.find(re.compile(r'^h[2-6]$'))
            section_name = section_el.get_text(strip=True) if section_el else ""
            for li in block.select("li"):
                raw = li.get_text(" ", strip=True)
                qty, name = _split_ingredient(raw)
                ingredients.append({"name": name, "quantity": qty, "category": "Other", "section": section_name})
        if ingredients:
            return ingredients

    # WP Recipe Maker
    wprm = soup.select(".wprm-recipe-ingredient-container")
    if wprm:
        ingredients = []
        for container in wprm:
            section_el = container.find(class_="wprm-recipe-ingredient-group-name")
            section_name = section_el.get_text(strip=True) if section_el else ""
            for item in container.select(".wprm-recipe-ingredient"):
                amount = item.find(class_="wprm-recipe-ingredient-amount")
                unit = item.find(class_="wprm-recipe-ingredient-unit")
                name_el = item.find(class_="wprm-recipe-ingredient-name")
                qty = ((amount.get_text(" ") if amount else "") + " " + (unit.get_text(" ") if unit else "")).strip()
                name = name_el.get_text(strip=True) if name_el else item.get_text(" ", strip=True)
                ingredients.append({"name": name, "quantity": _normalize_qty(qty), "category": "Other", "section": section_name})
        if ingredients:
            return ingredients

    return None


def _extract_instructions_jsonld(jsonld: dict) -> str | None:
    """Extract instructions from JSON-LD Recipe object, preserving section headers."""
    instructions_raw = jsonld.get("recipeInstructions") or jsonld.get("instructions")
    if not instructions_raw:
        return None
    if isinstance(instructions_raw, str):
        return _normalize_instructions(instructions_raw)

    lines: list[str] = []

    def _process_steps(steps: list, prefix: str = "") -> None:
        for item in steps:
            if isinstance(item, str):
                s = re.sub(r'^(?:step\s*)?\d+[.):\s]+', '', item, flags=re.I).strip()
                if s:
                    lines.append(s)
            elif isinstance(item, dict):
                t = item.get("@type", "")
                if t == "HowToSection":
                    name = item.get("name", "")
                    if name:
                        lines.append(f"## {name}")
                    _process_steps(item.get("itemListElement") or [], prefix)
                elif t in ("HowToStep", ""):
                    text = item.get("text") or item.get("name") or ""
                    text = re.sub(r'^(?:step\s*)?\d+[.):\s]+', '', text, flags=re.I).strip()
                    if text:
                        lines.append(text)

    _process_steps(instructions_raw if isinstance(instructions_raw, list) else [instructions_raw])
    return "\n".join(lines) if lines else None


def _extract_jsonld_recipe(html_str: str) -> dict | None:
    """Find and parse JSON-LD Recipe objects from HTML."""
    soup = BeautifulSoup(html_str, "lxml")
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except Exception:
            continue
        if isinstance(data, list):
            data = next((d for d in data if isinstance(d, dict) and "Recipe" in d.get("@type", "")), None)
            if not data:
                continue
        if isinstance(data, dict):
            if "Recipe" in data.get("@type", ""):
                return data
            # @graph pattern
            if "@graph" in data:
                for item in data["@graph"]:
                    if isinstance(item, dict) and "Recipe" in item.get("@type", ""):
                        return item
    return None


def _safe_int(val: Any, default: int = 0) -> int:
    try:
        return int(val or default)
    except (TypeError, ValueError):
        return default


def _extract_servings(val: Any, default: int = 0) -> int:
    if val is None:
        return default
    parsed = _safe_int(val)
    if parsed:
        return parsed
    match = re.search(r"(\d+)", str(val))
    if match:
        return int(match.group(1))
    return default


# ---------------------------------------------------------------------------
# URL parsing endpoint
# ---------------------------------------------------------------------------

@router.post("/parse-url", response_model=ParsedRecipe)
async def parse_url(
    body: RecipeParseUrlRequest,
    user: User = Depends(get_current_user),
):
    url = _validate_url(body.url)

    # Fetch HTML
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; NüMe/1.0)",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            max_redirects=_MAX_REDIRECTS,
            timeout=15.0,
            headers=headers,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            content_bytes = response.content[:_MAX_HTML_BYTES]
            # Detect charset
            content_type = response.headers.get("content-type", "")
            charset = "utf-8"
            if "charset=" in content_type:
                charset = content_type.split("charset=")[-1].strip().split(";")[0].strip()
            try:
                html = content_bytes.decode(charset, errors="replace")
            except (LookupError, UnicodeDecodeError):
                html = content_bytes.decode("utf-8", errors="replace")
            canonical_url = str(response.url)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, f"Failed to fetch URL: {exc}")

    # Try recipe-scrapers first
    scraper = None
    try:
        from recipe_scrapers import scrape_html, WebsiteNotImplementedError
        scraper = scrape_html(html, org_url=canonical_url)
    except Exception:
        scraper = None

    # JSON-LD extraction
    jsonld = _extract_jsonld_recipe(html)

    # Title
    title = ""
    if scraper:
        try:
            title = scraper.title() or ""
        except Exception:
            pass
    if not title and jsonld:
        title = jsonld.get("name") or ""

    # Description
    description = ""
    if scraper:
        try:
            description = scraper.description() or ""
        except Exception:
            pass
    if not description and jsonld:
        description = jsonld.get("description") or ""

    # Times
    prep_minutes = 0
    cook_minutes = 0
    if scraper:
        try:
            prep_minutes = _safe_int(scraper.prep_time())
        except Exception:
            pass
        try:
            cook_minutes = _safe_int(scraper.cook_time())
        except Exception:
            pass
    if jsonld and not prep_minutes:
        pt = jsonld.get("prepTime") or ""
        m = re.search(r'(\d+)', str(pt))
        if m:
            prep_minutes = int(m.group(1))
    if jsonld and not cook_minutes:
        ct = jsonld.get("cookTime") or ""
        m = re.search(r'(\d+)', str(ct))
        if m:
            cook_minutes = int(m.group(1))

    # Servings
    servings = 2
    if scraper:
        try:
            servings = _extract_servings(scraper.yields(), 0)
        except Exception:
            pass
    if not servings and jsonld:
        servings = _extract_servings(jsonld.get("recipeYield"), 0)

    # Instructions — prefer JSON-LD for section preservation
    instructions = ""
    if jsonld:
        instructions = _extract_instructions_jsonld(jsonld) or ""
    if not instructions and scraper:
        try:
            inst_list = scraper.instructions_list()
            if inst_list:
                instructions = _normalize_instructions(inst_list)
        except Exception:
            pass
        if not instructions:
            try:
                instructions = _normalize_instructions(scraper.instructions())
            except Exception:
                pass

    # Ingredients — prefer HTML plugin groups, then scraper groups, then raw
    ingredients: list[dict] = []

    html_groups = _extract_ingredients_from_html(html)
    if html_groups:
        ingredients = html_groups
    else:
        # Try scraper ingredient groups
        if scraper:
            try:
                groups = scraper.ingredient_groups()
                if groups:
                    for group in groups:
                        section_name = getattr(group, "purpose", "") or ""
                        for raw in group.ingredients:
                            qty, name = _split_ingredient(raw)
                            ingredients.append({"name": name, "quantity": qty, "category": "Other", "section": section_name})
            except Exception:
                pass

        if not ingredients and scraper:
            try:
                for raw in scraper.ingredients():
                    qty, name = _split_ingredient(raw)
                    ingredients.append({"name": name, "quantity": qty, "category": "Other", "section": ""})
            except Exception:
                pass

        if not ingredients and jsonld:
            for raw in (jsonld.get("recipeIngredient") or []):
                qty, name = _split_ingredient(str(raw))
                ingredients.append({"name": name, "quantity": qty, "category": "Other", "section": ""})

    # Photo URL
    photo_url = ""
    if jsonld:
        img = jsonld.get("image")
        if isinstance(img, str):
            photo_url = img
        elif isinstance(img, dict):
            photo_url = img.get("url", "")
        elif isinstance(img, list) and img:
            first = img[0]
            photo_url = first if isinstance(first, str) else (first or {}).get("url", "")
    if not photo_url and scraper:
        try:
            photo_url = scraper.image() or ""
        except Exception:
            pass

    if not title:
        raise HTTPException(422, "Could not extract recipe title from this URL")

    return ParsedRecipe(
        title=title,
        description=str(description)[:500],
        source_url=canonical_url,
        prep_minutes=prep_minutes,
        cook_minutes=cook_minutes,
        servings=servings or 2,
        tags=[],
        ingredients=ingredients,
        instructions=instructions,
        photo_url=photo_url,
    )


# ---------------------------------------------------------------------------
# Text parsing endpoint (Azure OpenAI)
# ---------------------------------------------------------------------------

@router.post("/parse-text", response_model=ParsedRecipe)
async def parse_text(
    body: RecipeParseTextRequest,
    request: Request,
    _ai_gate: None = Depends(require_ai_enabled),
    user: User = Depends(get_current_user),
    rate_limit_db: AsyncSession = Depends(get_rate_limit_db),
):
    if not body.text.strip():
        raise HTTPException(400, "text is empty")

    await enforce_ai_rate_limit(
        request=request,
        user=user,
        db=rate_limit_db,
        cost_units=COST_LIGHT,
    )

    try:
        prompt = (
            'Extract the recipe below into a JSON object with exactly these keys:\n'
            'title, description, prep_minutes, cook_minutes, servings,\n'
            'ingredients (array of {name, quantity, category, section}), instructions (array of strings), tags.\n\n'
            'Rules:\n'
            '- "quantity": copy the FULL quantity string exactly as written including alternatives and parenthetical notes.\n'
            '  Example: "220g (or 2 sticks/1 cup)", "2 large eggs + 1 yolk". Never invent a quantity not stated.\n'
            '- "name": use the standard grocery-store name. Keep type qualifiers. Remove opinion words only.\n'
            '  Expand abbreviations: "AP flour" → "all-purpose flour".\n'
            '- "category": one of: Produce Meat Dairy Pantry Frozen Bakery Beverages Other\n'
            '- "section": if the recipe has labelled ingredient groups (e.g. "For the sauce:", "Crust", "Filling"),\n'
            '  set this to that group name. Otherwise empty string.\n'
            '- "instructions": a JSON ARRAY of strings, one element per step, no numbering.\n'
            '  If the recipe has named instruction sections (e.g. "Make the sauce:"),\n'
            '  insert that section name prefixed with "## " as its own array element immediately before the steps.\n'
            '  Example: ["## Make the sauce", "Blend tomatoes.", "## Assemble", "Layer ingredients."].\n'
            '- "tags": array of 1-4 short lowercase tag strings (e.g. ["italian", "pasta", "quick"]).\n'
            'Return only the JSON object, no markdown fences.\n\n'
            + body.text
        )

        text = (await generate_text(prompt)).strip()

        # Extract JSON from response
        m = re.search(r'\{[\s\S]*\}', text)
        if not m:
            raise ValueError("No JSON found in Azure OpenAI response")
        data = json.loads(m.group())

    except Exception as exc:
        logger.error("Azure OpenAI recipe parse failed: %s", exc)
        raise HTTPException(502, f"AI parsing failed: {exc}")

    # Normalize ingredients
    raw_ingredients = data.get("ingredients") or []
    ingredients = []
    for ing in raw_ingredients:
        if not isinstance(ing, dict):
            continue
        cat = ing.get("category", "Other")
        if cat not in VALID_CATEGORIES:
            cat = "Other"
        ingredients.append({
            "name": str(ing.get("name", "")).strip(),
            "quantity": _normalize_qty(str(ing.get("quantity", ""))),
            "category": cat,
            "section": str(ing.get("section", "")).strip(),
        })

    # Normalize instructions
    instructions = _normalize_instructions(data.get("instructions") or "")

    # Tags: max 4, strings only
    tags = [str(t).lower().strip() for t in (data.get("tags") or []) if t][:4]

    return ParsedRecipe(
        title=str(data.get("title") or "Untitled Recipe").strip(),
        description=str(data.get("description") or "")[:500],
        source_url="",
        prep_minutes=_safe_int(data.get("prep_minutes")),
        cook_minutes=_safe_int(data.get("cook_minutes")),
        servings=_safe_int(data.get("servings"), 2) or 2,
        tags=tags,
        ingredients=ingredients,
        instructions=instructions,
        photo_url="",
    )


# ---------------------------------------------------------------------------
# Recipe CRUD
# ---------------------------------------------------------------------------

@router.post("", response_model=RecipeOut, status_code=201)
async def create_recipe(
    body: RecipeIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    recipe = Recipe(
        user_id=user.id,
        title=body.title,
        description=body.description,
        source_url=body.source_url,
        our_way_notes=body.our_way_notes,
        prep_minutes=body.prep_minutes,
        cook_minutes=body.cook_minutes,
        servings=body.servings,
        tags=body.tags,
        ingredients=[i.model_dump() for i in body.ingredients],
        instructions=body.instructions,
        photo_filename=body.photo_filename,
    )
    db.add(recipe)
    await db.commit()
    await db.refresh(recipe)
    return recipe


@router.get("", response_model=List[RecipeOut])
async def list_recipes(
    q: Optional[str] = Query(None, description="Search by title"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Recipe).where(Recipe.user_id == user.id)
    if q:
        query = query.where(Recipe.title.ilike(f"%{q}%"))
    if tag:
        # JSONB @> operator: check if tags array contains the tag
        query = query.where(Recipe.tags.contains([tag]))
    result = await db.execute(query.order_by(Recipe.created_at.desc()))
    return result.scalars().all()


@router.get("/recommended", response_model=List[RecipeOut])
async def recommended_recipes(
    limit: int = Query(5, ge=1, le=20),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return template recipes matched against the meal_constraints from the user's
    most recent intervention. Falls back to top template recipes if none exists.
    """
    # 1. Get latest intervention's meal_constraints
    await _ensure_template_recipes(db, user_id=user.id)

    intervention_result = await db.execute(
        select(Intervention)
        .where(Intervention.user_id == user.id)
        .order_by(Intervention.created_at.desc())
        .limit(1)
    )
    intervention = intervention_result.scalar_one_or_none()
    constraints: list[str] = (intervention.meal_constraints or []) if intervention else []

    # 2. Query template recipes
    base_query = select(Recipe).where(
        Recipe.is_template.is_(True),
        _template_recipe_scope(user.id),
    )

    if constraints:
        # Score by number of overlapping tags — fetch templates and filter in Python
        # (avoids complex SQL for hackathon simplicity)
        all_templates = (await db.execute(base_query)).scalars().all()
        constraint_set = set(constraints)
        scored = sorted(
            all_templates,
            key=lambda r: len(constraint_set.intersection(set(r.tags or []))),
            reverse=True,
        )
        return scored[:limit]

    result = await db.execute(base_query.order_by(Recipe.id).limit(limit))
    return result.scalars().all()


@router.get("/{recipe_id}", response_model=RecipeOut)
async def get_recipe(
    recipe_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Recipe).where(
            Recipe.id == recipe_id,
            or_(
                Recipe.user_id == user.id,
                (Recipe.is_template.is_(True) & Recipe.user_id.is_(None)),
            ),
        )
    )
    recipe = result.scalar_one_or_none()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe


@router.delete("/{recipe_id}", status_code=204)
async def delete_recipe(
    recipe_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Recipe).where(Recipe.id == recipe_id, Recipe.user_id == user.id))
    recipe = result.scalar_one_or_none()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    await db.delete(recipe)
    await db.commit()


# ---------------------------------------------------------------------------
# Meal plan
# ---------------------------------------------------------------------------

@router.get("/meal-plan/slots", response_model=List[MealPlanSlotOut])
async def list_meal_plan(
    week_start: Optional[str] = Query(None, description="YYYY-MM-DD start of week"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(MealPlanSlot).where(MealPlanSlot.user_id == user.id)
    if week_start:
        from datetime import date, timedelta
        start = date.fromisoformat(week_start)
        end = start + timedelta(days=6)
        query = query.where(MealPlanSlot.plan_date >= start, MealPlanSlot.plan_date <= end)
    result = await db.execute(query.order_by(MealPlanSlot.plan_date, MealPlanSlot.meal_type))
    slots = result.scalars().all()

    # Enrich with recipe summary
    out = []
    for slot in slots:
        d = {
            "id": slot.id, "user_id": slot.user_id, "plan_date": slot.plan_date,
            "meal_type": slot.meal_type, "recipe_id": slot.recipe_id,
            "custom_name": slot.custom_name, "notes": slot.notes, "created_at": slot.created_at,
            "recipe": None,
        }
        if slot.recipe_id:
            r_result = await db.execute(select(Recipe).where(Recipe.id == slot.recipe_id))
            r = r_result.scalar_one_or_none()
            if r:
                d["recipe"] = {"id": r.id, "title": r.title, "description": r.description,
                               "prep_minutes": r.prep_minutes, "cook_minutes": r.cook_minutes,
                               "servings": r.servings, "photo_filename": r.photo_filename}
        out.append(MealPlanSlotOut(**d))
    return out


@router.post("/meal-plan/slots", response_model=MealPlanSlotOut, status_code=201)
async def create_meal_plan_slot(
    body: MealPlanSlotIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from datetime import date
    slot = MealPlanSlot(
        user_id=user.id,
        plan_date=date.fromisoformat(body.plan_date),
        meal_type=body.meal_type,
        recipe_id=body.recipe_id,
        custom_name=body.custom_name,
        notes=body.notes,
    )
    db.add(slot)
    await db.commit()
    await db.refresh(slot)
    return MealPlanSlotOut(
        id=slot.id, user_id=slot.user_id, plan_date=slot.plan_date,
        meal_type=slot.meal_type, recipe_id=slot.recipe_id,
        custom_name=slot.custom_name, notes=slot.notes, created_at=slot.created_at,
    )


@router.delete("/meal-plan/slots/{slot_id}", status_code=204)
async def delete_meal_plan_slot(
    slot_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(MealPlanSlot).where(MealPlanSlot.id == slot_id, MealPlanSlot.user_id == user.id))
    slot = result.scalar_one_or_none()
    if not slot:
        raise HTTPException(404, "Slot not found")
    await db.delete(slot)
    await db.commit()
