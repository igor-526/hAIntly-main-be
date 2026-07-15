from typing import Annotated
from uuid import UUID

from fastapi import Cookie, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ClientError, InvalidCredentials
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
    return AuthService(
        users=users,
        roles=roles,
        security=security,
        service_key=settings.main_be_service_key.get_secret_value(),
    )


async def get_current_user(
    service: Annotated[AuthService, Depends(get_auth_service)],
    access_token: Annotated[str | None, Cookie()] = None,
    authorization: Annotated[str | None, Header()] = None,
    x_user_id: Annotated[str | None, Header()] = None,
) -> UserOut:
    if authorization is not None:
        scheme, separator, service_key = authorization.partition(" ")
        if scheme != "Bearer" or separator != " " or not service_key or x_user_id is None:
            raise InvalidCredentials()
        return await service.current_service_user(service_key=service_key, user_id=x_user_id)
    if x_user_id is not None:
        raise InvalidCredentials()
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


async def get_hh_user_id(
    user: Annotated[UserOut, Depends(get_current_user)],
    users: Annotated[UserRepositoryProtocol, Depends(get_user_repository)],
) -> str:
    return await resolve_hh_user_id(user)


async def resolve_hh_user_id(user: UserOut) -> str:
    from repositories import UserRepository
    from utils.database import SessionFactory
    async with SessionFactory() as session:
        repo = UserRepository(session=session)
        db_user = await repo.get_by_id(user_id=user.id)
        if db_user is None or db_user.active_hh_account_id is None:
            raise ClientError("Не выбран HH-аккаунт. Привяжите и выберите HH-аккаунт в настройках")
        profiles = ProfileServiceClient(
            base_url=str(settings.profile_service_url), timeout_seconds=settings.profile_service_timeout_seconds
        )
        account = await profiles.get_account(user_id=user.id, account_id=db_user.active_hh_account_id)
        if account is None:
            raise ClientError("Выбранный HH-аккаунт не найден")
        return account.hh_user_id


async def get_hh_account_id(
    user: Annotated[UserOut, Depends(get_current_user)],
    users: Annotated[UserRepositoryProtocol, Depends(get_user_repository)],
) -> UUID:
    db_user = await users.get_by_id(user_id=user.id)
    if db_user is None or db_user.active_hh_account_id is None:
        raise ClientError("Не выбран HH-аккаунт. Привяжите и выберите HH-аккаунт в настройках")
    return db_user.active_hh_account_id
