"""
AI endpoint rate limiting and emergency kill switch.

Enforcement model
-----------------
- Check-before-charge: counters are only incremented for admitted requests.
- Multi-bucket atomicity: all bucket increments run in one DB transaction.
- Fail mode: CLOSED. If the accounting DB check fails, the request is denied (503).
- Kill switch: RATE_LIMIT_ENABLED=false bypasses rate checks (dev/testing only).

This module exposes an explicit `enforce_ai_rate_limit()` helper instead of
hiding accounting inside a FastAPI dependency. That lets routes validate cheap
4xx cases first so obviously invalid requests do not burn quota.
"""
from __future__ import annotations

import hashlib
import ipaddress
import logging
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from settings import settings

logger = logging.getLogger(__name__)

COST_HEAVY = 5
COST_LIGHT = 1


# ── Emergency brake ────────────────────────────────────────────────────────

async def require_ai_enabled() -> None:
    """
    Hard stop for all AI-triggering endpoints.
    Inject on AI-triggering routes before any expensive work.
    Controlled by AI_ENDPOINTS_ENABLED env var; requires process restart to change.
    """
    if not settings.ai_endpoints_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "ai_disabled", "message": "AI features are temporarily disabled."},
        )


# ── IP extraction ──────────────────────────────────────────────────────────

def _trusted_proxy_networks() -> tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]:
    networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    for raw_value in settings.rate_limit_trusted_proxy_ips.split(","):
        value = raw_value.strip()
        if not value:
            continue
        try:
            networks.append(ipaddress.ip_network(value, strict=False))
        except ValueError:
            logger.warning("Ignoring invalid RATE_LIMIT_TRUSTED_PROXY_IPS entry: %s", value)
    return tuple(networks)


