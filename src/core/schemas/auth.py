from uuid import UUID

from pydantic import ConfigDict, EmailStr, Field

from .base import Schema


class RegisterData(Schema):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginData(Schema):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class AuthTokens(Schema):
    access_token: str
    refresh_token: str


class RoleOut(Schema):
    id: UUID
    name: str


class UserOut(Schema):
    id: UUID
    email: EmailStr
    roles: list[RoleOut] = Field(default_factory=list)
