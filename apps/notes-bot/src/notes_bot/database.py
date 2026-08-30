import sqlite3
import stat
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

SCHEMA_VERSION = 2


class DatabaseVersionError(RuntimeError):
    """Raised when the database schema is newer than the application."""


MIGRATION_1 = """
BEGIN;

CREATE TABLE link_challenges (
    token_hash TEXT PRIMARY KEY
        CHECK (length(token_hash) = 64),

    telegram_user_id INTEGER NOT NULL,
    telegram_chat_id INTEGER NOT NULL,

    created_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,
    consumed_at INTEGER,

    CHECK (expires_at > created_at),
    CHECK (
        consumed_at IS NULL
        OR consumed_at >= created_at
    )
);

CREATE INDEX link_challenges_expires_at_idx
    ON link_challenges (expires_at);

CREATE TABLE linked_sessions (
    telegram_user_id INTEGER PRIMARY KEY,
    supabase_user_id TEXT NOT NULL UNIQUE,
    encrypted_refresh_token BLOB NOT NULL,

    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,

    CHECK (updated_at >= created_at)
);

PRAGMA user_version = 1;

COMMIT;
"""

MIGRATION_2 = """
BEGIN;

ALTER TABLE link_challenges
    ADD COLUMN auth_email TEXT;

ALTER TABLE link_challenges
    ADD COLUMN otp_requested_at INTEGER;

ALTER TABLE link_challenges
    ADD COLUMN failed_attempts INTEGER
        NOT NULL
        DEFAULT 0
        CHECK (failed_attempts >= 0);

PRAGMA user_version = 2;

COMMIT;
"""


def configure_connection(
    connection: sqlite3.Connection,
) -> None:
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    connection.execute("PRAGMA journal_mode = WAL")


def migrate_database(
    connection: sqlite3.Connection,
) -> None:
    version = connection.execute("PRAGMA user_version").fetchone()[0]

    if version > SCHEMA_VERSION:
        raise DatabaseVersionError(
            "Database schema version "
            f"{version} is newer than supported version "
            f"{SCHEMA_VERSION}"
        )

    if version == 0:
        connection.executescript(MIGRATION_1)
        version = 1

    if version == 1:
        connection.executescript(MIGRATION_2)


def open_database(
    path: Path,
) -> sqlite3.Connection:
    path.parent.mkdir(
        mode=0o700,
        parents=True,
        exist_ok=True,
    )
    path.parent.chmod(0o700)

    connection = sqlite3.connect(
        path,
        timeout=5,
    )

    try:
        configure_connection(connection)
        migrate_database(connection)
        path.chmod(0o600)
    except Exception:
        connection.close()
        raise

    return connection


@contextmanager
def database_connection(
    path: Path,
) -> Iterator[sqlite3.Connection]:
    connection = open_database(path)

    try:
        with connection:
            yield connection
    finally:
        connection.close()


def database_permissions(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)
