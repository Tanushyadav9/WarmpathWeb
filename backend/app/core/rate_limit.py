import time
from typing import Dict, List, Optional
from fastapi import Request
from app.core.config import settings
from app.core.errors import AppError
from app.core.redis import get_redis

_in_memory_rate_limits: Dict[str, List[float]] = {}


def get_daily_limit_for_trust_level(trust_level: str) -> int:
    level = trust_level.lower()
    if level == "restricted":
        return settings.REQUEST_LIMIT_RESTRICTED
    elif level == "established":
        return settings.REQUEST_LIMIT_ESTABLISHED
    elif level == "verified":
        return settings.REQUEST_LIMIT_VERIFIED
    return settings.REQUEST_LIMIT_NEW


async def check_rate_limit(user_id: str, trust_level: str = "new", action: str = "request"):
    key = f"ratelimit:{user_id}:{action}"
    limit = get_daily_limit_for_trust_level(trust_level)

    try:
        r = await get_redis()
        current = await r.incr(key)
        if current == 1:
            await r.expire(key, 86400)

        if current > limit:
            raise AppError(
                code="rate_limit_exceeded",
                message=f"Daily limit of {limit} {action}s exceeded for trust level '{trust_level}'.",
                status_code=429,
                details={"limit": limit, "current": current, "trust_level": trust_level},
            )
    except AppError:
        raise
    except Exception:
        # Fallback to in-memory window when Redis is unavailable
        now = time.time()
        window = 86400
        timestamps = _in_memory_rate_limits.get(key, [])
        valid_timestamps = [t for t in timestamps if now - t < window]
        valid_timestamps.append(now)
        _in_memory_rate_limits[key] = valid_timestamps

        current = len(valid_timestamps)
        if current > limit:
            raise AppError(
                code="rate_limit_exceeded",
                message=f"Daily limit of {limit} {action}s exceeded for trust level '{trust_level}'.",
                status_code=429,
                details={"limit": limit, "current": current, "trust_level": trust_level},
            )

