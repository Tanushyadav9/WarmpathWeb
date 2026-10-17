"""
backend/conftest.py - Root pytest fixtures for all tests across backend/tests and backend/app/modules.
"""

import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Use a test SQLite file
TEST_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_warmpath.db"))
TEST_DATABASE_URL = f"sqlite+aiosqlite:///{TEST_DB_PATH}"

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["ENVIRONMENT"] = "test"

from app.core.config import settings
settings.DATABASE_URL = TEST_DATABASE_URL
settings.ENVIRONMENT = "test"

import app.core.db as db_module
from app.core.db import Base, get_db
from app.main import app

# Import all models so Base.metadata knows about them
import app.modules.availability.models
import app.modules.matching.models
import app.modules.sessions.models
import app.modules.trust.models
import app.modules.ratings.models

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
test_session_maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

db_module.engine = test_engine
db_module.async_session_maker = test_session_maker


@pytest_asyncio.fixture(scope="session", autouse=True)
async def init_test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except Exception:
            pass


@pytest_asyncio.fixture
async def db_session():
    async with test_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def async_client():
    async def override_get_db():
        async with test_session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
