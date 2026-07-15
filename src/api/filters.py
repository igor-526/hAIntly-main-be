from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from core.exceptions import ClientError
from core.schemas import UserOut
from depends.services import get_current_user, get_hh_user_id
from infrastructure.vacancy_service import VacancyNotFound, VacancyServiceClient, VacancyValidationError
from settings import settings

router = APIRouter(prefix="/filters", tags=["Filters"])


def _client() -> VacancyServiceClient:
    return VacancyServiceClient(
        base_url=str(settings.vacancy_service_url), timeout_seconds=settings.vacancy_service_timeout_seconds
    )


@router.get("")
async def list_presets(
    user: Annotated[UserOut, Depends(get_current_user)],
    hh_user_id: Annotated[str, Depends(get_hh_user_id)],
    q: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    client = _client()
    try:
        return await client.filters_list(
            user_id=user.id, hh_user_id=hh_user_id, params={"q": q, "limit": limit, "offset": offset}
        )
    except VacancyNotFound:
        return JSONResponse(status_code=404, content={"detail": "Пресет не найден"})
    except VacancyValidationError as exc:
        return JSONResponse(status_code=422, content={"detail": str(exc)})
    except ClientError as exc:
        return JSONResponse(status_code=502, content={"detail": exc.message})


@router.get("/{preset_id}")
async def get_preset(
    preset_id: UUID,
    user: Annotated[UserOut, Depends(get_current_user)],
    hh_user_id: Annotated[str, Depends(get_hh_user_id)],
):
    client = _client()
    try:
        return await client.filters_get(preset_id=preset_id, user_id=user.id, hh_user_id=hh_user_id)
    except VacancyNotFound:
        return JSONResponse(status_code=404, content={"detail": "Пресет не найден"})
    except VacancyValidationError as exc:
        return JSONResponse(status_code=422, content={"detail": str(exc)})
    except ClientError as exc:
        return JSONResponse(status_code=502, content={"detail": exc.message})


@router.post("", status_code=201)
async def create_preset(
    request: Request,
    user: Annotated[UserOut, Depends(get_current_user)],
    hh_user_id: Annotated[str, Depends(get_hh_user_id)],
):
    body = await request.json()
    client = _client()
    try:
        return await client.filters_create(user_id=user.id, hh_user_id=hh_user_id, body=body)
    except VacancyNotFound:
        return JSONResponse(status_code=404, content={"detail": "Пресет не найден"})
    except VacancyValidationError as exc:
        return JSONResponse(status_code=422, content={"detail": str(exc)})
    except ClientError as exc:
        return JSONResponse(status_code=502, content={"detail": exc.message})


@router.patch("/{preset_id}")
async def update_preset(
    preset_id: UUID,
    request: Request,
    user: Annotated[UserOut, Depends(get_current_user)],
    hh_user_id: Annotated[str, Depends(get_hh_user_id)],
):
    body = await request.json()
    client = _client()
    try:
        return await client.filters_update(
            preset_id=preset_id, user_id=user.id, hh_user_id=hh_user_id, body=body
        )
    except VacancyNotFound:
        return JSONResponse(status_code=404, content={"detail": "Пресет не найден"})
    except VacancyValidationError as exc:
        return JSONResponse(status_code=422, content={"detail": str(exc)})
    except ClientError as exc:
        return JSONResponse(status_code=502, content={"detail": exc.message})


@router.delete("/{preset_id}", status_code=204)
async def delete_preset(
    preset_id: UUID,
    user: Annotated[UserOut, Depends(get_current_user)],
    hh_user_id: Annotated[str, Depends(get_hh_user_id)],
):
    client = _client()
    try:
        await client.filters_delete(preset_id=preset_id, user_id=user.id, hh_user_id=hh_user_id)
    except VacancyNotFound:
        return JSONResponse(status_code=404, content={"detail": "Пресет не найден"})
    except VacancyValidationError as exc:
        return JSONResponse(status_code=422, content={"detail": str(exc)})
    except ClientError as exc:
        return JSONResponse(status_code=502, content={"detail": exc.message})
