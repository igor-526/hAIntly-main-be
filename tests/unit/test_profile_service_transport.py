from uuid import uuid4

import pytest

from core.exceptions import ClientError
from infrastructure.profile_service import ProfileServiceClient


class Response:
    def __init__(self, status, payload=None):
        self.status, self.payload = status, payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def json(self):
        return self.payload


class Session:
    responses: list[Response] = []
    calls: list[tuple[str, str, object, object]] = []

    def __init__(self, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    def request(self, method, url, *, json=None, headers=None):
        self.calls.append((method, url, json, headers))
        return self.responses.pop(0)


@pytest.mark.asyncio
async def test_profile_client_typed_contract_uses_user_header_and_no_user_body(monkeypatch) -> None:
    monkeypatch.setattr("infrastructure.profile_service.aiohttp.ClientSession", Session)
    user_id, account_id = uuid4(), uuid4()
    payload = {
        "id": str(account_id),
        "hh_user_id": "hh-1",
        "display_name": None,
        "email": None,
        "avatar_url": None,
        "created_at": "2026-07-12T00:00:00Z",
        "updated_at": None,
    }
    Session.calls = []
    Session.responses = [
        Response(200, {"authorization_url": "https://hh.test/oauth"}),
        Response(200, payload),
        Response(200, {"accounts": [payload]}),
        Response(200, payload),
        Response(204),
    ]
    client = ProfileServiceClient(base_url="http://profile", timeout_seconds=1)
    assert await client.authorization_url(state="opaque") == "https://hh.test/oauth"
    assert await client.complete(user_id=user_id, code="code") is not None
    assert len(await client.list_accounts(user_id=user_id)) == 1
    assert await client.get_account(user_id=user_id, account_id=account_id) is not None
    await client.delete_account(user_id=user_id, account_id=account_id)
    authorization_call, complete_call, *account_calls = Session.calls
    assert authorization_call[2:] == ({"state": "opaque"}, None)
    assert complete_call[2:] == ({"code": "code"}, {"X-User-Id": str(user_id)})
    assert all(call[2] is None and call[3] == {"X-User-Id": str(user_id)} for call in account_calls)


@pytest.mark.asyncio
async def test_profile_client_maps_not_found_and_remote_errors(monkeypatch) -> None:
    monkeypatch.setattr("infrastructure.profile_service.aiohttp.ClientSession", Session)
    client = ProfileServiceClient(base_url="http://profile", timeout_seconds=1)
    Session.responses = [Response(404)]
    assert await client.get_account(user_id=uuid4(), account_id=uuid4()) is None
    Session.responses = [Response(503, {"detail": "internal"})]
    with pytest.raises(ClientError, match="не выполнена"):
        await client.list_accounts(user_id=uuid4())