def _is_private_or_loopback(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
        return addr.is_private or addr.is_loopback
    except ValueError:
        return True  # Unparseable → treat as private, skip IP check


def _is_trusted_proxy(ip: str | None) -> bool:
    if not ip:
        return False
    try:
        candidate = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(candidate in network for network in _trusted_proxy_networks())


def _extract_real_ip(request: Request) -> str | None:
    """
    Returns the real client IP, or None if the IP limit should be skipped.

    Trust model:
    - If request.client.host is in TRUSTED_PROXY_IPS → request came through a
      known proxy (CF Tunnel, nginx). Extract real IP from CF-Connecting-IP, then
      X-Forwarded-For[0].
    - Otherwise → direct connection. Use request.client.host as-is.
    - If the resolved IP is private/loopback → return None (skip IP limit).

    This ensures proxy headers are only trusted when the app can verify the
    connection came through a known proxy. If the app is ever directly exposed,
    request.client.host is used without trusting any forwarded headers.
    """
    direct_host = request.client.host if request.client else None

    if _is_trusted_proxy(direct_host):
        cf = request.headers.get("cf-connecting-ip", "").strip()
        if cf:
            return None if _is_private_or_loopback(cf) else cf
        xff = request.headers.get("x-forwarded-for", "").strip()
        if xff:
            first = xff.split(",")[0].strip()
            return None if _is_private_or_loopback(first) else first
        # Trusted proxy but no forwarded header present → skip IP check
        return None

    # Direct connection (no trusted proxy)
    if not direct_host or _is_private_or_loopback(direct_host):
        return None
    return direct_host


def _hash_ip(ip: str) -> str:
    """SHA-256, first 8 hex chars. Enough entropy for bucketing; limits privacy exposure."""
    return hashlib.sha256(ip.encode()).hexdigest()[:8]


# ── Time helpers ───────────────────────────────────────────────────────────

def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _hour_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H")


def _secs_until_midnight() -> int:
    now = datetime.now(timezone.utc)
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return max(int((tomorrow - now).total_seconds()), 1)


def _secs_until_next_hour() -> int:
    now = datetime.now(timezone.utc)
    next_h = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    return max(int((next_h - now).total_seconds()), 1)


# ── Atomic conditional upsert ──────────────────────────────────────────────

# Increments the counter only if the new value would not exceed the limit.
# Returns the new count if allowed; 0 rows if the limit would be exceeded.
# Must be called inside an open transaction — rollback on exception undoes all
# increments from that transaction.
_CONDITIONAL_UPSERT = text("""
    INSERT INTO ai_rate_counters (bucket_key, count)
    VALUES (:key, :units)
    ON CONFLICT (bucket_key) DO UPDATE
      SET count = ai_rate_counters.count + :units
      WHERE ai_rate_counters.count + :units <= :limit
    RETURNING count
""")


async def _try_increment(db: AsyncSession, key: str, units: int, limit: int) -> bool:
    """
    Atomically increments the counter for `key` by `units` if count + units <= limit.
    Returns True (allowed) or False (limit exceeded — nothing was incremented).
    PostgreSQL row-level locking on the upsert target serializes concurrent requests
    to the same bucket, eliminating the TOCTOU window.
    """
    result = await db.execute(_CONDITIONAL_UPSERT, {"key": key, "units": units, "limit": limit})
    return result.scalar_one_or_none() is not None


def _build_rate_limit_buckets(*, request: Request, user: User, cost_units: int) -> list[tuple]:
    today = _today_utc()
    hour = _hour_utc()

    # Ordered bucket list: IP checked first (cheapest guard), global last.
    # Format: (bucket_key, units, limit, limit_type, retry_fn, message)
    buckets: list[tuple] = []

    real_ip = _extract_real_ip(request)
    if real_ip:
        buckets.append((
            f"ip:{_hash_ip(real_ip)}:{today}",
            cost_units,
            settings.rate_limit_ip_daily_units,
            "ip_daily",
            _secs_until_midnight,
            "Too many requests from this network today. Resets at midnight UTC.",
        ))

    buckets += [
        (
            f"u:{user.id}:h:{hour}",
            cost_units,
            settings.rate_limit_user_hourly_units,
            "user_hourly",
            _secs_until_next_hour,
            "Hourly limit reached.",
        ),
        (
            f"u:{user.id}:{today}",
            cost_units,
            settings.rate_limit_user_daily_units,
            "user_daily",
            _secs_until_midnight,
            "Daily limit reached. Resets at midnight UTC.",
        ),
        (
            f"g:{today}",
            cost_units,
            settings.rate_limit_global_daily_units,
            "global_daily",
            _secs_until_midnight,
            "Demo capacity reached for today. Resets at midnight UTC.",
        ),
    ]
    return buckets


async def enforce_ai_rate_limit(
    *,
    request: Request,
    user: User,
    db: AsyncSession,
    cost_units: int,
) -> None:
    """
    Enforce per-IP, per-user, and global AI admission limits.

    Call this after auth and any cheap route validation that can reject before
    model work begins. `db` must come from the dedicated rate-limit session
    dependency rather than the request's main ORM session.
    """
    assert cost_units > 0, "cost_units must be positive"

    if not settings.rate_limit_enabled:
        return

    if db.in_transaction():
        raise RuntimeError("Rate limit accounting requires an isolated session")

    buckets = _build_rate_limit_buckets(request=request, user=user, cost_units=cost_units)

    try:
        async with db.begin():
            for key, units, limit, limit_type, retry_fn, message in buckets:
                allowed = await _try_increment(db, key, units, limit)
                if not allowed:
                    retry = retry_fn()
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail={
                            "error": "rate_limited",
                            "limit_type": limit_type,
                            "retry_after_seconds": retry,
                            "message": message,
                        },
                        headers={"Retry-After": str(retry)},
                    )
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "Rate limit DB check failed for user=%s endpoint=%s — denying request (fail-closed)",
            user.id,
            request.url.path,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "rate_limit_unavailable",
                "message": "Service temporarily unavailable. Please try again shortly.",
            },
        )
