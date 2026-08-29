import base64
import json
import os
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path

from platformdirs import user_config_path


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    publishable_key: str


class ConfigurationError(RuntimeError):
    pass


def settings_path() -> Path:
    override = os.getenv("NOTES_CLI_CONFIG_DIR")

    if override:
        return Path(override).expanduser() / "config.json"

    return (
        user_config_path(
            appname="notes-cli",
            appauthor=False,
        )
        / "config.json"
    )


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

    # The local Supabase CLI still exposes the legacy anon JWT.
    # Decoding here is only a safety check against accidentally supplying a
    # service-role key. Authorization remains enforced by Supabase and RLS.
    return jwt_role(key) == "anon"


def validate_settings(settings: Settings) -> Settings:
    url = settings.supabase_url.strip().rstrip("/")
    key = settings.publishable_key.strip()

    if not url.startswith(("http://", "https://")):
        raise ConfigurationError("Supabase URL must start with http:// or https://")

    if not is_publishable_key(key):
        raise ConfigurationError(
            "Expected an sb_publishable_ key or legacy anon key. "
            "Secret and service-role keys are forbidden."
        )

    return Settings(
        supabase_url=url,
        publishable_key=key,
    )


def read_saved_settings(
    path: Path | None = None,
) -> Settings | None:
    target = path or settings_path()

    if not target.exists():
        return None

    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        settings = Settings(
            supabase_url=str(data["supabase_url"]),
            publishable_key=str(data["publishable_key"]),
        )
    except (OSError, KeyError, TypeError, ValueError) as error:
        raise ConfigurationError(f"Invalid configuration file: {target}") from error

    return validate_settings(settings)


def save_settings(
    settings: Settings,
    path: Path | None = None,
) -> None:
    validated = validate_settings(settings)
    target = path or settings_path()

    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)

    descriptor = os.open(
        target,
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
        0o600,
    )

    with os.fdopen(descriptor, "w", encoding="utf-8") as file:
        json.dump(asdict(validated), file)

    target.chmod(0o600)


def remove_settings(path: Path | None = None) -> None:
    target = path or settings_path()
    target.unlink(missing_ok=True)


def load_settings(
    *,
    path: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> Settings:
    environment = environ if environ is not None else os.environ
    saved = read_saved_settings(path)

    supabase_url = environment.get(
        "SUPABASE_URL",
        saved.supabase_url if saved else "",
    )

    publishable_key = environment.get(
        "SUPABASE_PUBLISHABLE_KEY",
        saved.publishable_key if saved else "",
    )

    missing = []

    if not supabase_url.strip():
        missing.append("SUPABASE_URL")

    if not publishable_key.strip():
        missing.append("SUPABASE_PUBLISHABLE_KEY")

    if missing:
        names = ", ".join(missing)
        raise ConfigurationError(
            f"Missing configuration: {names}. Run: notes config set"
        )

    return validate_settings(
        Settings(
            supabase_url=supabase_url,
            publishable_key=publishable_key,
        )
    )
