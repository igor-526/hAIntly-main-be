from pathlib import Path

import pytest
from pydantic import ValidationError

from infrastructure import ProfileServiceClient
from settings import Settings


def test_profile_service_url_is_required(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PROFILE_SERVICE_URL", raising=False)

    with pytest.raises(ValidationError, match="PROFILE_SERVICE_URL"):
        Settings()


@pytest.mark.parametrize("value", ["profile-service:8000", "ftp://profile-service/internal", "not a url"])
def test_profile_service_url_must_be_absolute_http_url(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, value: str
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PROFILE_SERVICE_URL", value)

    with pytest.raises(ValidationError, match="PROFILE_SERVICE_URL"):
        Settings()


def test_profile_service_client_uses_environment_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    overridden_url = "https://controlled-profile.example.test:9443/api"
    monkeypatch.setenv("PROFILE_SERVICE_URL", overridden_url)

    configured = Settings()
    client = ProfileServiceClient(
        base_url=str(configured.profile_service_url),
        timeout_seconds=configured.profile_service_timeout_seconds,
    )

    assert client.base_url == overridden_url
