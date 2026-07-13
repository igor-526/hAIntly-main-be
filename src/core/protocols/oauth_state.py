from datetime import datetime
from typing import Protocol


class OAuthStateStoreProtocol(Protocol):
    async def consume(self, *, nonce: str, expires_at: datetime, now: datetime) -> bool: ...
