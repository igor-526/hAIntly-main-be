from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi.testclient import TestClient

from core.exceptions import ClientError
from core.schemas import UserOut
from depends.services import get_current_user, get_hh_user_id
from infrastructure.vacancy_service import VacancyNotFound, VacancyServiceClient, VacancyValidationError
from main import app


def _user() -> UserOut:
    return UserOut(id=uuid4(), email="filters@example.com", roles=[])


def _override(user: UserOut, hh_user_id: str = "hh-42"):
    app.dependency_overrides[get_current_user] = lambda: user

    async def _hh_uid() -> str:
        return hh_user_id

    app.dependency_overrides[get_hh_user_id] = _hh_uid


def _clear():
    app.dependency_overrides.clear()


def test_filters_require_auth():
    assert TestClient(app).get("/api/filters").status_code == 401
    assert TestClient(app).get(f"/api/filters/{uuid4()}").status_code == 401
    assert TestClient(app).post("/api/filters", json={}).status_code == 401
    assert TestClient(app).patch(f"/api/filters/{uuid4()}", json={}).status_code == 401
    assert TestClient(app).delete(f"/api/filters/{uuid4()}").status_code == 401


def test_list_presets_proxies_with_context(monkeypatch):
    user = _user()
    _override(user, "hh-99")
    mock = AsyncMock(return_value={"items": [{"id": str(uuid4()), "name": "My filter"}], "total": 1})
    monkeypatch.setattr(VacancyServiceClient, "filters_list", mock)
    try:
        response = TestClient(app).get("/api/filters", params={"limit": 10, "offset": 0, "q": "test"})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        call = mock.await_args.kwargs
        assert call["user_id"] == user.id
        assert call["hh_user_id"] == "hh-99"
        assert call["params"]["q"] == "test"
        assert call["params"]["limit"] == 10
    finally:
        _clear()


def test_list_presets_maps_not_found(monkeypatch):
    _user_obj = _user()
    _override(_user_obj)
    monkeypatch.setattr(VacancyServiceClient, "filters_list", AsyncMock(side_effect=VacancyNotFound()))
    try:
        assert TestClient(app).get("/api/filters").status_code == 404
    finally:
        _clear()


def test_list_presets_maps_validation_error(monkeypatch):
    _user_obj = _user()
    _override(_user_obj)
    monkeypatch.setattr(
        VacancyServiceClient, "filters_list", AsyncMock(side_effect=VacancyValidationError("bad param"))
    )
    try:
        assert TestClient(app).get("/api/filters").status_code == 422
    finally:
        _clear()


def test_list_presets_maps_service_unavailable(monkeypatch):
    _user_obj = _user()
    _override(_user_obj)
    monkeypatch.setattr(
        VacancyServiceClient,
        "filters_list",
        AsyncMock(side_effect=ClientError("Сервис вакансий временно недоступен")),
    )
    try:
        assert TestClient(app).get("/api/filters").status_code == 502
    finally:
        _clear()


def test_get_preset_proxies_with_context(monkeypatch):
    user = _user()
    preset_id = uuid4()
    _override(user, "hh-42")
    mock = AsyncMock(return_value={"id": str(preset_id), "name": "Test", "values": []})
    monkeypatch.setattr(VacancyServiceClient, "filters_get", mock)
    try:
        response = TestClient(app).get(f"/api/filters/{preset_id}")
        assert response.status_code == 200
        call = mock.await_args.kwargs
        assert call["preset_id"] == preset_id
        assert call["user_id"] == user.id
        assert call["hh_user_id"] == "hh-42"
    finally:
        _clear()


def test_get_preset_maps_not_found(monkeypatch):
    _user_obj = _user()
    _override(_user_obj)
    monkeypatch.setattr(VacancyServiceClient, "filters_get", AsyncMock(side_effect=VacancyNotFound()))
    try:
        assert TestClient(app).get(f"/api/filters/{uuid4()}").status_code == 404
    finally:
        _clear()


def test_create_preset_proxies_with_context(monkeypatch):
    user = _user()
    preset_id = uuid4()
    _override(user, "hh-7")
    mock = AsyncMock(return_value={"id": str(preset_id), "name": "New", "values": []})
    monkeypatch.setattr(VacancyServiceClient, "filters_create", mock)
    body = {"name": "New", "area": ["2"]}
    try:
        response = TestClient(app).post("/api/filters", json=body)
        assert response.status_code == 201
        call = mock.await_args.kwargs
        assert call["user_id"] == user.id
        assert call["hh_user_id"] == "hh-7"
        assert call["body"]["name"] == "New"
    finally:
        _clear()


def test_create_preset_maps_validation_error(monkeypatch):
    _user_obj = _user()
    _override(_user_obj)
    monkeypatch.setattr(
        VacancyServiceClient, "filters_create", AsyncMock(side_effect=VacancyValidationError("bad value"))
    )
    try:
        assert TestClient(app).post("/api/filters", json={"name": "X"}).status_code == 422
    finally:
        _clear()


def test_update_preset_proxies_with_context(monkeypatch):
    user = _user()
    preset_id = uuid4()
    _override(user, "hh-5")
    mock = AsyncMock(return_value={"id": str(preset_id), "name": "Updated", "values": []})
    monkeypatch.setattr(VacancyServiceClient, "filters_update", mock)
    try:
        response = TestClient(app).patch(f"/api/filters/{preset_id}", json={"name": "Updated"})
        assert response.status_code == 200
        call = mock.await_args.kwargs
        assert call["preset_id"] == preset_id
        assert call["user_id"] == user.id
        assert call["hh_user_id"] == "hh-5"
        assert call["body"]["name"] == "Updated"
    finally:
        _clear()


def test_update_preset_maps_not_found(monkeypatch):
    _user_obj = _user()
    _override(_user_obj)
    monkeypatch.setattr(VacancyServiceClient, "filters_update", AsyncMock(side_effect=VacancyNotFound()))
    try:
        assert TestClient(app).patch(f"/api/filters/{uuid4()}", json={"name": "X"}).status_code == 404
    finally:
        _clear()


def test_delete_preset_proxies_with_context(monkeypatch):
    user = _user()
    preset_id = uuid4()
    _override(user, "hh-3")
    mock = AsyncMock(return_value=None)
    monkeypatch.setattr(VacancyServiceClient, "filters_delete", mock)
    try:
        response = TestClient(app).delete(f"/api/filters/{preset_id}")
        assert response.status_code == 204
        call = mock.await_args.kwargs
        assert call["preset_id"] == preset_id
        assert call["user_id"] == user.id
        assert call["hh_user_id"] == "hh-3"
    finally:
        _clear()


def test_delete_preset_maps_not_found(monkeypatch):
    _user_obj = _user()
    _override(_user_obj)
    monkeypatch.setattr(VacancyServiceClient, "filters_delete", AsyncMock(side_effect=VacancyNotFound()))
    try:
        assert TestClient(app).delete(f"/api/filters/{uuid4()}").status_code == 404
    finally:
        _clear()


def test_delete_preset_maps_service_unavailable(monkeypatch):
    _user_obj = _user()
    _override(_user_obj)
    monkeypatch.setattr(
        VacancyServiceClient,
        "filters_delete",
        AsyncMock(side_effect=ClientError("Сервис вакансий временно недоступен")),
    )
    try:
        assert TestClient(app).delete(f"/api/filters/{uuid4()}").status_code == 502
    finally:
        _clear()
