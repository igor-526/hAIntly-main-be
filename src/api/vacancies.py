from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from core.exceptions import ClientError
from core.schemas import UserOut
from depends.services import get_current_user, resolve_hh_user_id
from infrastructure.vacancy_service import VacancyNotFound, VacancyServiceClient, VacancyValidationError
from settings import settings

router = APIRouter(prefix="/vacancies", tags=["Vacancies"])


def _client() -> VacancyServiceClient:
    return VacancyServiceClient(
        base_url=str(settings.vacancy_service_url), timeout_seconds=settings.vacancy_service_timeout_seconds
    )


def _collect_query_params(request: Request) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in request.query_params.multi_items():
        if key in result:
            existing = result[key]
            if isinstance(existing, list):
                existing.append(value)
            else:
                result[key] = [existing, value]
        else:
            result[key] = value
    return result


@router.get("")
async def search_vacancies(
    request: Request,
    user: Annotated[UserOut, Depends(get_current_user)],
):
    client = _client()
    params = _collect_query_params(request)

    hh_user_id: str | None = None
    if "preset_id" in params:
        try:
            hh_user_id = await resolve_hh_user_id(user)
        except ClientError:
            return JSONResponse(status_code=400, content={"detail": "Для использования пресетов необходим HH-аккаунт"})

    try:
        return await client.vacancies_search(user_id=user.id, hh_user_id=hh_user_id, params=params)
    except VacancyNotFound:
        return JSONResponse(status_code=404, content={"detail": "Вакансия не найдена"})
    except VacancyValidationError as exc:
        return JSONResponse(status_code=422, content={"detail": str(exc)})
    except ClientError as exc:
        status_code = 401 if "token" in exc.message.lower() else 502
        return JSONResponse(status_code=status_code, content={"detail": exc.message})


@router.get("/{vacancy_id}")
async def get_vacancy(
    vacancy_id: str,
    user: Annotated[UserOut, Depends(get_current_user)],
):
    client = _client()
    try:
        return await client.vacancy_get(user_id=user.id, vacancy_id=vacancy_id)
    except VacancyNotFound:
        return JSONResponse(status_code=404, content={"detail": "Вакансия не найдена"})
    except VacancyValidationError as exc:
        return JSONResponse(status_code=422, content={"detail": str(exc)})
    except ClientError as exc:
        status_code = 401 if "token" in exc.message.lower() else 502
        return JSONResponse(status_code=status_code, content={"detail": exc.message})
