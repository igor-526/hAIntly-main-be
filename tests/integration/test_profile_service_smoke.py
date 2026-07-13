import asyncio
import os
import socket
from pathlib import Path
from uuid import uuid4

import aiohttp
import pytest

from infrastructure import ProfileServiceClient


@pytest.mark.asyncio
async def test_main_be_client_to_real_profile_routes_with_mock_hh() -> None:
    profile_root = Path(__file__).parents[3] / "profile-service"
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    env = os.environ | {
        "PYTHONPATH": "src:tests",
        "HH_TOKEN_ENCRYPT_KEY": "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=",
        "HH_REDIRECT_URL": "http://localhost/callback",
        "HH_CLIENT_ID": "mock",
        "HH_CLIENT_SECRET": "mock",
    }
    command = [
        str(profile_root / ".venv/bin/python"),
        "-m",
        "uvicorn",
        "mock_hh_app:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--log-level",
        "error",
    ]
    process = await asyncio.create_subprocess_exec(
        *command,
        cwd=profile_root,
        env=env,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    try:
        for _ in range(50):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"http://127.0.0.1:{port}/health") as response:
                        assert response.status == 200
                break
            except aiohttp.ClientError, OSError:
                await asyncio.sleep(0.05)
        else:
            raise AssertionError("mock profile-service did not start")
        client = ProfileServiceClient(base_url=f"http://127.0.0.1:{port}", timeout_seconds=2)
        user_id = uuid4()
        url = await client.authorization_url(state="opaque")
        linked = await client.complete(user_id=user_id, code="mock-code")
        listed = await client.list_accounts(user_id=user_id)
        fetched = await client.get_account(user_id=user_id, account_id=linked.id)
        await client.delete_account(user_id=user_id, account_id=linked.id)
        assert url == "https://hh.mock/oauth?state=opaque"
        assert listed == [linked]
        assert fetched == linked
    finally:
        process.terminate()
        await asyncio.wait_for(process.wait(), timeout=5)
