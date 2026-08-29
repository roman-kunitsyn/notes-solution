import base64
import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlsplit


class ConfigurationError(RuntimeError):
    """Raised when the bot configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    supabase_url: str
    supabase_publishable_key: str
    bot_base_url: str
    encryption_key: str


def jwt_role(key: str) -> str | None:
    try:
        parts = key.split(".")

        if len(parts) != 3:
            return None

        payload = parts[1]
        padding = "=" * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload + padding)
        data = json.loads(decoded)

        role = data.get("role")

        return str(role) if role is not None else None
    except ValueError, UnicodeDecodeError, json.JSONDecodeError:
        return None


def is_publishable_key(key: str) -> bool:
    if key.startswith("sb_publishable_"):
        return True

    # Local Supabase currently exposes a legacy anon JWT.
    return jwt_role(key) == "anon"


def validate_supabase_url(value: str) -> str:
    url = value.strip().rstrip("/")
    parsed = urlsplit(url)

    if parsed.scheme not in {"http", "https"}:
        raise ConfigurationError("SUPABASE_URL must start with http:// or https://")

    if not parsed.hostname:
        raise ConfigurationError("SUPABASE_URL must include a hostname")

    return url


def validate_bot_base_url(value: str) -> str:
    url = value.strip().rstrip("/")
    parsed = urlsplit(url)

    if parsed.scheme not in {"http", "https"}:
        raise ConfigurationError(
            "NOTES_BOT_BASE_URL must start with http:// or https://"
        )

    if not parsed.hostname:
        raise ConfigurationError("NOTES_BOT_BASE_URL must include a hostname")

    if parsed.username or parsed.password:
        raise ConfigurationError("NOTES_BOT_BASE_URL must not contain credentials")

    if parsed.query or parsed.fragment:
        raise ConfigurationError(
            "NOTES_BOT_BASE_URL must not contain a query or fragment"
        )

    local_hosts = {
        "127.0.0.1",
        "::1",
        "localhost",
    }

    if parsed.scheme == "http" and parsed.hostname not in local_hosts:
        raise ConfigurationError(
            "NOTES_BOT_BASE_URL must use HTTPS unless it points to localhost"
        )

    return url


def validate_encryption_key(value: str) -> str:
    key = value.strip()

    try:
        decoded = base64.urlsafe_b64decode(key)
    except ValueError as error:
        raise ConfigurationError(
            "NOTES_BOT_ENCRYPTION_KEY must be URL-safe base64"
        ) from error

    if len(decoded) != 32:
        raise ConfigurationError(
            "NOTES_BOT_ENCRYPTION_KEY must encode exactly 32 bytes"
        )

    return key


def load_settings(
    environ: Mapping[str, str] | None = None,
) -> Settings:
    environment = environ if environ is not None else os.environ

    required_names = (
        "TELEGRAM_BOT_TOKEN",
        "SUPABASE_URL",
        "SUPABASE_PUBLISHABLE_KEY",
        "NOTES_BOT_BASE_URL",
        "NOTES_BOT_ENCRYPTION_KEY",
    )

    values = {name: environment.get(name, "").strip() for name in required_names}

    missing = [name for name, value in values.items() if not value]

    if missing:
        raise ConfigurationError(f"Missing configuration: {', '.join(missing)}")

    publishable_key = values["SUPABASE_PUBLISHABLE_KEY"]

    if not is_publishable_key(publishable_key):
        raise ConfigurationError(
            "Expected an sb_publishable_ key or legacy anon key. "
            "Secret and service-role keys are forbidden."
        )

    return Settings(
        telegram_bot_token=values["TELEGRAM_BOT_TOKEN"],
        supabase_url=validate_supabase_url(values["SUPABASE_URL"]),
        supabase_publishable_key=publishable_key,
        bot_base_url=validate_bot_base_url(values["NOTES_BOT_BASE_URL"]),
        encryption_key=validate_encryption_key(values["NOTES_BOT_ENCRYPTION_KEY"]),
    )
