import asyncio
import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import insert, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from models import oauth_state_nonces
from repositories import OAuthStateRepository

DEFAULT_TEST_DATABASE_URL = "postgresql+asyncpg://main_be_user:main_be_password@127.0.0.1:5451/main_oauth_clean"


@pytest_asyncio.fixture
async def postgres_engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(os.getenv("TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL), pool_pre_ping=True)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(oauth_state_nonces.create, checkfirst=True)
            await connection.execute(oauth_state_nonces.delete())
    except (OSError, OperationalError) as exc:
        await engine.dispose()
        pytest.skip(f"PostgreSQL test database unavailable: {exc}")
    yield engine
    async with engine.begin() as connection:
        await connection.execute(oauth_state_nonces.delete())
    await engine.dispose()


async def consume_and_commit(
    factory: async_sessionmaker[AsyncSession], *, nonce: str, expires_at: datetime, now: datetime
) -> bool:
    async with factory() as session:
        result = await OAuthStateRepository(session=session).consume(nonce=nonce, expires_at=expires_at, now=now)
        await session.commit()
        return result


@pytest.mark.asyncio
async def test_concurrent_independent_sessions_allow_exactly_one_consume(postgres_engine: AsyncEngine) -> None:
    factory = async_sessionmaker(postgres_engine, expire_on_commit=False)
    now = datetime.now(UTC)
    results = await asyncio.gather(
        consume_and_commit(factory, nonce="concurrent", expires_at=now + timedelta(minutes=10), now=now),
        consume_and_commit(factory, nonce="concurrent", expires_at=now + timedelta(minutes=10), now=now),
    )
    assert sorted(results) == [False, True]


@pytest.mark.asyncio
async def test_replay_is_rejected_by_new_repository_and_session_after_restart(postgres_engine: AsyncEngine) -> None:
    factory = async_sessionmaker(postgres_engine, expire_on_commit=False)
    now = datetime.now(UTC)
    assert await consume_and_commit(factory, nonce="restart", expires_at=now + timedelta(minutes=10), now=now)
    assert not await consume_and_commit(factory, nonce="restart", expires_at=now + timedelta(minutes=10), now=now)


@pytest.mark.asyncio
async def test_expired_nonce_is_cleaned_and_storage_key_can_be_reused(postgres_engine: AsyncEngine) -> None:
    factory = async_sessionmaker(postgres_engine, expire_on_commit=False)
    now = datetime.now(UTC)
    async with factory() as session:
        await session.execute(
            insert(oauth_state_nonces).values(nonce="expired", expires_at=now - timedelta(seconds=1))
        )
        await session.commit()
    assert await consume_and_commit(factory, nonce="expired", expires_at=now + timedelta(minutes=10), now=now)
    async with factory() as session:
        rows = (await session.execute(select(oauth_state_nonces))).mappings().all()
    assert [(row["nonce"], row["expires_at"] > now) for row in rows] == [("expired", True)]
    assert not await consume_and_commit(factory, nonce="expired", expires_at=now + timedelta(minutes=10), now=now)
