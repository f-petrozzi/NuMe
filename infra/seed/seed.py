"""
NüMe seed script.
Creates: 10 demo users across all personas, resources, and persona-appropriate health data.

Usage (from apps/api/ dir with DB running):
    python ../../infra/seed/seed.py
or:
    DATABASE_URL=postgresql+asyncpg://... python seed.py
"""
from __future__ import annotations

import asyncio
import os
import random
import sys
from datetime import date, datetime, timedelta, timezone

# Make sure apps/api is on the path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
API_DIR = os.path.join(SCRIPT_DIR, "..", "..", "apps", "api")
sys.path.insert(0, API_DIR)

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from models import (
    AccessibilityPreferences,
    HealthDailyMetrics,
    HealthSleepSession,
    Resource,
    User,
    UserProfile,
)
from settings import settings


RESOURCES = [
    # student
    {"persona_type": "student", "category": "Mental Health", "title": "Student Counseling Services",
     "description": "Free confidential counseling for enrolled students", "url": ""},
    {"persona_type": "student", "category": "Academic", "title": "Academic Support Center",
     "description": "Tutoring, study skills, and test prep resources", "url": ""},
    {"persona_type": "student", "category": "Wellness", "title": "Campus Recreation Center",
     "description": "Gym, fitness classes, and wellness programs for students", "url": ""},
    {"persona_type": "student", "category": "Crisis", "title": "Crisis Text Line",
     "description": "Text HOME to 741741 for free crisis support 24/7", "url": "https://www.crisistextline.org"},
    # caregiver
    {"persona_type": "caregiver", "category": "Respite", "title": "ARCH National Respite Network",
     "description": "Find respite care services in your area", "url": "https://archrespite.org"},
    {"persona_type": "caregiver", "category": "Support Groups", "title": "Caregiver Action Network",
     "description": "Resources, education, and peer support for caregivers", "url": "https://www.caregiveraction.org"},
    {"persona_type": "caregiver", "category": "Mental Health", "title": "Caregiver Help Desk",
     "description": "1-855-227-3640 — free support line for caregivers", "url": ""},
    {"persona_type": "caregiver", "category": "Wellness", "title": "15-Minute Mindfulness for Caregivers",
     "description": "Quick guided meditations designed for busy caregivers", "url": ""},
    # older_adult
    {"persona_type": "older_adult", "category": "Community", "title": "AARP Community Connections",
     "description": "Connect with neighbors and local volunteer programs", "url": "https://www.aarp.org"},
    {"persona_type": "older_adult", "category": "Fitness", "title": "SilverSneakers",
     "description": "Free gym and fitness classes for Medicare members", "url": "https://www.silversneakers.com"},
    {"persona_type": "older_adult", "category": "Health", "title": "Senior Health & Wellness Hotline",
     "description": "1-800-677-1116 — Eldercare Locator for local resources", "url": ""},
    # accessibility_focused
    {"persona_type": "accessibility_focused", "category": "Technology", "title": "AbilityNet",
     "description": "Free digital accessibility support and technology adaptations", "url": "https://abilitynet.org.uk"},
    {"persona_type": "accessibility_focused", "category": "Legal", "title": "ADA National Network",
     "description": "Information and guidance on ADA rights and accommodations", "url": "https://adata.org"},
]


