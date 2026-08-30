from dataclasses import dataclass
from pathlib import Path

from notes_bot.database import open_database
from notes_bot.linking import (
    TelegramIdentity,
    current_timestamp,
    token_hash,
)

OTP_REQUEST_COOLDOWN = 60
MAX_OTP_ATTEMPTS = 5


class InvalidLinkChallenge(RuntimeError):
    """Raised when a linking challenge is invalid."""


class ChallengeEmailMismatch(RuntimeError):
    """Raised when a different email is used."""


class OtpRequestTooSoon(RuntimeError):
    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after

        super().__init__("Wait before requesting another OTP")


class OtpNotRequested(RuntimeError):
    """Raised when verification starts before an OTP request."""


class OtpAttemptsExceeded(RuntimeError):
    """Raised after too many failed OTP attempts."""


@dataclass(frozen=True)
class OtpRequest:
    identity: TelegramIdentity
    email: str
    requested_at: int


@dataclass(frozen=True)
class OtpVerification:
    identity: TelegramIdentity
    email: str
    attempts_remaining: int


def normalize_email(email: str) -> str:
    normalized = email.strip().casefold()

    if (
        not normalized
        or len(normalized) > 320
        or "@" not in normalized
        or any(character.isspace() for character in normalized)
    ):
        raise ValueError("Invalid email address")

    return normalized


def reserve_otp_request(
    database_path: Path,
    token: str,
    email: str,
    *,
    now: int | None = None,
    cooldown: int = OTP_REQUEST_COOLDOWN,
) -> OtpRequest:
    timestamp = current_timestamp() if now is None else now
    normalized_email = normalize_email(email)
    hashed_token = token_hash(token)

    connection = open_database(database_path)

    try:
        connection.execute("BEGIN IMMEDIATE")

        row = connection.execute(
            """
            SELECT
                telegram_user_id,
                telegram_chat_id,
                auth_email,
                otp_requested_at,
                failed_attempts
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
            raise InvalidLinkChallenge("Link is invalid or expired")

        existing_email = row["auth_email"]

        if existing_email is not None and str(existing_email) != normalized_email:
            raise ChallengeEmailMismatch(
                "This link is already associated with another email"
            )

        failed_attempts = int(row["failed_attempts"])

        if failed_attempts >= MAX_OTP_ATTEMPTS:
            raise OtpAttemptsExceeded("Too many failed OTP attempts")

        previous_request = row["otp_requested_at"]

        if previous_request is not None:
            elapsed = timestamp - int(previous_request)

            if elapsed < cooldown:
                raise OtpRequestTooSoon(retry_after=cooldown - elapsed)

        connection.execute(
            """
            UPDATE link_challenges
            SET
                auth_email = ?,
                otp_requested_at = ?
            WHERE token_hash = ?
            """,
            (
                normalized_email,
                timestamp,
                hashed_token,
            ),
        )

        connection.commit()

        return OtpRequest(
            identity=TelegramIdentity(
                user_id=int(row["telegram_user_id"]),
                chat_id=int(row["telegram_chat_id"]),
            ),
            email=normalized_email,
            requested_at=timestamp,
        )
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def release_otp_request(
    database_path: Path,
    token: str,
    *,
    requested_at: int,
) -> bool:
    hashed_token = token_hash(token)

    with open_database(database_path) as connection:
        cursor = connection.execute(
            """
            UPDATE link_challenges
            SET otp_requested_at = NULL
            WHERE token_hash = ?
              AND otp_requested_at = ?
              AND consumed_at IS NULL
            """,
            (
                hashed_token,
                requested_at,
            ),
        )

        return cursor.rowcount == 1


def get_otp_verification(
    database_path: Path,
    token: str,
    email: str,
    *,
    now: int | None = None,
) -> OtpVerification:
    timestamp = current_timestamp() if now is None else now
    normalized_email = normalize_email(email)
    hashed_token = token_hash(token)

    with open_database(database_path) as connection:
        row = connection.execute(
            """
            SELECT
                telegram_user_id,
                telegram_chat_id,
                auth_email,
                otp_requested_at,
                failed_attempts
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
        raise InvalidLinkChallenge("Link is invalid or expired")

    stored_email = row["auth_email"]

    if stored_email is None or str(stored_email) != normalized_email:
        raise ChallengeEmailMismatch("Email does not match this link")

    if row["otp_requested_at"] is None:
        raise OtpNotRequested("Request an OTP before verification")

    failed_attempts = int(row["failed_attempts"])

    if failed_attempts >= MAX_OTP_ATTEMPTS:
        raise OtpAttemptsExceeded("Too many failed OTP attempts")

    return OtpVerification(
        identity=TelegramIdentity(
            user_id=int(row["telegram_user_id"]),
            chat_id=int(row["telegram_chat_id"]),
        ),
        email=normalized_email,
        attempts_remaining=(MAX_OTP_ATTEMPTS - failed_attempts),
    )


def record_failed_otp_attempt(
    database_path: Path,
    token: str,
    *,
    now: int | None = None,
) -> int:
    timestamp = current_timestamp() if now is None else now
    hashed_token = token_hash(token)

    connection = open_database(database_path)

    try:
        connection.execute("BEGIN IMMEDIATE")

        row = connection.execute(
            """
            SELECT failed_attempts
            FROM link_challenges
            WHERE token_hash = ?
              AND consumed_at IS NULL
              AND expires_at > ?
              AND otp_requested_at IS NOT NULL
            """,
            (
                hashed_token,
                timestamp,
            ),
        ).fetchone()

        if row is None:
            raise InvalidLinkChallenge("Link is invalid or expired")

        failed_attempts = int(row["failed_attempts"]) + 1
        attempts_remaining = max(
            0,
            MAX_OTP_ATTEMPTS - failed_attempts,
        )

        if attempts_remaining == 0:
            connection.execute(
                """
                UPDATE link_challenges
                SET
                    failed_attempts = ?,
                    consumed_at = ?
                WHERE token_hash = ?
                """,
                (
                    failed_attempts,
                    timestamp,
                    hashed_token,
                ),
            )
        else:
            connection.execute(
                """
                UPDATE link_challenges
                SET failed_attempts = ?
                WHERE token_hash = ?
                """,
                (
                    failed_attempts,
                    hashed_token,
                ),
            )

        connection.commit()

        return attempts_remaining
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
