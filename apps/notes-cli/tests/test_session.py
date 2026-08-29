from pathlib import Path

from notes_cli.session import (
    SessionTokens,
    load_session,
    remove_session,
    save_session,
)


def test_session_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "session.json"
    expected = SessionTokens(
        access_token="access-token",
        refresh_token="refresh-token",
    )

    save_session(expected, path)

    assert load_session(path) == expected
    assert path.stat().st_mode & 0o777 == 0o600


def test_remove_missing_session_is_safe(tmp_path: Path) -> None:
    path = tmp_path / "missing.json"

    remove_session(path)

    assert not path.exists()
