from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.entities import Role
from models import roles


class RoleRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def get_by_name(self, *, name: str) -> Role | None:
        row = (await self.session.execute(select(roles).where(roles.c.name == name))).mappings().first()
        return Role.model_validate(dict(row)) if row else None
