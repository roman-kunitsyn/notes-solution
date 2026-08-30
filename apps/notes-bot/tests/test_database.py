import sqlite3
from pathlib import Path

import pytest

from notes_bot.database import (
    MIGRATION_1,
    SCHEMA_VERSION,
    DatabaseVersionError,
    database_permissions,
    open_database,
)


def table_names(
    connection: sqlite3.Connection,
) -> set[str]:
    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        """
    ).fetchall()

    return {str(row["name"]) for row in rows}


def column_names(
    connection: sqlite3.Connection,
    table: str,
) -> set[str]:
    rows = connection.execute(f"PRAGMA table_info({table})").fetchall()

    return {str(row["name"]) for row in rows}


def test_open_database_creates_schema(
    tmp_path: Path,
) -> None:
    path = tmp_path / "data" / "notes-bot.sqlite3"

    with open_database(path) as connection:
        version = connection.execute("PRAGMA user_version").fetchone()[0]

        assert version == SCHEMA_VERSION
        assert table_names(connection) == {
            "link_challenges",
            "linked_sessions",
        }


def test_open_database_is_idempotent(
    tmp_path: Path,
) -> None:
    path = tmp_path / "notes-bot.sqlite3"

    with open_database(path):
        pass

    with open_database(path) as connection:
        version = connection.execute("PRAGMA user_version").fetchone()[0]

    assert version == SCHEMA_VERSION


def test_open_database_uses_restrictive_permissions(
    tmp_path: Path,
) -> None:
    path = tmp_path / "private" / "notes-bot.sqlite3"

    with open_database(path):
        pass

    assert database_permissions(path) == 0o600
    assert database_permissions(path.parent) == 0o700


def test_open_database_enables_foreign_keys(
    tmp_path: Path,
) -> None:
    path = tmp_path / "notes-bot.sqlite3"

    with open_database(path) as connection:
        enabled = connection.execute("PRAGMA foreign_keys").fetchone()[0]

    assert enabled == 1


def test_open_database_rejects_newer_schema(
    tmp_path: Path,
) -> None:
    path = tmp_path / "notes-bot.sqlite3"

    connection = sqlite3.connect(path)
    connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION + 1}")
    connection.close()

    with pytest.raises(
        DatabaseVersionError,
        match="newer than supported",
    ):
        open_database(path)


def test_link_challenges_has_auth_state(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"

    with open_database(path) as connection:
        columns = column_names(
            connection,
            "link_challenges",
        )

    assert {
        "auth_email",
        "otp_requested_at",
        "failed_attempts",
    } <= columns


def test_open_database_upgrades_version_one(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"

    connection = sqlite3.connect(path)
    connection.executescript(MIGRATION_1)
    connection.close()

    with open_database(path) as connection:
        version = connection.execute("PRAGMA user_version").fetchone()[0]

        columns = column_names(
            connection,
            "link_challenges",
        )

    assert version == SCHEMA_VERSION
    assert {
        "auth_email",
        "otp_requested_at",
        "failed_attempts",
    } <= columns
