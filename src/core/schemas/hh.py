from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict, Field

from .base import Schema


class HHAccount(Schema):
    id: UUID
    hh_user_id: str
    display_name: str | None
    email: str | None
    avatar_url: str | None
    created_at: datetime
    updated_at: datetime | None


class HHAccounts(Schema):
    accounts: list[HHAccount]
    active_account_id: UUID | None


class AuthorizationURL(Schema):
    authorization_url: str


class OAuthCallback(Schema):
    model_config = ConfigDict(extra="forbid")
    state: str = Field(min_length=1, max_length=4096)
    code: str | None = Field(default=None, min_length=1, max_length=4096)
    error: str | None = Field(default=None, max_length=255)


class OAuthResult(Schema):
    success: bool
    account: HHAccount | None = None
    message: str | None = None


class SelectAccount(Schema):
    model_config = ConfigDict(extra="forbid")
    account_id: UUID


class ActiveAccount(Schema):
    active_account_id: UUID
