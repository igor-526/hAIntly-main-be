from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from jwt import InvalidTokenError

from core.exceptions import InvalidCredentials
from core.protocols import OAuthStateStoreProtocol


class OAuthStateService:
    purpose = "hh-oauth"

    def __init__(self, *, secret: str, algorithm: str, ttl_minutes: int, store: OAuthStateStoreProtocol) -> None:
        self.secret = secret
        self.algorithm = algorithm
        self.ttl = timedelta(minutes=ttl_minutes)
        self.store = store

    def issue(self, *, user_id: UUID) -> str:
        now = datetime.now(UTC)
        return jwt.encode(
            {"sub": str(user_id), "purpose": self.purpose, "nonce": str(uuid4()), "iat": now, "exp": now + self.ttl},
            self.secret,
            algorithm=self.algorithm,
        )

    async def consume(self, *, state: str) -> UUID:
        try:
            payload = jwt.decode(state, self.secret, algorithms=[self.algorithm])
            if payload.get("purpose") != self.purpose:
                raise InvalidCredentials("Некорректное назначение OAuth state")
            user_id = UUID(str(payload["sub"]))
            nonce = str(payload["nonce"])
            expires_at = datetime.fromtimestamp(float(payload["exp"]), tz=UTC)
        except InvalidCredentials:
            raise
        except (InvalidTokenError, KeyError, TypeError, ValueError) as exc:
            raise InvalidCredentials("Недействительный или просроченный OAuth state") from exc
        if not await self.store.consume(nonce=nonce, expires_at=expires_at, now=datetime.now(UTC)):
            raise InvalidCredentials("OAuth state уже использован")
        return user_id
