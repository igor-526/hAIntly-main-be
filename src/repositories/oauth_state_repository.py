from datetime import datetime

from sqlalchemy import delete, insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models import oauth_state_nonces


class OAuthStateRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def consume(self, *, nonce: str, expires_at: datetime, now: datetime) -> bool:
        await self.session.execute(delete(oauth_state_nonces).where(oauth_state_nonces.c.expires_at <= now))
        try:
            async with self.session.begin_nested():
                await self.session.execute(insert(oauth_state_nonces).values(nonce=nonce, expires_at=expires_at))
        except IntegrityError:
            return False
        return True
