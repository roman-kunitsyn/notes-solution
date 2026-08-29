from pathlib import Path

import pytest

from notes_cli.config import (
    ConfigurationError,
    Settings,
    load_settings,
    read_saved_settings,
    remove_settings,
    save_settings,
)


def example_settings() -> Settings:
    return Settings(
        supabase_url="http://127.0.0.1:8000/",
        publishable_key="sb_publishable_example_12345678",
    )


def test_settings_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "config.json"

    save_settings(example_settings(), path)

    assert read_saved_settings(path) == Settings(
        supabase_url="http://127.0.0.1:8000",
        publishable_key="sb_publishable_example_12345678",
    )
    assert path.stat().st_mode & 0o777 == 0o600


def test_environment_overrides_saved_settings(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    save_settings(example_settings(), path)

    settings = load_settings(
        path=path,
        environ={
            "SUPABASE_URL": "https://api.example.test",
            "SUPABASE_PUBLISHABLE_KEY": ("sb_publishable_override_12345678"),
        },
    )

    assert settings.supabase_url == "https://api.example.test"
    assert settings.publishable_key == "sb_publishable_override_12345678"


@pytest.mark.parametrize(
    "key",
    [
        "sb_secret_forbidden_12345678",
        "eyJlegacy-service-role-token",
        "plain-text-key",
    ],
)
def test_rejects_non_publishable_keys(
    tmp_path: Path,
    key: str,
) -> None:
    with pytest.raises(ConfigurationError):
        save_settings(
            Settings(
                supabase_url="http://127.0.0.1:8000",
                publishable_key=key,
            ),
            tmp_path / "config.json",
        )


def test_remove_missing_settings_is_safe(tmp_path: Path) -> None:
    remove_settings(tmp_path / "missing.json")
