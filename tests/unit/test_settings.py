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


@pytest.mark.parametrize("value", [None, ""])
def test_main_be_service_key_is_required_and_non_empty(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, value: str | None
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PROFILE_SERVICE_URL", "http://profile.invalid")
    if value is None:
        monkeypatch.delenv("MAIN_BE_SERVICE_KEY", raising=False)
    else:
        monkeypatch.setenv("MAIN_BE_SERVICE_KEY", value)

    with pytest.raises(ValidationError, match="MAIN_BE_SERVICE_KEY"):
        Settings()


def test_main_be_service_key_accepts_valid_secret(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PROFILE_SERVICE_URL", "http://profile.invalid")
    monkeypatch.setenv("MAIN_BE_SERVICE_KEY", "runtime-test-secret")
    monkeypatch.setenv("VACANCY_SERVICE_URL", "http://vacancy.invalid")
    monkeypatch.setenv("VACANCY_SERVICE_TIMEOUT_SECONDS", "10")

    configured = Settings()

    assert configured.main_be_service_key.get_secret_value() == "runtime-test-secret"
    assert "runtime-test-secret" not in repr(configured.main_be_service_key)


@pytest.mark.parametrize("value", ["profile-service:8000", "ftp://profile-service/internal", "not a url"])
def test_profile_service_url_must_be_absolute_http_url(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, value: str
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PROFILE_SERVICE_URL", value)

    with pytest.raises(ValidationError, match="PROFILE_SERVICE_URL"):
        Settings()


def test_profile_service_client_uses_environment_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    overridden_url = "https://controlled-profile.example.test:9443/api"
    monkeypatch.setenv("PROFILE_SERVICE_URL", overridden_url)
    monkeypatch.setenv("VACANCY_SERVICE_URL", "http://vacancy.invalid")
    monkeypatch.setenv("VACANCY_SERVICE_TIMEOUT_SECONDS", "10")

    configured = Settings()
    client = ProfileServiceClient(
        base_url=str(configured.profile_service_url),
        timeout_seconds=configured.profile_service_timeout_seconds,
    )

    assert client.base_url == overridden_url
