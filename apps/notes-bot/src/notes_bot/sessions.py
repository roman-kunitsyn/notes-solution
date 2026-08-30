import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from cryptography.fernet import (
    Fernet,
    InvalidToken,
)

from notes_bot.database import open_database


class SessionAlreadyLinked(RuntimeError):
    """Raised when a Supabase user is linked elsewhere."""


class SessionDecryptionError(RuntimeError):
    """Raised when an encrypted session cannot be decrypted."""


@dataclass(frozen=True)
class LinkedSession:
    telegram_user_id: int
    supabase_user_id: str
    refresh_token: str
    created_at: int
    updated_at: int


class TokenCipher:
    def __init__(self, encryption_key: str) -> None:
        self._fernet = Fernet(encryption_key.encode("ascii"))

    def encrypt(self, value: str) -> bytes:
        if not value:
            raise ValueError("Value to encrypt must not be empty")

        return self._fernet.encrypt(value.encode("utf-8"))

    def decrypt(self, value: bytes) -> str:
        try:
            plaintext = self._fernet.decrypt(value)
        except InvalidToken as error:
            raise SessionDecryptionError(
                "Stored session could not be decrypted"
            ) from error

        return plaintext.decode("utf-8")


def current_timestamp() -> int:
    return int(time.time())


def save_linked_session(
    database_path: Path,
    cipher: TokenCipher,
    *,
    telegram_user_id: int,
    supabase_user_id: str,
    refresh_token: str,
    now: int | None = None,
) -> None:
    if telegram_user_id <= 0:
        raise ValueError("telegram_user_id must be positive")

    normalized_user_id = supabase_user_id.strip()

    if not normalized_user_id:
        raise ValueError("supabase_user_id must not be empty")

    timestamp = current_timestamp() if now is None else now
    encrypted_refresh_token = cipher.encrypt(refresh_token)

    try:
        with open_database(database_path) as connection:
            connection.execute(
                """
                INSERT INTO linked_sessions (
                    telegram_user_id,
                    supabase_user_id,
                    encrypted_refresh_token,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (telegram_user_id)
                DO UPDATE SET
                    supabase_user_id = excluded.supabase_user_id,
                    encrypted_refresh_token =
                        excluded.encrypted_refresh_token,
                    updated_at = excluded.updated_at
                """,
                (
                    telegram_user_id,
                    normalized_user_id,
                    encrypted_refresh_token,
                    timestamp,
                    timestamp,
                ),
            )
    except sqlite3.IntegrityError as error:
        raise SessionAlreadyLinked(
            "Supabase account is already linked to another Telegram user"
        ) from error


def load_linked_session(
    database_path: Path,
    cipher: TokenCipher,
    *,
    telegram_user_id: int,
) -> LinkedSession | None:
    with open_database(database_path) as connection:
        row = connection.execute(
            """
            SELECT
                telegram_user_id,
                supabase_user_id,
                encrypted_refresh_token,
                created_at,
                updated_at
            FROM linked_sessions
            WHERE telegram_user_id = ?
            """,
            (telegram_user_id,),
        ).fetchone()

    if row is None:
        return None

    return LinkedSession(
        telegram_user_id=int(row["telegram_user_id"]),
        supabase_user_id=str(row["supabase_user_id"]),
        refresh_token=cipher.decrypt(bytes(row["encrypted_refresh_token"])),
        created_at=int(row["created_at"]),
        updated_at=int(row["updated_at"]),
    )


def replace_refresh_token(
    database_path: Path,
    cipher: TokenCipher,
    *,
    telegram_user_id: int,
    refresh_token: str,
    now: int | None = None,
) -> bool:
    timestamp = current_timestamp() if now is None else now
    encrypted_refresh_token = cipher.encrypt(refresh_token)

    with open_database(database_path) as connection:
        cursor = connection.execute(
            """
            UPDATE linked_sessions
            SET
                encrypted_refresh_token = ?,
                updated_at = ?
            WHERE telegram_user_id = ?
            """,
            (
                encrypted_refresh_token,
                timestamp,
                telegram_user_id,
            ),
        )

        return cursor.rowcount == 1


def delete_linked_session(
    database_path: Path,
    *,
    telegram_user_id: int,
) -> bool:
    with open_database(database_path) as connection:
        cursor = connection.execute(
            """
            DELETE FROM linked_sessions
            WHERE telegram_user_id = ?
            """,
            (telegram_user_id,),
        )

        return cursor.rowcount == 1
