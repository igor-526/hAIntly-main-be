from uuid import uuid4

import pytest
from aiohttp import web

from core.exceptions import ClientError
from infrastructure.vacancy_service import VacancyNotFound, VacancyServiceClient, VacancyValidationError


async def serve(handler):
    app = web.Application()
    app.router.add_get("/{tail:.*}", handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    return runner, f"http://127.0.0.1:{port}"


@pytest.mark.asyncio
async def test_real_http_passes_query_and_user_header():
    user_id = uuid4()

    async def handler(request):
        assert request.headers["X-User-Id"] == str(user_id)
        assert request.query["limit"] == "2" and request.query["q"] == "ru"
        return web.json_response({"items": []})

    runner, url = await serve(handler)
    try:
        assert await VacancyServiceClient(base_url=url, timeout_seconds=1).get(
            path="languages", user_id=user_id, params={"limit": 2, "q": "ru"}
        ) == {"items": []}
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
@pytest.mark.parametrize("status,error", [(404, VacancyNotFound), (400, VacancyValidationError), (500, ClientError)])
async def test_real_http_maps_errors(status, error):
    async def handler(_):
        return web.json_response({}, status=status)

    runner, url = await serve(handler)
    try:
        with pytest.raises(error):
            await VacancyServiceClient(base_url=url, timeout_seconds=1).get(
                path="languages", user_id=uuid4(), params={}
            )
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_real_http_timeout_and_invalid_json():
    async def slow(_):
        import asyncio

        await asyncio.sleep(0.1)
        return web.json_response({})

    runner, url = await serve(slow)
    try:
        with pytest.raises(ClientError):
            await VacancyServiceClient(base_url=url, timeout_seconds=0.01).get(
                path="languages", user_id=uuid4(), params={}
            )
    finally:
        await runner.cleanup()

    async def invalid(_):
        return web.Response(text="not-json")

    runner, url = await serve(invalid)
    try:
        with pytest.raises(ClientError):
            await VacancyServiceClient(base_url=url, timeout_seconds=1).get(
                path="languages", user_id=uuid4(), params={}
            )
    finally:
        await runner.cleanup()
