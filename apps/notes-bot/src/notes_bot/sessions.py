import sqlite3
from dataclasses import dataclass
from pathlib import Path

from cryptography.fernet import (
    Fernet,
    InvalidToken,
)

from notes_bot.database import open_database
from notes_bot.linking import (
    TelegramIdentity,
    current_timestamp,
    token_hash,
)


class SessionAlreadyLinked(RuntimeError):
    """Raised when a Supabase user is linked elsewhere."""


class SessionDecryptionError(RuntimeError):
    """Raised when an encrypted session cannot be decrypted."""


class LinkCompletionError(RuntimeError):
    """Raised when linking cannot be completed."""


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


def complete_linked_session(
    database_path: Path,
    cipher: TokenCipher,
    *,
    challenge_token: str,
    email: str,
    supabase_user_id: str,
    refresh_token: str,
    now: int | None = None,
) -> TelegramIdentity:
    normalized_user_id = supabase_user_id.strip()
    normalized_email = email.strip().casefold()

    if not normalized_user_id:
        raise ValueError("supabase_user_id must not be empty")

    if not normalized_email:
        raise ValueError("email must not be empty")

    timestamp = current_timestamp() if now is None else now
    hashed_token = token_hash(challenge_token)
    encrypted_refresh_token = cipher.encrypt(refresh_token)

    connection = open_database(database_path)

    try:
        connection.execute("BEGIN IMMEDIATE")

        challenge = connection.execute(
            """
            SELECT
                telegram_user_id,
                telegram_chat_id
            FROM link_challenges
            WHERE token_hash = ?
              AND auth_email = ?
              AND otp_requested_at IS NOT NULL
              AND failed_attempts < 5
              AND consumed_at IS NULL
              AND expires_at > ?
            """,
            (
                hashed_token,
                normalized_email,
                timestamp,
            ),
        ).fetchone()

        if challenge is None:
            raise LinkCompletionError(
                "Link is invalid, expired, or not ready for completion"
            )

        telegram_user_id = int(challenge["telegram_user_id"])

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
                supabase_user_id =
                    excluded.supabase_user_id,
                encrypted_refresh_token =
                    excluded.encrypted_refresh_token,
                updated_at =
                    excluded.updated_at
            """,
            (
                telegram_user_id,
                normalized_user_id,
                encrypted_refresh_token,
                timestamp,
                timestamp,
            ),
        )

        updated = connection.execute(
            """
            UPDATE link_challenges
            SET consumed_at = ?
            WHERE token_hash = ?
              AND consumed_at IS NULL
            """,
            (
                timestamp,
                hashed_token,
            ),
        )

        if updated.rowcount != 1:
            raise LinkCompletionError("Link was consumed concurrently")

        connection.commit()

        return TelegramIdentity(
            user_id=telegram_user_id,
            chat_id=int(challenge["telegram_chat_id"]),
        )
    except sqlite3.IntegrityError as error:
        connection.rollback()

        raise SessionAlreadyLinked(
            "Supabase account is already linked to another Telegram user"
        ) from error
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
