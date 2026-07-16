from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi.testclient import TestClient

from core.exceptions import ClientError
from core.schemas import UserOut
from depends.services import get_current_user
from infrastructure.vacancy_service import VacancyNotFound, VacancyServiceClient, VacancyValidationError
from main import app


def _user() -> UserOut:
    return UserOut(id=uuid4(), email="vacancies@example.com", roles=[])


def _override(user: UserOut | None = None):
    app.dependency_overrides[get_current_user] = lambda: user or _user()


def _clear():
    app.dependency_overrides.clear()


# --- Auth ---


def test_vacancies_require_auth():
    assert TestClient(app).get("/api/vacancies").status_code == 401


def test_vacancy_detail_requires_auth():
    assert TestClient(app).get(f"/api/vacancies/{uuid4()}").status_code == 401


# --- Proxy search ---


def test_search_proxies_params_and_context(monkeypatch):
    user = _user()
    _override(user)
    mock = AsyncMock(return_value={"items": [{"id": "123", "name": "Python Dev"}], "found": 1})
    monkeypatch.setattr(VacancyServiceClient, "vacancies_search", mock)
    try:
        response = TestClient(app).get("/api/vacancies", params={"text": "python", "page": "0", "per_page": "30"})
        assert response.status_code == 200
        data = response.json()
        assert data["found"] == 1
        call = mock.await_args.kwargs
        assert call["user_id"] == user.id
        assert call["hh_user_id"] is None
        assert call["params"]["text"] == "python"
    finally:
        _clear()


def test_search_proxies_preset_id(monkeypatch):
    _override()
    preset_id = uuid4()
    mock = AsyncMock(return_value={"items": [], "found": 0})
    monkeypatch.setattr(VacancyServiceClient, "vacancies_search", mock)
    monkeypatch.setattr("api.vacancies.resolve_hh_user_id", AsyncMock(return_value="12345"))
    try:
        response = TestClient(app).get("/api/vacancies", params={"preset_id": str(preset_id)})
        assert response.status_code == 200
        call = mock.await_args.kwargs
        assert call["params"]["preset_id"] == str(preset_id)
        assert call["hh_user_id"] == "12345"
    finally:
        _clear()


def test_search_proxies_multiple_values(monkeypatch):
    _override()
    mock = AsyncMock(return_value={"items": [], "found": 0})
    monkeypatch.setattr(VacancyServiceClient, "vacancies_search", mock)
    try:
        response = TestClient(app).get("/api/vacancies", params=[("area", "1"), ("area", "2")])
        assert response.status_code == 200
        call = mock.await_args.kwargs
        assert "1" in call["params"]["area"] and "2" in call["params"]["area"]
    finally:
        _clear()


# --- Proxy detail ---


def test_get_vacancy_proxies_context(monkeypatch):
    user = _user()
    vacancy_id = "12345"
    _override(user)
    mock = AsyncMock(return_value={"id": vacancy_id, "name": "Python Dev"})
    monkeypatch.setattr(VacancyServiceClient, "vacancy_get", mock)
    try:
        response = TestClient(app).get(f"/api/vacancies/{vacancy_id}")
        assert response.status_code == 200
        call = mock.await_args.kwargs
        assert call["user_id"] == user.id
        assert call["vacancy_id"] == vacancy_id
    finally:
        _clear()


# --- Error mapping ---


def test_search_maps_not_found(monkeypatch):
    _override()
    monkeypatch.setattr(VacancyServiceClient, "vacancies_search", AsyncMock(side_effect=VacancyNotFound()))
    try:
        assert TestClient(app).get("/api/vacancies").status_code == 404
    finally:
        _clear()


def test_search_maps_validation_error(monkeypatch):
    _override()
    monkeypatch.setattr(
        VacancyServiceClient, "vacancies_search", AsyncMock(side_effect=VacancyValidationError("bad param"))
    )
    try:
        assert TestClient(app).get("/api/vacancies").status_code == 422
    finally:
        _clear()


def test_search_maps_service_unavailable(monkeypatch):
    _override()
    monkeypatch.setattr(
        VacancyServiceClient,
        "vacancies_search",
        AsyncMock(side_effect=ClientError("Сервис вакансий временно недоступен")),
    )
    try:
        assert TestClient(app).get("/api/vacancies").status_code == 502
    finally:
        _clear()


def test_search_maps_hh_authorization_failed(monkeypatch):
    _override()
    monkeypatch.setattr(
        VacancyServiceClient,
        "vacancies_search",
        AsyncMock(side_effect=ClientError("HH token refresh failed")),
    )
    try:
        assert TestClient(app).get("/api/vacancies").status_code == 401
    finally:
        _clear()


def test_get_vacancy_maps_not_found(monkeypatch):
    _override()
    monkeypatch.setattr(VacancyServiceClient, "vacancy_get", AsyncMock(side_effect=VacancyNotFound()))
    try:
        assert TestClient(app).get(f"/api/vacancies/{uuid4()}").status_code == 404
    finally:
        _clear()


def test_get_vacancy_maps_service_unavailable(monkeypatch):
    _override()
    monkeypatch.setattr(
        VacancyServiceClient,
        "vacancy_get",
        AsyncMock(side_effect=ClientError("Сервис вакансий временно недоступен")),
    )
    try:
        assert TestClient(app).get(f"/api/vacancies/{uuid4()}").status_code == 502
    finally:
        _clear()
