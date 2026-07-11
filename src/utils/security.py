from datetime import UTC, datetime, timedelta

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash

from core.exceptions import InvalidCredentials
from settings import settings


class Security:
    def __init__(self) -> None:
        self.password_hash = PasswordHash.recommended()

    def hash_password(self, password: str) -> str:
        return self.password_hash.hash(password)

    def verify_password(self, password: str, password_hash: str) -> bool:
        return self.password_hash.verify(password, password_hash)

    def create_access_token(self, *, subject: str, session_version: int) -> str:
        return self._create_token(
            subject=subject,
            session_version=session_version,
            token_type="access",
            expires=timedelta(minutes=settings.access_token_minutes),
        )

    def create_refresh_token(self, *, subject: str, session_version: int) -> str:
        return self._create_token(
            subject=subject,
            session_version=session_version,
            token_type="refresh",
            expires=timedelta(days=settings.refresh_token_days),
        )

    def _create_token(self, *, subject: str, session_version: int, token_type: str, expires: timedelta) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": subject,
            "session_version": session_version,
            "type": token_type,
            "iat": now,
            "exp": now + expires,
        }
        return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)

    def decode_token(self, token: str) -> dict[str, object]:
        try:
            return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        except InvalidTokenError as exc:
            raise InvalidCredentials("Недействительный или просроченный токен") from exc
