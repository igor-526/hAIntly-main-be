from core.entities import Role
from core.exceptions import ForbiddenError
from core.schemas import RoleOut, UserOut
from depends.roles import require_admin


async def test_require_admin_accepts_admin() -> None:
    user = UserOut(
        id=Role(name="placeholder").id,
        email="admin@example.com",
        roles=[RoleOut(id=Role(name="admin").id, name="admin")],
    )
    assert await require_admin(user) == user


async def test_require_admin_rejects_user() -> None:
    role = Role(name="user")
    user = UserOut(id=role.id, email="user@example.com", roles=[RoleOut(id=role.id, name="user")])
    try:
        await require_admin(user)
    except ForbiddenError:
        return
    raise AssertionError("ForbiddenError was not raised")
