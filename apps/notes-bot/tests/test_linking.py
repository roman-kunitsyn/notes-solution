import re
from pathlib import Path

import pytest

from notes_bot.database import database_connection
from notes_bot.linking import (
    TelegramIdentity,
    consume_link_challenge,
    create_link_challenge,
    delete_expired_challenges,
    token_hash,
)


def test_create_link_challenge_returns_base64url_token(
    tmp_path: Path,
) -> None:
    challenge = create_link_challenge(
        tmp_path / "bot.sqlite3",
        telegram_user_id=100,
        telegram_chat_id=200,
        now=1_000,
    )

    assert re.fullmatch(
        r"[A-Za-z0-9_-]{43}",
        challenge.token,
    )
    assert challenge.expires_at == 1_600


def test_create_link_challenge_stores_only_hash(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"

    challenge = create_link_challenge(
        path,
        telegram_user_id=100,
        telegram_chat_id=200,
        now=1_000,
    )

    with database_connection(path) as connection:
        row = connection.execute(
            """
            SELECT token_hash
            FROM link_challenges
            """
        ).fetchone()

    assert row["token_hash"] == token_hash(challenge.token)
    assert row["token_hash"] != challenge.token


def test_consume_link_challenge_returns_identity(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"

    challenge = create_link_challenge(
        path,
        telegram_user_id=100,
        telegram_chat_id=200,
        now=1_000,
    )

    identity = consume_link_challenge(
        path,
        challenge.token,
        now=1_500,
    )

    assert identity == TelegramIdentity(
        user_id=100,
        chat_id=200,
    )


def test_link_challenge_can_be_consumed_once(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"

    challenge = create_link_challenge(
        path,
        telegram_user_id=100,
        telegram_chat_id=200,
        now=1_000,
    )

    first_result = consume_link_challenge(
        path,
        challenge.token,
        now=1_100,
    )
    second_result = consume_link_challenge(
        path,
        challenge.token,
        now=1_101,
    )

    assert first_result is not None
    assert second_result is None


def test_expired_link_challenge_is_rejected(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"

    challenge = create_link_challenge(
        path,
        telegram_user_id=100,
        telegram_chat_id=200,
        now=1_000,
        ttl=60,
    )

    result = consume_link_challenge(
        path,
        challenge.token,
        now=1_060,
    )

    assert result is None


def test_new_challenge_invalidates_previous_challenge(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"

    previous = create_link_challenge(
        path,
        telegram_user_id=100,
        telegram_chat_id=200,
        now=1_000,
    )
    current = create_link_challenge(
        path,
        telegram_user_id=100,
        telegram_chat_id=200,
        now=1_001,
    )

    assert (
        consume_link_challenge(
            path,
            previous.token,
            now=1_002,
        )
        is None
    )
    assert (
        consume_link_challenge(
            path,
            current.token,
            now=1_002,
        )
        is not None
    )


def test_different_users_have_independent_challenges(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"

    first = create_link_challenge(
        path,
        telegram_user_id=100,
        telegram_chat_id=100,
        now=1_000,
    )
    second = create_link_challenge(
        path,
        telegram_user_id=200,
        telegram_chat_id=200,
        now=1_000,
    )

    assert consume_link_challenge(
        path,
        first.token,
        now=1_001,
    ) == TelegramIdentity(
        user_id=100,
        chat_id=100,
    )
    assert consume_link_challenge(
        path,
        second.token,
        now=1_001,
    ) == TelegramIdentity(
        user_id=200,
        chat_id=200,
    )


def test_delete_expired_challenges(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"

    create_link_challenge(
        path,
        telegram_user_id=100,
        telegram_chat_id=100,
        now=1_000,
        ttl=10,
    )
    create_link_challenge(
        path,
        telegram_user_id=200,
        telegram_chat_id=200,
        now=1_000,
        ttl=100,
    )

    deleted = delete_expired_challenges(
        path,
        now=1_010,
    )

    assert deleted == 1

    with database_connection(path) as connection:
        remaining = connection.execute(
            """
            SELECT COUNT(*)
            FROM link_challenges
            """
        ).fetchone()[0]

    assert remaining == 1


@pytest.mark.parametrize(
    ("telegram_user_id", "telegram_chat_id", "ttl"),
    [
        (0, 100, 600),
        (-1, 100, 600),
        (100, 0, 600),
        (100, -1, 600),
        (100, 100, 0),
        (100, 100, -1),
    ],
)
def test_create_link_challenge_rejects_invalid_values(
    tmp_path: Path,
    telegram_user_id: int,
    telegram_chat_id: int,
    ttl: int,
) -> None:
    with pytest.raises(ValueError):
        create_link_challenge(
            tmp_path / "bot.sqlite3",
            telegram_user_id=telegram_user_id,
            telegram_chat_id=telegram_chat_id,
            now=1_000,
            ttl=ttl,
        )
