from uuid import UUID

import aiohttp

from core.exceptions import ClientError


class VacancyNotFound(Exception):
    pass


class VacancyValidationError(Exception):
    pass


class VacancyServiceClient:
    def __init__(self, *, base_url: str, timeout_seconds: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds)

    async def get(self, *, path: str, user_id: UUID, params: dict[str, object]):
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(
                    self.base_url + "/internal/dictionaries/" + path,
                    params={k: str(v) for k, v in params.items() if v is not None},
                    headers={"X-User-Id": str(user_id)},
                ) as response:
                    if response.status == 404:
                        raise VacancyNotFound
                    if response.status == 400:
                        raise VacancyValidationError
                    if response.status >= 400:
                        raise ClientError("Сервис справочников временно недоступен")
                    data = await response.json()
                    if not isinstance(data, (dict, list)):
                        raise ClientError("Сервис справочников вернул некорректный ответ")
                    return data
        except VacancyNotFound, VacancyValidationError:
            raise
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise ClientError("Сервис справочников временно недоступен") from exc
