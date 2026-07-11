from sqlalchemy.dialects.postgresql import insert

from core.seeds.roles import ROLE_SEEDS
from models import roles
from utils.database import SessionFactory


async def seed_roles() -> None:
    async with SessionFactory.begin() as session:
        for name, role_id in ROLE_SEEDS.items():
            statement = (
                insert(roles).values(id=role_id, name=name).on_conflict_do_nothing(index_elements=[roles.c.name])
            )
            await session.execute(statement)
