import base64
import json
from pathlib import Path

import pytest

from notes_bot.config import (
    ConfigurationError,
    Settings,
    load_settings,
)


def encryption_key() -> str:
    return base64.urlsafe_b64encode(b"x" * 32).decode()


def legacy_key(role: str) -> str:
    payload = (
        base64.urlsafe_b64encode(json.dumps({"role": role}).encode())
        .decode()
        .rstrip("=")
    )

    return f"header.{payload}.signature"


def valid_environment() -> dict[str, str]:
    return {
        "TELEGRAM_BOT_TOKEN": "telegram-token",
        "SUPABASE_URL": "http://127.0.0.1:54321/",
        "SUPABASE_PUBLISHABLE_KEY": "sb_publishable_test",
        "NOTES_BOT_BASE_URL": "http://127.0.0.1:8080/",
        "NOTES_BOT_ENCRYPTION_KEY": encryption_key(),
        "NOTES_BOT_DATABASE_PATH": "/tmp/notes-bot.sqlite3",
    }


def test_load_settings_reads_configuration() -> None:
    settings = load_settings(valid_environment())

    assert settings == Settings(
        telegram_bot_token="telegram-token",
        supabase_url="http://127.0.0.1:54321",
        supabase_publishable_key="sb_publishable_test",
        bot_base_url="http://127.0.0.1:8080",
        encryption_key=encryption_key(),
        database_path=Path("/tmp/notes-bot.sqlite3"),
        http_host="127.0.0.1",
        http_port=8080,
    )


def test_load_settings_reports_all_missing_values() -> None:
    with pytest.raises(ConfigurationError) as error:
        load_settings({})

    message = str(error.value)

    assert "TELEGRAM_BOT_TOKEN" in message
    assert "SUPABASE_URL" in message
    assert "SUPABASE_PUBLISHABLE_KEY" in message
    assert "NOTES_BOT_BASE_URL" in message
    assert "NOTES_BOT_ENCRYPTION_KEY" in message


def test_load_settings_accepts_legacy_anon_key() -> None:
    environment = valid_environment()
    environment["SUPABASE_PUBLISHABLE_KEY"] = legacy_key("anon")

    settings = load_settings(environment)

    assert settings.supabase_publishable_key == legacy_key("anon")


@pytest.mark.parametrize(
    "key",
    [
        "sb_secret_test",
        legacy_key("service_role"),
        "invalid-key",
    ],
)
def test_load_settings_rejects_privileged_key(
    key: str,
) -> None:
    environment = valid_environment()
    environment["SUPABASE_PUBLISHABLE_KEY"] = key

    with pytest.raises(
        ConfigurationError,
        match="service-role keys are forbidden",
    ):
        load_settings(environment)


def test_load_settings_rejects_public_http_callback() -> None:
    environment = valid_environment()
    environment["NOTES_BOT_BASE_URL"] = "http://notes.example.com"

    with pytest.raises(
        ConfigurationError,
        match="must use HTTPS",
    ):
        load_settings(environment)


def test_load_settings_accepts_public_https_callback() -> None:
    environment = valid_environment()
    environment["NOTES_BOT_BASE_URL"] = "https://notes.example.com/"

    settings = load_settings(environment)

    assert settings.bot_base_url == ("https://notes.example.com")


def test_load_settings_rejects_short_encryption_key() -> None:
    environment = valid_environment()
    environment["NOTES_BOT_ENCRYPTION_KEY"] = base64.urlsafe_b64encode(
        b"short"
    ).decode()

    with pytest.raises(
        ConfigurationError,
        match="exactly 32 bytes",
    ):
        load_settings(environment)


def test_load_settings_expands_database_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    environment = valid_environment()
    database_path = tmp_path / "data" / "notes.sqlite3"

    environment["NOTES_BOT_DATABASE_PATH"] = str(database_path)

    settings = load_settings(environment)

    assert settings.database_path == database_path


@pytest.mark.parametrize(
    "port",
    [
        "not-a-number",
        "0",
        "-1",
        "65536",
    ],
)
def test_load_settings_rejects_invalid_http_port(
    port: str,
) -> None:
    environment = valid_environment()
    environment["NOTES_BOT_HTTP_PORT"] = port

    with pytest.raises(
        ConfigurationError,
        match="NOTES_BOT_HTTP_PORT",
    ):
        load_settings(environment)


def test_load_settings_accepts_http_binding() -> None:
    environment = valid_environment()
    environment["NOTES_BOT_HTTP_HOST"] = "0.0.0.0"
    environment["NOTES_BOT_HTTP_PORT"] = "9000"

    settings = load_settings(environment)

    assert settings.http_host == "0.0.0.0"
    assert settings.http_port == 9000
