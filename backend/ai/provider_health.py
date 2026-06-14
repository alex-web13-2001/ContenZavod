"""Circuit breaker for the KIE image-generation provider.

Why: when KIE runs out of credits or its network is unreachable, every cover
generation fails. Without a breaker, two retry mechanisms (Celery max_retries +
the periodic autopilot_retry_covers sweep) pile up and hammer the API hundreds
of times — on 2026-06-14 that turned 21 real covers into ~2500 attempts and
burned all credits overnight. The breaker trips on a hard provider failure and
makes all cover work short-circuit (no API call) until it expires.

Backed by Redis so the state is shared across all worker processes. If Redis is
unavailable the helpers fail OPEN (breaker considered closed) — we never block
on the breaker itself.
"""

import structlog

from app.config import get_settings

log = structlog.get_logger()
settings = get_settings()

_BREAKER_KEY = "img_gen:circuit_open"
# How long to stop hitting the provider after a hard failure. Credits/outages
# don't resolve in seconds; 30 min avoids burning the whole window on retries
# while still recovering automatically once the issue is fixed.
COOLDOWN_SECONDS = 1800

# Substrings in an error that mean "stop trying" (systemic, not per-request).
HARD_FAILURE_MARKERS = (
    "credits insufficient",
    "insufficient",
    "errno -2",            # DNS / name resolution
    "errno -5",            # no address
    "certificate_verify_failed",
    "connection refused",
    "temporarily unavailable",
)


def _redis():
    """Best-effort Redis client; None if unavailable."""
    try:
        import redis

        return redis.Redis.from_url(settings.redis_url, socket_timeout=2)
    except Exception:
        return None


def is_hard_failure(error: str) -> bool:
    """True if the error means the provider is systemically down (don't retry)."""
    e = (error or "").lower()
    return any(m in e for m in HARD_FAILURE_MARKERS)


def trip_breaker(reason: str = "") -> None:
    """Open the breaker for COOLDOWN_SECONDS (idempotent; refreshes the window)."""
    r = _redis()
    if r is None:
        return
    try:
        r.setex(_BREAKER_KEY, COOLDOWN_SECONDS, reason[:200] or "tripped")
        log.warning("img_gen.circuit_tripped", reason=reason[:120], cooldown_s=COOLDOWN_SECONDS)
    except Exception:
        pass


def is_breaker_open() -> bool:
    """True if cover generation should short-circuit right now."""
    r = _redis()
    if r is None:
        return False  # fail open — never block on the breaker itself
    try:
        return r.exists(_BREAKER_KEY) > 0
    except Exception:
        return False


class ImageProviderDown(Exception):
    """Raised when a cover task is skipped because the breaker is open."""
    pass
