"""
backend/app/core/health.py - Health and readiness probes with detailed diagnostic metrics.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import settings
from app.core.db import async_session_maker
from app.core.redis import get_redis

router = APIRouter(tags=["health"])


@router.get("/healthz", summary="Liveness probe")
@router.get("/health", summary="Liveness probe (alias)")
async def health_check():
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/readyz", summary="Readiness probe")
@router.get("/ready", summary="Readiness probe (alias)")
async def readiness_check():
    # Verify Database connectivity
    db_ok = False
    try:
        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        db_ok = False

    # Verify Redis connectivity
    redis_ok = False
    try:
        r = await get_redis()
        await r.ping()
        redis_ok = True
    except Exception:
        redis_ok = False

    # Overall system readiness requires database connectivity
    overall_ok = db_ok
    status_code = status.HTTP_200_OK if overall_ok else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if overall_ok else "not_ready",
            "service": settings.PROJECT_NAME,
            "database": "ok" if db_ok else "unreachable",
            "redis": "ok" if redis_ok else "unreachable",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
