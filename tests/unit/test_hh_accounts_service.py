from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

import pytest

from core.entities import User
from core.exceptions import ClientError
from core.schemas import HHAccount
from core.services import HHAccountsService


def account(account_id=None):
    return HHAccount(
        id=account_id or uuid4(),
        hh_user_id=str(uuid4()),
        display_name=None,
        email=None,
        avatar_url=None,
        created_at=datetime.now(UTC),
        updated_at=None,
    )


class Profiles:
    def __init__(self, accounts):
        self.accounts = accounts

    async def list_accounts(self, *, user_id):
        return list(self.accounts)

    async def get_account(self, *, user_id, account_id):
        return next((item for item in self.accounts if item.id == account_id), None)

    async def get_selected_account(self, *, user_id, account_id):
        return await self.get_account(user_id=user_id, account_id=account_id)

    async def delete_account(self, *, user_id, account_id):
        self.accounts = [item for item in self.accounts if item.id != account_id]

    async def authorization_url(self, *, state):
        return "https://hh/auth"

    async def complete(self, *, user_id, code):
        return self.accounts[0]


class Users:
    def __init__(self, user):
        self.user = user

    async def get_by_id(self, *, user_id):
        return self.user

    async def set_active_hh_account(self, *, user_id, account_id):
        self.user.active_hh_account_id = account_id


@pytest.mark.asyncio
async def test_multi_account_select_delete_and_empty_reconciliation() -> None:
    first, second = account(), account()
    user = User(email="a@b.test", password="hash", active_hh_account_id=first.id)
    profiles, users = Profiles([first, second]), Users(user)
    service = HHAccountsService(profiles=profiles, users=cast(Any, users))
    assert (await service.list(user_id=user.id)).active_account_id == first.id
    assert await service.select(user_id=user.id, account_id=second.id) == second.id
    await service.delete(user_id=user.id, account_id=second.id)
    assert user.active_hh_account_id == first.id
    await service.delete(user_id=user.id, account_id=first.id)
    assert user.active_hh_account_id is None


@pytest.mark.asyncio
async def test_missing_or_foreign_selection_keeps_previous_active() -> None:
    first = account()
    user = User(email="a@b.test", password="hash", active_hh_account_id=first.id)
    service = HHAccountsService(profiles=Profiles([first]), users=cast(Any, Users(user)))
    with pytest.raises(ClientError, match="не найден"):
        await service.select(user_id=user.id, account_id=uuid4())
    assert user.active_hh_account_id == first.id
