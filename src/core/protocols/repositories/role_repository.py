from typing import Protocol

from core.entities import Role


class RoleRepositoryProtocol(Protocol):
    async def get_by_name(self, *, name: str) -> Role | None: ...
