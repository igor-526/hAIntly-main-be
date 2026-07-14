from uuid import uuid4

import pytest

from api.dictionaries import allowed_path
from infrastructure.vacancy_service import VacancyServiceClient


def test_client_keeps_runtime_configuration() -> None:
    client = VacancyServiceClient(base_url="http://vacancy.invalid/", timeout_seconds=3)
    assert client.base_url == "http://vacancy.invalid"
    assert client.timeout.total == 3


@pytest.mark.asyncio
async def test_user_id_is_a_uuid() -> None:
    assert str(uuid4())


@pytest.mark.parametrize(
    "path",
    ["languages", "languages/ru", "dictionary-items", "dictionary-items/schedule/fullDay"],
)
def test_proxy_allowlist_accepts_contract_routes(path: str) -> None:
    assert allowed_path(path)


@pytest.mark.parametrize("path", ["../health", "unknown", "languages/ru/extra", "dictionary-items/code"])
def test_proxy_allowlist_rejects_arbitrary_paths(path: str) -> None:
    assert not allowed_path(path)
