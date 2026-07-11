from pydantic import Field

from .base import Entity, TimestampMixin


class User(Entity, TimestampMixin):
    email: str
    password: str
    session_version: int = Field(default=1, ge=1)
