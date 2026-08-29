import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    publishable_key: str


class ConfigurationError(RuntimeError):
    pass


def load_settings() -> Settings:
    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    publishable_key = os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip()

    missing = []

    if not supabase_url:
        missing.append("SUPABASE_URL")

    if not publishable_key:
        missing.append("SUPABASE_PUBLISHABLE_KEY")

    if missing:
        names = ", ".join(missing)
        raise ConfigurationError(f"Missing environment variables: {names}")

    return Settings(
        supabase_url=supabase_url.rstrip("/"),
        publishable_key=publishable_key,
    )
