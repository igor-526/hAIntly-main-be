from uuid import UUID

from core.exceptions import ClientError
from core.protocols import ProfileServiceProtocol
from core.protocols.repositories import UserRepositoryProtocol
from core.schemas import HHAccount, HHAccounts


class HHAccountsService:
    def __init__(self, *, profiles: ProfileServiceProtocol, users: UserRepositoryProtocol) -> None:
        self.profiles = profiles
        self.users = users

    async def list(self, *, user_id: UUID) -> HHAccounts:
        accounts = await self.profiles.list_accounts(user_id=user_id)
        user = await self.users.get_by_id(user_id=user_id)
        active = user.active_hh_account_id if user else None
        ids = {account.id for account in accounts}
        if active not in ids:
            active = accounts[0].id if accounts else None
            await self.users.set_active_hh_account(user_id=user_id, account_id=active)
        return HHAccounts(accounts=accounts, active_account_id=active)

    async def get(self, *, user_id: UUID, account_id: UUID) -> HHAccount | None:
        return await self.profiles.get_account(user_id=user_id, account_id=account_id)

    async def select(self, *, user_id: UUID, account_id: UUID) -> UUID:
        if await self.profiles.get_account(user_id=user_id, account_id=account_id) is None:
            raise ClientError("HH-аккаунт не найден")
        await self.users.set_active_hh_account(user_id=user_id, account_id=account_id)
        return account_id

    async def delete(self, *, user_id: UUID, account_id: UUID) -> None:
        await self.profiles.delete_account(user_id=user_id, account_id=account_id)
        await self.list(user_id=user_id)
