import pytest

from notes_bot.config import (
    ConfigurationError,
    Settings,
    load_settings,
)


def test_load_settings_reads_bot_token() -> None:
    settings = load_settings(
        {
            "TELEGRAM_BOT_TOKEN": "  test-token  ",
        }
    )

    assert settings == Settings(
        telegram_bot_token="test-token",
    )


def test_load_settings_requires_bot_token() -> None:
    with pytest.raises(
        ConfigurationError,
        match="TELEGRAM_BOT_TOKEN",
    ):
        load_settings({})


def test_load_settings_rejects_blank_bot_token() -> None:
    with pytest.raises(
        ConfigurationError,
        match="TELEGRAM_BOT_TOKEN",
    ):
        load_settings(
            {
                "TELEGRAM_BOT_TOKEN": "   ",
            }
        )
