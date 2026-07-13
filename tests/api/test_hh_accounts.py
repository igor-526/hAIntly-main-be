from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from fastapi.testclient import TestClient

from core.schemas import HHAccount
from depends.services import get_hh_accounts_service, get_oauth_state_service
from main import app


def test_callback_is_open_and_never_returns_code_state_or_tokens() -> None:
    user_id = uuid4()
    account = HHAccount(
        id=uuid4(),
        hh_user_id="hh-1",
        display_name="Иван",
        email=None,
        avatar_url=None,
        created_at=datetime.now(UTC),
        updated_at=None,
    )
    states = Mock()
    states.consume = AsyncMock(return_value=user_id)
    profiles = AsyncMock()
    profiles.complete.return_value = account
    accounts = AsyncMock()
    accounts.profiles = profiles
    accounts.list.return_value.active_account_id = account.id
    app.dependency_overrides[get_oauth_state_service] = lambda: states
    app.dependency_overrides[get_hh_accounts_service] = lambda: accounts
    try:
        response = TestClient(app).post(
            "/api/hh/oauth/callback", json={"state": "opaque-state", "code": "one-time-code"}
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["success"] is True
    serialized = response.text.lower()
    assert "opaque-state" not in serialized
    assert "one-time-code" not in serialized
    assert "token" not in serialized
    states.consume.assert_awaited_once_with(state="opaque-state")
    profiles.complete.assert_awaited_once_with(user_id=user_id, code="one-time-code")


def test_callback_consumes_state_before_safe_hh_error_result() -> None:
    states = Mock()
    states.consume = AsyncMock(return_value=uuid4())
    accounts = AsyncMock()
    app.dependency_overrides[get_oauth_state_service] = lambda: states
    app.dependency_overrides[get_hh_accounts_service] = lambda: accounts
    try:
        response = TestClient(app).post(
            "/api/hh/oauth/callback", json={"state": "opaque-state", "error": "access_denied"}
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() == {
        "success": False,
        "account": None,
        "message": "Подключение HH отменено или не выполнено",
    }
    accounts.profiles.complete.assert_not_awaited()
