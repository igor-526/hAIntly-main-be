from unittest.mock import AsyncMock
from uuid import UUID

from fastapi.testclient import TestClient

from core.schemas import AuthTokens, RoleOut, UserOut
from depends.services import get_auth_service
from main import app

USER = UserOut(
    id=UUID("f30d8335-08e5-46ca-a05c-25bf3a49a6c3"),
    email="tester@example.com",
    roles=[RoleOut(id=UUID("589a21a7-307c-4d4d-8722-e709fb6ed8d3"), name="user")],
)


def test_register_accepts_json_dto_and_returns_user_dto() -> None:
    service = AsyncMock()
    service.register.return_value = USER
    app.dependency_overrides[get_auth_service] = lambda: service
    try:
        response = TestClient(app).post(
            "/api/auth/register",
            json={"email": "tester@example.com", "password": "password1"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json() == {
        "id": "f30d8335-08e5-46ca-a05c-25bf3a49a6c3",
        "email": "tester@example.com",
        "roles": [{"id": "589a21a7-307c-4d4d-8722-e709fb6ed8d3", "name": "user"}],
    }
    data = service.register.await_args.kwargs["data"]
    assert data.model_dump() == {
        "email": "tester@example.com",
        "password": "password1",
    }


def test_login_sets_http_only_cookies_and_returns_no_tokens() -> None:
    service = AsyncMock()
    service.login.return_value = AuthTokens(access_token="access", refresh_token="refresh")
    app.dependency_overrides[get_auth_service] = lambda: service
    try:
        response = TestClient(app).post(
            "/api/auth/token", json={"email": "tester@example.com", "password": "password1"}
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 204
    assert response.content == b""
    cookies = response.headers.get_list("set-cookie")
    assert any(
        "access_token=access" in cookie and "HttpOnly" in cookie and "Path=/" in cookie and "SameSite=lax" in cookie
        for cookie in cookies
    )
    refresh_cookie = next(cookie for cookie in cookies if "refresh_token=refresh" in cookie)
    assert "HttpOnly" in refresh_cookie
    assert "Path=/api/auth" in refresh_cookie
    assert "SameSite=lax" in refresh_cookie
    assert service.login.await_args.kwargs["data"].model_dump() == {
        "email": "tester@example.com",
        "password": "password1",
    }


def test_refresh_uses_cookie_and_rotates_http_only_cookies() -> None:
    service = AsyncMock()
    service.refresh.return_value = AuthTokens(access_token="new-access", refresh_token="new-refresh")
    app.dependency_overrides[get_auth_service] = lambda: service
    try:
        client = TestClient(app)
        client.cookies.set("refresh_token", "old-refresh")
        response = client.post("/api/auth/refresh")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 204
    assert response.content == b""
    assert service.refresh.await_args.kwargs == {"token": "old-refresh"}
    cookies = response.headers.get_list("set-cookie")
    assert any(
        "access_token=new-access" in cookie and "HttpOnly" in cookie and "Path=/" in cookie for cookie in cookies
    )
    assert any(
        "refresh_token=new-refresh" in cookie and "HttpOnly" in cookie and "Path=/api/auth" in cookie
        for cookie in cookies
    )


def test_verify_uses_access_cookie_and_returns_user_dto() -> None:
    service = AsyncMock()
    service.current_user.return_value = USER
    app.dependency_overrides[get_auth_service] = lambda: service
    try:
        client = TestClient(app)
        client.cookies.set("access_token", "access")
        response = client.get("/api/auth/verify")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == USER.model_dump(mode="json")
    assert service.current_user.await_args.kwargs == {"token": "access"}


def test_verify_requires_cookie_and_ignores_bearer_header() -> None:
    service = AsyncMock()
    app.dependency_overrides[get_auth_service] = lambda: service
    try:
        response = TestClient(app).get("/api/auth/verify", headers={"Authorization": "Bearer access"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
    assert response.json() == {"detail": "Access-токен отсутствует"}
    service.current_user.assert_not_awaited()


def test_refresh_requires_cookie_and_returns_string_detail() -> None:
    service = AsyncMock()
    app.dependency_overrides[get_auth_service] = lambda: service
    try:
        response = TestClient(app).post("/api/auth/refresh")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
    assert response.json() == {"detail": "Refresh-токен отсутствует"}
    service.refresh.assert_not_awaited()


def test_invalid_registration_is_400() -> None:
    response = TestClient(app).post(
        "/api/auth/register",
        json={"email": "invalid", "password": "short"},
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert isinstance(detail, list)
    assert {error["loc"][-1] for error in detail} == {"email", "password"}
    assert all({"type", "loc", "msg", "input"} <= error.keys() for error in detail)


def test_legacy_auth_fields_are_rejected() -> None:
    client = TestClient(app)

    registration = client.post(
        "/api/auth/register",
        json={"email": "tester@example.com", "username": "tester", "password": "password1"},
    )
    login = client.post("/api/auth/token", json={"login": "tester", "password": "password1"})

    assert registration.status_code == 400
    assert registration.json()["detail"][0]["loc"][-1] == "username"
    assert login.status_code == 400
    assert {error["loc"][-1] for error in login.json()["detail"]} == {"email", "login"}


def test_user_responses_never_contain_removed_or_secret_fields() -> None:
    payload = USER.model_dump(mode="json")

    assert {"login", "username", "password", "password_hash"}.isdisjoint(payload)
