from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from notes_bot.database import database_connection
from notes_bot.linking import (
    consume_link_challenge,
    create_link_challenge,
)
from notes_bot.otp_state import (
    get_otp_verification,
    reserve_otp_request,
)
from notes_bot.sessions import (
    LinkCompletionError,
    SessionAlreadyLinked,
    SessionDecryptionError,
    TokenCipher,
    complete_linked_session,
    delete_linked_session,
    load_linked_session,
    replace_refresh_token,
    save_linked_session,
)


def create_cipher() -> TokenCipher:
    return TokenCipher(Fernet.generate_key().decode("ascii"))


def test_save_and_load_linked_session(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"
    cipher = create_cipher()

    save_linked_session(
        path,
        cipher,
        telegram_user_id=100,
        supabase_user_id="supabase-user-1",
        refresh_token="refresh-token-1",
        now=1_000,
    )

    session = load_linked_session(
        path,
        cipher,
        telegram_user_id=100,
    )

    assert session is not None
    assert session.telegram_user_id == 100
    assert session.supabase_user_id == ("supabase-user-1")
    assert session.refresh_token == "refresh-token-1"
    assert session.created_at == 1_000
    assert session.updated_at == 1_000


def test_refresh_token_is_not_stored_as_plaintext(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"
    cipher = create_cipher()
    plaintext = "very-secret-refresh-token"

    save_linked_session(
        path,
        cipher,
        telegram_user_id=100,
        supabase_user_id="supabase-user-1",
        refresh_token=plaintext,
        now=1_000,
    )

    with database_connection(path) as connection:
        row = connection.execute(
            """
            SELECT encrypted_refresh_token
            FROM linked_sessions
            WHERE telegram_user_id = ?
            """,
            (100,),
        ).fetchone()

    stored_value = bytes(row["encrypted_refresh_token"])

    assert stored_value != plaintext.encode()
    assert plaintext.encode() not in stored_value


def test_save_updates_existing_telegram_link(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"
    cipher = create_cipher()

    save_linked_session(
        path,
        cipher,
        telegram_user_id=100,
        supabase_user_id="supabase-user-1",
        refresh_token="old-token",
        now=1_000,
    )
    save_linked_session(
        path,
        cipher,
        telegram_user_id=100,
        supabase_user_id="supabase-user-1",
        refresh_token="new-token",
        now=2_000,
    )

    session = load_linked_session(
        path,
        cipher,
        telegram_user_id=100,
    )

    assert session is not None
    assert session.refresh_token == "new-token"
    assert session.created_at == 1_000
    assert session.updated_at == 2_000


def test_supabase_user_cannot_link_two_telegram_users(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"
    cipher = create_cipher()

    save_linked_session(
        path,
        cipher,
        telegram_user_id=100,
        supabase_user_id="supabase-user-1",
        refresh_token="first-token",
        now=1_000,
    )

    with pytest.raises(
        SessionAlreadyLinked,
        match="already linked",
    ):
        save_linked_session(
            path,
            cipher,
            telegram_user_id=200,
            supabase_user_id="supabase-user-1",
            refresh_token="second-token",
            now=1_001,
        )


def test_replace_refresh_token(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"
    cipher = create_cipher()

    save_linked_session(
        path,
        cipher,
        telegram_user_id=100,
        supabase_user_id="supabase-user-1",
        refresh_token="old-token",
        now=1_000,
    )

    replaced = replace_refresh_token(
        path,
        cipher,
        telegram_user_id=100,
        refresh_token="new-token",
        now=2_000,
    )

    session = load_linked_session(
        path,
        cipher,
        telegram_user_id=100,
    )

    assert replaced is True
    assert session is not None
    assert session.refresh_token == "new-token"
    assert session.updated_at == 2_000


def test_replace_refresh_token_reports_missing_session(
    tmp_path: Path,
) -> None:
    replaced = replace_refresh_token(
        tmp_path / "bot.sqlite3",
        create_cipher(),
        telegram_user_id=100,
        refresh_token="new-token",
        now=1_000,
    )

    assert replaced is False


def test_delete_linked_session(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"
    cipher = create_cipher()

    save_linked_session(
        path,
        cipher,
        telegram_user_id=100,
        supabase_user_id="supabase-user-1",
        refresh_token="refresh-token",
        now=1_000,
    )

    deleted = delete_linked_session(
        path,
        telegram_user_id=100,
    )

    assert deleted is True
    assert (
        load_linked_session(
            path,
            cipher,
            telegram_user_id=100,
        )
        is None
    )


def test_corrupted_session_cannot_be_decrypted(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"
    cipher = create_cipher()

    save_linked_session(
        path,
        cipher,
        telegram_user_id=100,
        supabase_user_id="supabase-user-1",
        refresh_token="refresh-token",
        now=1_000,
    )

    with database_connection(path) as connection:
        connection.execute(
            """
            UPDATE linked_sessions
            SET encrypted_refresh_token = ?
            WHERE telegram_user_id = ?
            """,
            (
                b"corrupted-ciphertext",
                100,
            ),
        )

    with pytest.raises(
        SessionDecryptionError,
        match="could not be decrypted",
    ):
        load_linked_session(
            path,
            cipher,
            telegram_user_id=100,
        )


def test_wrong_encryption_key_cannot_decrypt_session(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"

    save_linked_session(
        path,
        create_cipher(),
        telegram_user_id=100,
        supabase_user_id="supabase-user-1",
        refresh_token="refresh-token",
        now=1_000,
    )

    with pytest.raises(SessionDecryptionError):
        load_linked_session(
            path,
            create_cipher(),
            telegram_user_id=100,
        )


def test_complete_linked_session_is_atomic(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"
    cipher = create_cipher()

    challenge = create_link_challenge(
        path,
        telegram_user_id=100,
        telegram_chat_id=100,
        now=1_000,
    )

    reserve_otp_request(
        path,
        challenge.token,
        "roman@example.com",
        now=1_001,
    )

    identity = complete_linked_session(
        path,
        cipher,
        challenge_token=challenge.token,
        email="roman@example.com",
        supabase_user_id="supabase-user-1",
        refresh_token="refresh-token",
        now=1_002,
    )

    assert identity.user_id == 100
    assert identity.chat_id == 100

    session = load_linked_session(
        path,
        cipher,
        telegram_user_id=100,
    )

    assert session is not None
    assert session.supabase_user_id == ("supabase-user-1")
    assert session.refresh_token == ("refresh-token")

    assert (
        consume_link_challenge(
            path,
            challenge.token,
            now=1_003,
        )
        is None
    )


def test_completion_requires_otp_request(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"
    cipher = create_cipher()

    challenge = create_link_challenge(
        path,
        telegram_user_id=100,
        telegram_chat_id=100,
        now=1_000,
    )

    with pytest.raises(
        LinkCompletionError,
        match="not ready",
    ):
        complete_linked_session(
            path,
            cipher,
            challenge_token=challenge.token,
            email="roman@example.com",
            supabase_user_id="supabase-user-1",
            refresh_token="refresh-token",
            now=1_001,
        )

    assert (
        load_linked_session(
            path,
            cipher,
            telegram_user_id=100,
        )
        is None
    )


def test_link_conflict_does_not_consume_challenge(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"
    cipher = create_cipher()

    save_linked_session(
        path,
        cipher,
        telegram_user_id=100,
        supabase_user_id="supabase-user-1",
        refresh_token="existing-token",
        now=1_000,
    )

    challenge = create_link_challenge(
        path,
        telegram_user_id=200,
        telegram_chat_id=200,
        now=1_001,
    )

    reserve_otp_request(
        path,
        challenge.token,
        "second@example.com",
        now=1_002,
    )

    with pytest.raises(SessionAlreadyLinked):
        complete_linked_session(
            path,
            cipher,
            challenge_token=challenge.token,
            email="second@example.com",
            supabase_user_id="supabase-user-1",
            refresh_token="new-token",
            now=1_003,
        )

    verification = get_otp_verification(
        path,
        challenge.token,
        "second@example.com",
        now=1_004,
    )

    assert verification.identity.user_id == 200