# 10 demo users across all 4 personas + admin + coordinator
DEMO_USERS = [
    # --- Students (3) ---
    {
        "email": "student@nume.demo",
        "role": "member",
        "health_preset": "stressed_student",
        "profile": {
            "age_range": "18-24", "sex": "male", "height_cm": 175.0, "weight_kg": 70.0,
            "goal": "stress_reduction", "activity_level": "moderate",
            "dietary_style": "omnivore", "allergies": [], "persona_type": "student",
        },
    },
    {
        "email": "student2@nume.demo",
        "role": "member",
        "health_preset": "stressed_student",
        "profile": {
            "age_range": "18-24", "sex": "female", "height_cm": 162.0, "weight_kg": 58.0,
            "goal": "stress_reduction", "activity_level": "low",
            "dietary_style": "vegetarian", "allergies": ["gluten"], "persona_type": "student",
        },
    },
    {
        "email": "student3@nume.demo",
        "role": "member",
        "health_preset": "recovering_student",
        "profile": {
            "age_range": "25-34", "sex": "male", "height_cm": 180.0, "weight_kg": 75.0,
            "goal": "weight_management", "activity_level": "moderate",
            "dietary_style": "omnivore", "allergies": [], "persona_type": "student",
        },
    },
    # --- Caregivers (2) ---
    {
        "email": "caregiver@nume.demo",
        "role": "member",
        "health_preset": "exhausted_caregiver",
        "profile": {
            "age_range": "35-44", "sex": "female", "height_cm": 163.0, "weight_kg": 65.0,
            "goal": "burnout_recovery", "activity_level": "low",
            "dietary_style": "omnivore", "allergies": [], "persona_type": "caregiver",
        },
    },
    {
        "email": "caregiver2@nume.demo",
        "role": "member",
        "health_preset": "exhausted_caregiver",
        "profile": {
            "age_range": "45-54", "sex": "male", "height_cm": 178.0, "weight_kg": 88.0,
            "goal": "burnout_recovery", "activity_level": "low",
            "dietary_style": "omnivore", "allergies": ["dairy"], "persona_type": "caregiver",
        },
    },
    # --- Older adults (2) ---
    {
        "email": "older_adult@nume.demo",
        "role": "member",
        "health_preset": "older_adult_disrupted",
        "profile": {
            "age_range": "65-74", "sex": "female", "height_cm": 158.0, "weight_kg": 62.0,
            "goal": "general_wellness", "activity_level": "low",
            "dietary_style": "omnivore", "allergies": [], "persona_type": "older_adult",
        },
    },
    {
        "email": "older_adult2@nume.demo",
        "role": "member",
        "health_preset": "older_adult_stable",
        "profile": {
            "age_range": "55-64", "sex": "male", "height_cm": 172.0, "weight_kg": 80.0,
            "goal": "fitness_improvement", "activity_level": "moderate",
            "dietary_style": "omnivore", "allergies": [], "persona_type": "older_adult",
        },
    },
    # --- Accessibility focused (1) ---
    {
        "email": "accessibility@nume.demo",
        "role": "member",
        "health_preset": "accessibility_focused",
        "profile": {
            "age_range": "25-34", "sex": "female", "height_cm": 165.0, "weight_kg": 60.0,
            "goal": "stress_reduction", "activity_level": "low",
            "dietary_style": "vegan", "allergies": ["nuts"], "persona_type": "accessibility_focused",
        },
    },
    # --- Staff ---
    {
        "email": "coordinator@nume.demo",
        "role": "coordinator",
        "health_preset": None,
        "profile": None,
    },
    {
        "email": "admin@nume.demo",
        "role": "admin",
        "health_preset": None,
        "profile": None,
    },
]


