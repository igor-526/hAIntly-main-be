from typing import Annotated

from fastapi import Depends

from core.exceptions import ForbiddenError
from core.schemas import UserOut
from core.seeds.roles import ADMIN_ROLE_NAME
from depends.services import get_current_user


async def require_admin(user: Annotated[UserOut, Depends(get_current_user)]) -> UserOut:
    if ADMIN_ROLE_NAME not in {role.name for role in user.roles}:
        raise ForbiddenError()
    return user
