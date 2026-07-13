from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from core.schemas import (
    ActiveAccount,
    AuthorizationURL,
    HHAccount,
    HHAccounts,
    OAuthCallback,
    OAuthResult,
    SelectAccount,
    UserOut,
)
from core.services import HHAccountsService, OAuthStateService
from depends.services import get_current_user, get_hh_accounts_service, get_oauth_state_service

router = APIRouter(prefix="/hh", tags=["HH accounts"])


@router.post("/oauth/start", response_model=AuthorizationURL)
async def start_oauth(
    user: Annotated[UserOut, Depends(get_current_user)],
    accounts: Annotated[HHAccountsService, Depends(get_hh_accounts_service)],
    states: Annotated[OAuthStateService, Depends(get_oauth_state_service)],
) -> AuthorizationURL:
    state = states.issue(user_id=user.id)
    return AuthorizationURL(authorization_url=await accounts.profiles.authorization_url(state=state))


@router.post("/oauth/callback", response_model=OAuthResult)
async def callback(
    data: OAuthCallback,
    accounts: Annotated[HHAccountsService, Depends(get_hh_accounts_service)],
    states: Annotated[OAuthStateService, Depends(get_oauth_state_service)],
) -> OAuthResult:
    user_id = await states.consume(state=data.state)
    if data.error or data.code is None:
        return OAuthResult(success=False, message="Подключение HH отменено или не выполнено")
    account = await accounts.profiles.complete(user_id=user_id, code=data.code)
    current = await accounts.list(user_id=user_id)
    if current.active_account_id is None:
        await accounts.select(user_id=user_id, account_id=account.id)
    return OAuthResult(success=True, account=account)


@router.get("/accounts", response_model=HHAccounts)
async def list_accounts(
    user: Annotated[UserOut, Depends(get_current_user)],
    accounts: Annotated[HHAccountsService, Depends(get_hh_accounts_service)],
) -> HHAccounts:
    return await accounts.list(user_id=user.id)


@router.get("/accounts/{account_id}", response_model=HHAccount)
async def get_account(
    account_id: UUID,
    user: Annotated[UserOut, Depends(get_current_user)],
    accounts: Annotated[HHAccountsService, Depends(get_hh_accounts_service)],
) -> HHAccount:
    account = await accounts.get(user_id=user.id, account_id=account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="HH-аккаунт не найден")
    return account


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: UUID,
    user: Annotated[UserOut, Depends(get_current_user)],
    accounts: Annotated[HHAccountsService, Depends(get_hh_accounts_service)],
) -> Response:
    await accounts.delete(user_id=user.id, account_id=account_id)
    return Response(status_code=204)


@router.put("/accounts/active", response_model=ActiveAccount)
async def select_account(
    data: SelectAccount,
    user: Annotated[UserOut, Depends(get_current_user)],
    accounts: Annotated[HHAccountsService, Depends(get_hh_accounts_service)],
) -> ActiveAccount:
    return ActiveAccount(active_account_id=await accounts.select(user_id=user.id, account_id=data.account_id))