def _health_params(preset: str, day_index: int) -> dict:
    """
    Return daily health metric values shaped to each persona's narrative.
    day_index=0 is today, day_index=6 is 6 days ago.
    """
    rng = random.Random(preset + str(day_index))  # deterministic per preset+day

    if preset == "stressed_student":
        # Finals week: poor sleep, high stress, low activity
        return dict(
            steps=rng.randint(800, 3500),
            active_calories=rng.randint(80, 200),
            total_calories=rng.randint(1400, 2200),
            resting_hr=rng.randint(68, 82),
            avg_hr=rng.randint(75, 95),
            body_battery_high=rng.randint(30, 55),
            body_battery_low=rng.randint(5, 20),
            stress_avg=rng.randint(55, 85),
            intensity_minutes_moderate=rng.randint(0, 10),
            intensity_minutes_vigorous=0,
            floors_climbed=rng.randint(0, 3),
            spo2_avg=round(rng.uniform(95.0, 97.5), 1),
            hrv_weekly_avg=round(rng.uniform(25.0, 45.0), 1),
            hrv_status="UNBALANCED",
            vo2_max=round(rng.uniform(35.0, 44.0), 1),
            active_minutes=rng.randint(5, 20),
            sleep_hours=round(rng.uniform(3.5, 5.5), 1),
            sleep_score=rng.randint(40, 62),
        )
    elif preset == "recovering_student":
        # Mostly healthy student with moderate stress
        return dict(
            steps=rng.randint(5000, 9000),
            active_calories=rng.randint(250, 450),
            total_calories=rng.randint(1800, 2400),
            resting_hr=rng.randint(60, 72),
            avg_hr=rng.randint(68, 82),
            body_battery_high=rng.randint(60, 85),
            body_battery_low=rng.randint(25, 45),
            stress_avg=rng.randint(30, 55),
            intensity_minutes_moderate=rng.randint(15, 45),
            intensity_minutes_vigorous=rng.randint(0, 15),
            floors_climbed=rng.randint(3, 10),
            spo2_avg=round(rng.uniform(97.0, 99.0), 1),
            hrv_weekly_avg=round(rng.uniform(50.0, 70.0), 1),
            hrv_status="BALANCED",
            vo2_max=round(rng.uniform(42.0, 52.0), 1),
            active_minutes=rng.randint(30, 70),
            sleep_hours=round(rng.uniform(6.5, 8.0), 1),
            sleep_score=rng.randint(70, 88),
        )
    elif preset == "exhausted_caregiver":
        # Caregiver burnout: fragmented sleep, high stress, very low activity
        return dict(
            steps=rng.randint(1500, 4500),
            active_calories=rng.randint(100, 250),
            total_calories=rng.randint(1500, 2100),
            resting_hr=rng.randint(70, 85),
            avg_hr=rng.randint(78, 95),
            body_battery_high=rng.randint(25, 50),
            body_battery_low=rng.randint(5, 18),
            stress_avg=rng.randint(60, 88),
            intensity_minutes_moderate=rng.randint(0, 8),
            intensity_minutes_vigorous=0,
            floors_climbed=rng.randint(0, 4),
            spo2_avg=round(rng.uniform(94.5, 97.0), 1),
            hrv_weekly_avg=round(rng.uniform(20.0, 38.0), 1),
            hrv_status="POOR",
            vo2_max=round(rng.uniform(30.0, 40.0), 1),
            active_minutes=rng.randint(5, 15),
            sleep_hours=round(rng.uniform(4.0, 6.0), 1),
            sleep_score=rng.randint(38, 58),
        )
    elif preset == "older_adult_disrupted":
        # Routine disruption: fragmented sleep, very low steps, low energy
        return dict(
            steps=rng.randint(600, 2500),
            active_calories=rng.randint(60, 180),
            total_calories=rng.randint(1400, 1900),
            resting_hr=rng.randint(62, 75),
            avg_hr=rng.randint(68, 80),
            body_battery_high=rng.randint(35, 60),
            body_battery_low=rng.randint(10, 28),
            stress_avg=rng.randint(35, 65),
            intensity_minutes_moderate=rng.randint(0, 10),
            intensity_minutes_vigorous=0,
            floors_climbed=rng.randint(0, 3),
            spo2_avg=round(rng.uniform(94.0, 97.0), 1),
            hrv_weekly_avg=round(rng.uniform(22.0, 42.0), 1),
            hrv_status="UNBALANCED",
            vo2_max=round(rng.uniform(25.0, 35.0), 1),
            active_minutes=rng.randint(5, 25),
            sleep_hours=round(rng.uniform(4.5, 6.5), 1),
            sleep_score=rng.randint(45, 65),
        )
    elif preset == "older_adult_stable":
        # Stable older adult: moderate routine, decent sleep
        return dict(
            steps=rng.randint(3500, 7000),
            active_calories=rng.randint(180, 350),
            total_calories=rng.randint(1600, 2100),
            resting_hr=rng.randint(60, 70),
            avg_hr=rng.randint(65, 78),
            body_battery_high=rng.randint(55, 80),
            body_battery_low=rng.randint(20, 40),
            stress_avg=rng.randint(20, 45),
            intensity_minutes_moderate=rng.randint(10, 35),
            intensity_minutes_vigorous=rng.randint(0, 10),
            floors_climbed=rng.randint(1, 6),
            spo2_avg=round(rng.uniform(95.0, 98.0), 1),
            hrv_weekly_avg=round(rng.uniform(35.0, 55.0), 1),
            hrv_status="BALANCED",
            vo2_max=round(rng.uniform(28.0, 38.0), 1),
            active_minutes=rng.randint(20, 50),
            sleep_hours=round(rng.uniform(6.0, 7.5), 1),
            sleep_score=rng.randint(65, 82),
        )
    elif preset == "accessibility_focused":
        # Variable energy, moderate stress, low-impact activity
        return dict(
            steps=rng.randint(1000, 4000),
            active_calories=rng.randint(80, 220),
            total_calories=rng.randint(1500, 2000),
            resting_hr=rng.randint(65, 78),
            avg_hr=rng.randint(70, 85),
            body_battery_high=rng.randint(40, 70),
            body_battery_low=rng.randint(10, 30),
            stress_avg=rng.randint(40, 70),
            intensity_minutes_moderate=rng.randint(0, 20),
            intensity_minutes_vigorous=0,
            floors_climbed=rng.randint(0, 3),
            spo2_avg=round(rng.uniform(95.5, 98.5), 1),
            hrv_weekly_avg=round(rng.uniform(30.0, 55.0), 1),
            hrv_status="UNBALANCED",
            vo2_max=round(rng.uniform(28.0, 40.0), 1),
            active_minutes=rng.randint(10, 35),
            sleep_hours=round(rng.uniform(5.5, 7.5), 1),
            sleep_score=rng.randint(55, 78),
        )
    # fallback
    return dict(
        steps=rng.randint(4000, 10000),
        active_calories=rng.randint(200, 500),
        total_calories=rng.randint(1700, 2400),
        resting_hr=rng.randint(58, 72),
        avg_hr=rng.randint(65, 82),
        body_battery_high=rng.randint(60, 90),
        body_battery_low=rng.randint(20, 40),
        stress_avg=rng.randint(20, 55),
        intensity_minutes_moderate=rng.randint(10, 50),
        intensity_minutes_vigorous=rng.randint(0, 20),
        floors_climbed=rng.randint(2, 12),
        spo2_avg=round(rng.uniform(96.5, 99.0), 1),
        hrv_weekly_avg=round(rng.uniform(45.0, 75.0), 1),
        hrv_status="BALANCED",
        vo2_max=round(rng.uniform(38.0, 52.0), 1),
        active_minutes=rng.randint(20, 80),
        sleep_hours=round(rng.uniform(6.5, 8.5), 1),
        sleep_score=rng.randint(68, 90),
    )


