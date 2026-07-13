from uuid import UUID

from pydantic import Field

from .base import Entity, TimestampMixin


class User(Entity, TimestampMixin):
    email: str
    password: str
    session_version: int = Field(default=1, ge=1)
    active_hh_account_id: UUID | None = None
