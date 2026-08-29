import os
from collections.abc import Mapping
from dataclasses import dataclass


class ConfigurationError(RuntimeError):
    """Raised when the bot configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str


def load_settings(
    environ: Mapping[str, str] | None = None,
) -> Settings:
    environment = environ if environ is not None else os.environ
    telegram_bot_token = environment.get(
        "TELEGRAM_BOT_TOKEN",
        "",
    ).strip()

    if not telegram_bot_token:
        raise ConfigurationError("Missing configuration: TELEGRAM_BOT_TOKEN")

    return Settings(
        telegram_bot_token=telegram_bot_token,
    )
