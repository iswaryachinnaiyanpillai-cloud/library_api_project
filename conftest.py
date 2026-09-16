import pytest
import pytest_asyncio

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from database import Base
from main import app, get_db


# =========================================================
# ISOLATED TEST DATABASE
# =========================================================

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={
        "check_same_thread": False,
    },
    poolclass=StaticPool,
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# =========================================================
# TEST DATABASE SETUP
# =========================================================

@pytest_asyncio.fixture
async def test_db():
    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    yield

    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)


# =========================================================
# OVERRIDE FASTAPI DATABASE DEPENDENCY
# =========================================================

@pytest_asyncio.fixture(autouse=True)
async def override_database(test_db):

    async def override_get_db():
        async with TestSessionLocal() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    yield

    app.dependency_overrides.clear()