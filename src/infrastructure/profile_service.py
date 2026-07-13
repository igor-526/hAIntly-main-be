from uuid import UUID

import aiohttp

from core.exceptions import ClientError
from core.schemas import HHAccount


class ProfileServiceClient:
    def __init__(self, *, base_url: str, timeout_seconds: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds)

    async def authorization_url(self, *, state: str) -> str:
        data = await self._request("POST", "/internal/hh/oauth/authorization", json={"state": state})
        return str(data["authorization_url"])

    async def complete(self, *, user_id: UUID, code: str) -> HHAccount:
        return HHAccount.model_validate(
            await self._request("POST", "/internal/hh/oauth/complete", json={"user_id": str(user_id), "code": code})
        )

    async def list_accounts(self, *, user_id: UUID) -> list[HHAccount]:
        data = await self._request("POST", "/internal/hh/accounts/list", json={"user_id": str(user_id)})
        items = data.get("accounts", [])
        if not isinstance(items, list):
            raise ClientError("Profile-service вернул некорректный ответ")
        return [HHAccount.model_validate(item) for item in items]

    async def get_account(self, *, user_id: UUID, account_id: UUID) -> HHAccount | None:
        try:
            data = await self._request("POST", f"/internal/hh/accounts/{account_id}", json={"user_id": str(user_id)})
        except _NotFound:
            return None
        return HHAccount.model_validate(data)

    async def delete_account(self, *, user_id: UUID, account_id: UUID) -> None:
        await self._request("DELETE", f"/internal/hh/accounts/{account_id}", json={"user_id": str(user_id)})

    async def _request(self, method: str, path: str, *, json: dict[str, str] | None = None) -> dict[str, object]:
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.request(method, self.base_url + path, json=json) as response:
                    if response.status == 404:
                        raise _NotFound
                    if response.status >= 400:
                        raise ClientError("Операция с HH-аккаунтом не выполнена")
                    if response.status == 204:
                        return {}
                    data = await response.json()
                    if not isinstance(data, dict):
                        raise ClientError("Profile-service вернул некорректный ответ")
                    return data
        except _NotFound:
            raise
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise ClientError("Profile-service временно недоступен") from exc


class _NotFound(Exception):
    pass
