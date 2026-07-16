import asyncio
import os
import socket
from pathlib import Path
from uuid import uuid4

import aiohttp
import pytest

from infrastructure import ProfileServiceClient

pytestmark = [pytest.mark.infrastructure, pytest.mark.asyncio]


def _profile_service_paths() -> tuple[Path, Path]:
    workspace_profile_root = Path(__file__).parents[3] / "profile-service"
    profile_root = Path(os.environ.get("PROFILE_SERVICE_ROOT", workspace_profile_root)).expanduser().resolve()
    profile_python = Path(os.environ.get("PROFILE_SERVICE_PYTHON", profile_root / ".venv/bin/python")).expanduser()
    return profile_root, profile_python


async def test_main_be_client_to_real_profile_routes_with_mock_hh() -> None:
    profile_root, profile_python = _profile_service_paths()
    if not (profile_root / "tests/mock_hh_app.py").is_file():
        pytest.fail(
            "Не найден profile-service с tests/mock_hh_app.py. "
            "Задайте PROFILE_SERVICE_ROOT или разместите checkout в HAIntly workspace."
        )
    if not profile_python.is_file():
        pytest.fail(
            "Не найден Python profile-service. Установите зависимости сервиса или задайте PROFILE_SERVICE_PYTHON."
        )
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
        str(profile_python),
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
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        for _ in range(100):
            if process.returncode is not None:
                stderr = await process.stderr.read() if process.stderr else b""
                pytest.fail(f"mock profile-service завершился при запуске: {stderr.decode().strip()}")
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
        if process.returncode is None:
            process.terminate()
            await asyncio.wait_for(process.wait(), timeout=5)
