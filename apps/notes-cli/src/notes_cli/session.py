import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from platformdirs import user_config_path


@dataclass(frozen=True)
class SessionTokens:
    access_token: str
    refresh_token: str


def session_path() -> Path:
    override = os.getenv("NOTES_CLI_CONFIG_DIR")

    if override:
        return Path(override).expanduser() / "session.json"

    return (
        user_config_path(
            appname="notes-cli",
            appauthor=False,
        )
        / "session.json"
    )


def save_session(
    tokens: SessionTokens,
    path: Path | None = None,
) -> None:
    target = path or session_path()
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)

    descriptor = os.open(
        target,
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
        0o600,
    )

    with os.fdopen(descriptor, "w", encoding="utf-8") as file:
        json.dump(asdict(tokens), file)

    target.chmod(0o600)


def load_session(path: Path | None = None) -> SessionTokens | None:
    target = path or session_path()

    if not target.exists():
        return None

    data = json.loads(target.read_text(encoding="utf-8"))

    return SessionTokens(
        access_token=data["access_token"],
        refresh_token=data["refresh_token"],
    )


def remove_session(path: Path | None = None) -> None:
    target = path or session_path()
    target.unlink(missing_ok=True)
