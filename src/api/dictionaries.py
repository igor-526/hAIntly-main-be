from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from core.schemas import UserOut
from depends.services import get_current_user
from infrastructure.vacancy_service import VacancyNotFound, VacancyServiceClient, VacancyValidationError
from settings import settings

router = APIRouter(prefix="/dictionaries", tags=["Dictionaries"])
FAMILIES = {
    "areas",
    "countries",
    "professional-roles",
    "industries",
    "metro-cities",
    "metro-lines",
    "metro-stations",
    "languages",
}


def allowed_path(path: str) -> bool:
    parts = path.strip("/").split("/")
    if parts[0] == "dictionary-items":
        return len(parts) in (1, 3) and all(parts)
    return parts[0] in FAMILIES and len(parts) in (1, 2) and all(parts)


@router.get("/{path:path}")
async def proxy(
    path: str,
    request: Request,
    user: Annotated[UserOut, Depends(get_current_user)],
    q: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    parent_id: str | None = None,
    category_id: str | None = None,
    city_id: str | None = None,
    line_id: str | None = None,
    dictionary_code: str | None = None,
):
    if not allowed_path(path):
        raise HTTPException(404, "Справочник не найден")
    client = VacancyServiceClient(
        base_url=str(settings.vacancy_service_url), timeout_seconds=settings.vacancy_service_timeout_seconds
    )
    try:
        return await client.get(
            path=path,
            user_id=user.id,
            params={
                "q": q,
                "limit": limit,
                "offset": offset,
                "parent_id": parent_id,
                "category_id": category_id,
                "city_id": city_id,
                "line_id": line_id,
                "dictionary_code": dictionary_code,
            },
        )
    except VacancyNotFound as exc:
        raise HTTPException(404, "Элемент не найден") from exc
    except VacancyValidationError as exc:
        raise HTTPException(400, "Некорректные параметры") from exc
