from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Response, status

from core.exceptions import InvalidCredentials
from core.schemas import LoginData, RegisterData, UserOut
from core.services import AuthService
from depends.services import get_auth_service, get_current_user
from settings import settings

router = APIRouter(prefix="/auth", tags=["Auth"])


def _set_auth_cookies(response: Response, *, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=settings.access_token_minutes * 60,
        path="/",
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=settings.refresh_token_days * 24 * 60 * 60,
        path="/api/auth",
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterData,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserOut:
    return await service.register(data=data)


@router.post("/token", status_code=status.HTTP_204_NO_CONTENT)
async def login(
    data: LoginData,
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> None:
    tokens = await service.login(data=data)
    _set_auth_cookies(response, access_token=tokens.access_token, refresh_token=tokens.refresh_token)


@router.post("/refresh", status_code=status.HTTP_204_NO_CONTENT)
async def refresh(
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> None:
    if refresh_token is None:
        raise InvalidCredentials("Refresh-токен отсутствует")
    tokens = await service.refresh(token=refresh_token)
    _set_auth_cookies(response, access_token=tokens.access_token, refresh_token=tokens.refresh_token)


@router.get("/verify", response_model=UserOut)
async def verify(
    user: Annotated[UserOut, Depends(get_current_user)],
) -> UserOut:
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    response.delete_cookie(
        "access_token",
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )
    response.delete_cookie(
        "refresh_token",
        path="/api/auth",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )
