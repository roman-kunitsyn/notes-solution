import hashlib
import secrets
import time
from dataclasses import dataclass
from pathlib import Path

from notes_bot.database import open_database

DEFAULT_CHALLENGE_TTL = 10 * 60


@dataclass(frozen=True)
class IssuedLinkChallenge:
    token: str
    expires_at: int


@dataclass(frozen=True)
class TelegramIdentity:
    user_id: int
    chat_id: int


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def current_timestamp() -> int:
    return int(time.time())


def create_link_challenge(
    database_path: Path,
    *,
    telegram_user_id: int,
    telegram_chat_id: int,
    now: int | None = None,
    ttl: int = DEFAULT_CHALLENGE_TTL,
) -> IssuedLinkChallenge:
    if telegram_user_id <= 0:
        raise ValueError("telegram_user_id must be positive")

    if telegram_chat_id <= 0:
        raise ValueError("telegram_chat_id must be positive")

    if ttl <= 0:
        raise ValueError("ttl must be positive")

    created_at = current_timestamp() if now is None else now
    expires_at = created_at + ttl

    # 32 random bytes become a 43-character base64url token.
    token = secrets.token_urlsafe(32)
    hashed_token = token_hash(token)

    with open_database(database_path) as connection:
        # Issuing a new link invalidates all older unused links
        # for the same Telegram user.
        connection.execute(
            """
            UPDATE link_challenges
            SET consumed_at = ?
            WHERE telegram_user_id = ?
              AND consumed_at IS NULL
            """,
            (
                created_at,
                telegram_user_id,
            ),
        )

        connection.execute(
            """
            INSERT INTO link_challenges (
                token_hash,
                telegram_user_id,
                telegram_chat_id,
                created_at,
                expires_at,
                consumed_at
            )
            VALUES (?, ?, ?, ?, ?, NULL)
            """,
            (
                hashed_token,
                telegram_user_id,
                telegram_chat_id,
                created_at,
                expires_at,
            ),
        )

    return IssuedLinkChallenge(
        token=token,
        expires_at=expires_at,
    )


def consume_link_challenge(
    database_path: Path,
    token: str,
    *,
    now: int | None = None,
) -> TelegramIdentity | None:
    consumed_at = current_timestamp() if now is None else now
    hashed_token = token_hash(token)

    connection = open_database(database_path)

    try:
        # IMMEDIATE prevents two callback requests from consuming
        # the same challenge concurrently.
        connection.execute("BEGIN IMMEDIATE")

        row = connection.execute(
            """
            SELECT
                telegram_user_id,
                telegram_chat_id
            FROM link_challenges
            WHERE token_hash = ?
              AND consumed_at IS NULL
              AND expires_at > ?
            """,
            (
                hashed_token,
                consumed_at,
            ),
        ).fetchone()

        if row is None:
            connection.rollback()
            return None

        connection.execute(
            """
            UPDATE link_challenges
            SET consumed_at = ?
            WHERE token_hash = ?
            """,
            (
                consumed_at,
                hashed_token,
            ),
        )

        connection.commit()

        return TelegramIdentity(
            user_id=int(row["telegram_user_id"]),
            chat_id=int(row["telegram_chat_id"]),
        )
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def delete_expired_challenges(
    database_path: Path,
    *,
    now: int | None = None,
) -> int:
    timestamp = current_timestamp() if now is None else now

    with open_database(database_path) as connection:
        cursor = connection.execute(
            """
            DELETE FROM link_challenges
            WHERE expires_at <= ?
            """,
            (timestamp,),
        )

        return cursor.rowcount


def inspect_link_challenge(
    database_path: Path,
    token: str,
    *,
    now: int | None = None,
) -> TelegramIdentity | None:
    timestamp = current_timestamp() if now is None else now
    hashed_token = token_hash(token)

    with open_database(database_path) as connection:
        row = connection.execute(
            """
            SELECT
                telegram_user_id,
                telegram_chat_id
            FROM link_challenges
            WHERE token_hash = ?
              AND consumed_at IS NULL
              AND expires_at > ?
            """,
            (
                hashed_token,
                timestamp,
            ),
        ).fetchone()

    if row is None:
        return None

    return TelegramIdentity(
        user_id=int(row["telegram_user_id"]),
        chat_id=int(row["telegram_chat_id"]),
    )
