from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi.testclient import TestClient

from core.schemas import UserOut
from depends.services import get_current_user
from infrastructure.vacancy_service import VacancyNotFound, VacancyServiceClient
from main import app


def test_proxy_requires_real_auth_dependency():
    assert TestClient(app).get("/api/dictionaries/languages").status_code == 401


def test_proxy_route_passes_user_and_query_and_maps_upstream(monkeypatch):
    user = UserOut(id=uuid4(), email="proxy@example.com", roles=[])
    app.dependency_overrides[get_current_user] = lambda: user
    request = AsyncMock(return_value={"items": []})
    monkeypatch.setattr(VacancyServiceClient, "get", request)
    try:
        client = TestClient(app)
        response = client.get("/api/dictionaries/languages", params={"limit": 2, "offset": 1, "q": "ru"})
        assert response.status_code == 200
        call = request.await_args.kwargs
        assert call["user_id"] == user.id
        assert call["params"]["limit"] == 2 and call["params"]["q"] == "ru"
        request.side_effect = VacancyNotFound()
        assert client.get("/api/dictionaries/languages/missing").status_code == 404
        assert client.get("/api/dictionaries/languages", params={"limit": 0}).status_code == 422
    finally:
        app.dependency_overrides.clear()
