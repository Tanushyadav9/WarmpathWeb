"""
backend/tests/conftest.py - Pytest fixtures with SQLite test database.
"""

import os
# Ensure SQLite is used for tests before any app modules initialize
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///warmpath_test.db"
os.environ["ENVIRONMENT"] = "test"

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.core.db import Base, engine, async_session_maker, get_db
from app.main import app as fastapi_app

# Import all models so Base.metadata knows about them
import app.modules.availability.models
import app.modules.matching.models
import app.modules.sessions.models
import app.modules.trust.models
import app.modules.ratings.models
import app.modules.credits.models
import app.modules.institution.models


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    if os.path.exists("warmpath_test.db"):
        try:
            os.remove("warmpath_test.db")
        except Exception:
            pass


@pytest_asyncio.fixture
async def db_session():
    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def async_client():
    async def override_get_db():
        async with async_session_maker() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    fastapi_app.dependency_overrides.clear()
