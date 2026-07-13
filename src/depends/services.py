from typing import Annotated

from fastapi import Cookie, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import InvalidCredentials
from core.protocols.repositories import RoleRepositoryProtocol, UserRepositoryProtocol
from core.schemas import UserOut
from core.services import AuthService, HHAccountsService, OAuthStateService
from depends.repositories import get_role_repository, get_user_repository
from infrastructure import ProfileServiceClient
from repositories import OAuthStateRepository
from settings import settings
from utils.database import get_session
from utils.security import Security


def get_security() -> Security:
    return Security()


async def get_auth_service(
    users: Annotated[UserRepositoryProtocol, Depends(get_user_repository)],
    roles: Annotated[RoleRepositoryProtocol, Depends(get_role_repository)],
    security: Annotated[Security, Depends(get_security)],
) -> AuthService:
    return AuthService(users=users, roles=roles, security=security)


async def get_current_user(
    service: Annotated[AuthService, Depends(get_auth_service)],
    access_token: Annotated[str | None, Cookie()] = None,
) -> UserOut:
    if access_token is None:
        raise InvalidCredentials("Требуется аутентификация")
    return await service.current_user(token=access_token)


async def get_oauth_state_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OAuthStateService:
    return OAuthStateService(
        secret=settings.secret_key,
        algorithm=settings.jwt_algorithm,
        ttl_minutes=settings.oauth_state_minutes,
        store=OAuthStateRepository(session=session),
    )


async def get_hh_accounts_service(
    users: Annotated[UserRepositoryProtocol, Depends(get_user_repository)],
) -> HHAccountsService:
    return HHAccountsService(
        users=users,
        profiles=ProfileServiceClient(
            base_url=str(settings.profile_service_url), timeout_seconds=settings.profile_service_timeout_seconds
        ),
    )
