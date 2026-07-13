from datetime import datetime
from uuid import uuid4

import jwt
import pytest

from core.exceptions import InvalidCredentials
from core.services.oauth_state import OAuthStateService


class MemoryStore:
    def __init__(self) -> None:
        self.nonces: dict[str, datetime] = {}

    async def consume(self, *, nonce: str, expires_at: datetime, now: datetime) -> bool:
        self.nonces = {key: expiry for key, expiry in self.nonces.items() if expiry > now}
        if nonce in self.nonces:
            return False
        self.nonces[nonce] = expires_at
        return True


@pytest.mark.asyncio
async def test_state_round_trip_replay_tampering_and_purpose() -> None:
    secret = "test-secret-that-is-at-least-thirty-two-bytes"
    store = MemoryStore()
    service = OAuthStateService(secret=secret, algorithm="HS256", ttl_minutes=10, store=store)
    user_id = uuid4()
    state = service.issue(user_id=user_id)
    assert await service.consume(state=state) == user_id
    with pytest.raises(InvalidCredentials, match="использован"):
        await service.consume(state=state)
    with pytest.raises(InvalidCredentials):
        await service.consume(state=state + "x")
    wrong = jwt.encode({"sub": str(user_id), "purpose": "wrong", "nonce": "n"}, secret, algorithm="HS256")
    with pytest.raises(InvalidCredentials, match="назначение"):
        await service.consume(state=wrong)


@pytest.mark.asyncio
async def test_expired_state() -> None:
    secret = "test-secret-that-is-at-least-thirty-two-bytes"
    service = OAuthStateService(secret=secret, algorithm="HS256", ttl_minutes=10, store=MemoryStore())
    expired = jwt.encode(
        {"sub": str(uuid4()), "purpose": "hh-oauth", "nonce": "n", "exp": 1}, secret, algorithm="HS256"
    )
    with pytest.raises(InvalidCredentials, match="просроченный"):
        await service.consume(state=expired)


@pytest.mark.asyncio
async def test_shared_store_blocks_replay_across_instances_and_restart() -> None:
    secret = "test-secret-that-is-at-least-thirty-two-bytes"
    store = MemoryStore()
    first = OAuthStateService(secret=secret, algorithm="HS256", ttl_minutes=10, store=store)
    state = first.issue(user_id=uuid4())
    await first.consume(state=state)
    restarted_worker = OAuthStateService(secret=secret, algorithm="HS256", ttl_minutes=10, store=store)
    with pytest.raises(InvalidCredentials, match="использован"):
        await restarted_worker.consume(state=state)
