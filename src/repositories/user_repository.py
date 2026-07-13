from uuid import UUID, uuid4

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from core.entities import Role, User
from models import roles, user_roles, users


class UserRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, *, user_id: UUID) -> User | None:
        return await self._get(users.c.id == user_id)

    async def get_by_email(self, *, email: str) -> User | None:
        return await self._get(users.c.email == email)

    async def _get(self, condition: ColumnElement[bool]) -> User | None:
        row = (await self.session.execute(select(users).where(condition))).mappings().first()
        return User.model_validate(dict(row)) if row else None

    async def create(self, *, user: User) -> User:
        values = user.model_dump(exclude={"updated_at"})
        row = (await self.session.execute(insert(users).values(**values).returning(users))).mappings().one()
        return User.model_validate(dict(row))

    async def get_roles(self, *, user_id: UUID) -> list[Role]:
        query = (
            select(roles).join(user_roles, roles.c.id == user_roles.c.role_id).where(user_roles.c.user_id == user_id)
        )
        rows = (await self.session.execute(query)).mappings().all()
        return [Role.model_validate(dict(row)) for row in rows]

    async def assign_role(self, *, user_id: UUID, role_id: UUID) -> None:
        await self.session.execute(insert(user_roles).values(id=uuid4(), user_id=user_id, role_id=role_id))

    async def set_active_hh_account(self, *, user_id: UUID, account_id: UUID | None) -> None:
        await self.session.execute(update(users).where(users.c.id == user_id).values(active_hh_account_id=account_id))