async def seed(db: AsyncSession) -> None:
    print("Seeding resources...")
    for r in RESOURCES:
        result = await db.execute(
            select(Resource).where(Resource.title == r["title"], Resource.persona_type == r["persona_type"])
        )
        if not result.scalar_one_or_none():
            db.add(Resource(**r))
    await db.flush()

    print("Creating demo users...")
    created_members = []
    for u_data in DEMO_USERS:
        result = await db.execute(select(User).where(User.email == u_data["email"]))
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                email=u_data["email"],
                role=u_data["role"],
            )
            db.add(user)
            await db.flush()
            print(f"  Created user: {user.email} (id={user.id}, role={user.role})")

            if u_data["profile"]:
                profile = UserProfile(user_id=user.id, **u_data["profile"])
                db.add(profile)
                db.add(AccessibilityPreferences(user_id=user.id))
        else:
            print(f"  User already exists: {user.email}")

        if u_data["health_preset"]:
            created_members.append((user, u_data["health_preset"]))

    await db.flush()

    print("Seeding health data (14 days per member)...")
    today = date.today()
    for user, preset in created_members:
        for i in range(14):
            day = today - timedelta(days=i)
            p = _health_params(preset, i)

            stmt = pg_insert(HealthDailyMetrics).values(
                user_id=user.id,
                metric_date=day,
                steps=p["steps"],
                step_goal=8000,
                active_calories=p["active_calories"],
                total_calories=p["total_calories"],
                resting_hr=p["resting_hr"],
                avg_hr=p["avg_hr"],
                body_battery_high=p["body_battery_high"],
                body_battery_low=p["body_battery_low"],
                stress_avg=p["stress_avg"],
                intensity_minutes_moderate=p["intensity_minutes_moderate"],
                intensity_minutes_vigorous=p["intensity_minutes_vigorous"],
                floors_climbed=p["floors_climbed"],
                spo2_avg=p["spo2_avg"],
                hrv_weekly_avg=p["hrv_weekly_avg"],
                hrv_status=p["hrv_status"],
                vo2_max=p["vo2_max"],
                active_minutes=p["active_minutes"],
                raw_json={"seeded": True, "preset": preset},
                synced_at=datetime.now(timezone.utc),
            ).on_conflict_do_nothing(constraint="uq_daily_metrics_user_date")
            await db.execute(stmt)

            sleep_seconds = int(p["sleep_hours"] * 3600)
            stmt = pg_insert(HealthSleepSession).values(
                user_id=user.id,
                sleep_date=day,
                sleep_start="22:30",
                sleep_end="06:30",
                duration_seconds=sleep_seconds,
                deep_seconds=int(sleep_seconds * 0.2),
                light_seconds=int(sleep_seconds * 0.5),
                rem_seconds=int(sleep_seconds * 0.25),
                awake_seconds=int(sleep_seconds * 0.05),
                sleep_score=p["sleep_score"],
                avg_spo2=p["spo2_avg"],
                avg_respiration=round(random.uniform(13.0, 17.0), 1),
                raw_json={"seeded": True, "preset": preset},
                synced_at=datetime.now(timezone.utc),
            ).on_conflict_do_nothing(constraint="uq_sleep_sessions_user_date")
            await db.execute(stmt)

    await db.commit()
    print(f"Seed complete. {len(DEMO_USERS)} users, {len(created_members)} with health data (14 days each).")


async def main():
    engine = create_async_engine(settings.database_url, echo=False)
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    from models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        await seed(db)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
