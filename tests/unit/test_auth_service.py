from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from core.entities import Role, User
from core.exceptions import AlreadyExistsError, InvalidCredentials
from core.schemas import LoginData, RegisterData
from core.services import AuthService


@pytest.fixture
def dependencies():
    users = Mock()
    users.get_by_email = AsyncMock(return_value=None)
    users.create = AsyncMock()
    users.assign_role = AsyncMock()
    users.get_roles = AsyncMock()
    users.get_by_id = AsyncMock()
    roles = Mock()
    roles.get_by_name = AsyncMock()
    security = Mock()
    return users, roles, security


async def test_register_assigns_user_role(dependencies) -> None:
    users, roles, security = dependencies
    user = User(email="tester@example.com", password="hash")
    role = Role(name="user")
    security.hash_password.return_value = "hash"
    users.create.return_value = user
    users.get_roles.return_value = [role]
    roles.get_by_name.return_value = role
    service = AuthService(users=users, roles=roles, security=security)

    result = await service.register(data=RegisterData(email="Tester@Example.com", password="password1"))

    assert result.email == "tester@example.com"
    assert result.roles[0].name == "user"
    users.assign_role.assert_awaited_once_with(user_id=user.id, role_id=role.id)


async def test_register_rejects_duplicate_email(dependencies) -> None:
    users, roles, security = dependencies
    users.get_by_email.return_value = User(email="tester@example.com", password="hash")
    service = AuthService(users=users, roles=roles, security=security)

    with pytest.raises(AlreadyExistsError):
        await service.register(data=RegisterData(email="tester@example.com", password="password1"))


async def test_login_rejects_wrong_password(dependencies) -> None:
    users, roles, security = dependencies
    users.get_by_email.return_value = User(email="tester@example.com", password="hash")
    security.verify_password.return_value = False
    service = AuthService(users=users, roles=roles, security=security)

    with pytest.raises(InvalidCredentials):
        await service.login(data=LoginData(email="tester@example.com", password="wrong"))


async def test_login_normalizes_email_and_rejects_unknown_user(dependencies) -> None:
    users, roles, security = dependencies
    service = AuthService(users=users, roles=roles, security=security)

    with pytest.raises(InvalidCredentials) as unknown_error:
        await service.login(data=LoginData(email="Tester@Example.com", password="password1"))

    users.get_by_email.assert_awaited_once_with(email="tester@example.com")
    users.get_by_email.return_value = User(email="tester@example.com", password="hash")
    security.verify_password.return_value = False
    with pytest.raises(InvalidCredentials) as password_error:
        await service.login(data=LoginData(email="tester@example.com", password="wrong"))
    assert unknown_error.value.message == password_error.value.message


async def test_refresh_rejects_access_token(dependencies) -> None:
    users, roles, security = dependencies
    security.decode_token.return_value = {"type": "access", "sub": str(uuid4()), "session_version": 1}
    service = AuthService(users=users, roles=roles, security=security)

    with pytest.raises(InvalidCredentials):
        await service.refresh(token="access-token")
