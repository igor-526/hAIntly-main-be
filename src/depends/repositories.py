from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.protocols.repositories import RoleRepositoryProtocol, UserRepositoryProtocol
from repositories import RoleRepository, UserRepository
from utils.database import get_session


async def get_user_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserRepositoryProtocol:
    return UserRepository(session=session)


async def get_role_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RoleRepositoryProtocol:
    return RoleRepository(session=session)
