from uuid import UUID

import aiohttp

from core.exceptions import ClientError


def _flat_params(params: dict[str, object]) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    for k, v in params.items():
        if v is None:
            continue
        if isinstance(v, list):
            result.extend((k, str(item)) for item in v)
        else:
            result.append((k, str(v)))
    return result


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
        except (VacancyNotFound, VacancyValidationError):
            raise
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise ClientError("Сервис справочников временно недоступен") from exc

    async def filters_list(
        self, *, user_id: UUID, hh_user_id: str, params: dict[str, object]
    ) -> dict[str, object]:
        return await self._request(
            "GET", "/internal/filters", user_id=user_id, hh_user_id=hh_user_id, params=params
        )

    async def filters_get(
        self, *, preset_id: UUID, user_id: UUID, hh_user_id: str
    ) -> dict[str, object]:
        return await self._request(
            "GET", f"/internal/filters/{preset_id}", user_id=user_id, hh_user_id=hh_user_id
        )

    async def filters_create(
        self, *, user_id: UUID, hh_user_id: str, body: dict[str, object]
    ) -> dict[str, object]:
        return await self._request(
            "POST", "/internal/filters", user_id=user_id, hh_user_id=hh_user_id, json_body=body
        )

    async def filters_update(
        self, *, preset_id: UUID, user_id: UUID, hh_user_id: str, body: dict[str, object]
    ) -> dict[str, object]:
        return await self._request(
            "PATCH", f"/internal/filters/{preset_id}", user_id=user_id, hh_user_id=hh_user_id, json_body=body
        )

    async def filters_delete(
        self, *, preset_id: UUID, user_id: UUID, hh_user_id: str
    ) -> None:
        await self._request(
            "DELETE", f"/internal/filters/{preset_id}", user_id=user_id, hh_user_id=hh_user_id
        )

    async def vacancies_search(
        self, *, user_id: UUID, hh_user_id: str | None, params: dict[str, object]
    ) -> dict[str, object]:
        return await self._vacancy_request(
            "GET", "/internal/vacancies", user_id=user_id, hh_user_id=hh_user_id, params=params
        )

    async def vacancy_get(
        self, *, user_id: UUID, vacancy_id: str
    ) -> dict[str, object]:
        return await self._vacancy_request(
            "GET", f"/internal/vacancies/{vacancy_id}", user_id=user_id
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        user_id: UUID,
        hh_user_id: str,
        params: dict[str, object] | None = None,
        json_body: dict[str, object] | None = None,
    ) -> dict[str, object]:
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                kwargs: dict[str, object] = {
                    "headers": {"X-User-Id": str(user_id), "X-Hh-User-Id": hh_user_id},
                }
                if params is not None:
                    kwargs["params"] = {k: str(v) for k, v in params.items() if v is not None}
                if json_body is not None:
                    kwargs["json"] = json_body
                async with session.request(method, self.base_url + path, **kwargs) as response:  # type: ignore[arg-type]
                    if response.status == 404:
                        raise VacancyNotFound
                    if response.status == 422:
                        detail = await response.text()
                        raise VacancyValidationError(detail)
                    if response.status == 400:
                        detail = await response.text()
                        raise VacancyValidationError(detail)
                    if response.status >= 400:
                        raise ClientError("Сервис вакансий временно недоступен")
                    if response.status == 204:
                        return {}
                    data = await response.json()
                    if not isinstance(data, (dict, list)):
                        raise ClientError("Сервис вакансий вернул некорректный ответ")
                    return data
        except (VacancyNotFound, VacancyValidationError):
            raise
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise ClientError("Сервис вакансий временно недоступен") from exc

    async def _vacancy_request(
        self,
        method: str,
        path: str,
        *,
        user_id: UUID,
        hh_user_id: str | None = None,
        params: dict[str, object] | None = None,
    ) -> dict[str, object]:
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                headers: dict[str, str] = {"X-User-Id": str(user_id)}
                if hh_user_id:
                    headers["X-Hh-User-Id"] = hh_user_id
                kwargs: dict[str, object] = {"headers": headers}
                if params is not None:
                    kwargs["params"] = _flat_params(params)
                async with session.request(method, self.base_url + path, **kwargs) as response:  # type: ignore[arg-type]
                    if response.status == 404:
                        raise VacancyNotFound
                    if response.status == 422:
                        detail = await response.text()
                        raise VacancyValidationError(detail)
                    if response.status == 400:
                        detail = await response.text()
                        raise VacancyValidationError(detail)
                    if response.status == 401:
                        detail = await response.text()
                        raise ClientError(detail or "HH token refresh failed")
                    if response.status >= 400:
                        raise ClientError("Сервис вакансий временно недоступен")
                    data = await response.json()
                    if not isinstance(data, (dict, list)):
                        raise ClientError("Сервис вакансий вернул некорректный ответ")
                    return data
        except (VacancyNotFound, VacancyValidationError, ClientError):
            raise
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise ClientError("Сервис вакансий временно недоступен") from exc
