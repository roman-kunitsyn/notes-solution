from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from cryptography.fernet import Fernet

from notes_bot.sessions import (
    TokenCipher,
    load_linked_session,
    save_linked_session,
)
from notes_bot.supabase_session import (
    SessionIdentityMismatch,
    SessionNotLinked,
    SupabaseSessionManager,
)


def create_cipher() -> TokenCipher:
    return TokenCipher(Fernet.generate_key().decode("ascii"))


def auth_response(
    *,
    user_id: str,
    refresh_token: str,
):
    return SimpleNamespace(
        user=SimpleNamespace(
            id=user_id,
        ),
        session=SimpleNamespace(
            refresh_token=refresh_token,
            access_token="access-token",
        ),
    )


def create_fake_client(
    response,
):
    client = SimpleNamespace(
        auth=SimpleNamespace(refresh_session=AsyncMock(return_value=response))
    )

    factory = AsyncMock(return_value=client)

    return client, factory


async def test_authenticated_client_refreshes_session(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"
    cipher = create_cipher()

    save_linked_session(
        path,
        cipher,
        telegram_user_id=100,
        supabase_user_id="user-1",
        refresh_token="old-refresh-token",
        now=1_000,
    )

    client, factory = create_fake_client(
        auth_response(
            user_id="user-1",
            refresh_token="new-refresh-token",
        )
    )

    manager = SupabaseSessionManager(
        supabase_url="http://127.0.0.1:54321",
        publishable_key="sb_publishable_test",
        database_path=path,
        cipher=cipher,
        client_factory=factory,
    )

    result = await manager.authenticated_client(telegram_user_id=100)

    assert result is client

    factory.assert_awaited_once_with(
        "http://127.0.0.1:54321",
        "sb_publishable_test",
    )
    client.auth.refresh_session.assert_awaited_once_with("old-refresh-token")


async def test_authenticated_client_persists_rotated_token(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"
    cipher = create_cipher()

    save_linked_session(
        path,
        cipher,
        telegram_user_id=100,
        supabase_user_id="user-1",
        refresh_token="old-refresh-token",
        now=1_000,
    )

    _, factory = create_fake_client(
        auth_response(
            user_id="user-1",
            refresh_token="new-refresh-token",
        )
    )

    manager = SupabaseSessionManager(
        supabase_url="http://127.0.0.1:54321",
        publishable_key="sb_publishable_test",
        database_path=path,
        cipher=cipher,
        client_factory=factory,
    )

    await manager.authenticated_client(telegram_user_id=100)

    stored = load_linked_session(
        path,
        cipher,
        telegram_user_id=100,
    )

    assert stored is not None
    assert stored.refresh_token == ("new-refresh-token")


async def test_authenticated_client_rejects_unlinked_user(
    tmp_path: Path,
) -> None:
    manager = SupabaseSessionManager(
        supabase_url="http://127.0.0.1:54321",
        publishable_key="sb_publishable_test",
        database_path=(tmp_path / "bot.sqlite3"),
        cipher=create_cipher(),
        client_factory=AsyncMock(),
    )

    with pytest.raises(
        SessionNotLinked,
        match="not linked",
    ):
        await manager.authenticated_client(telegram_user_id=100)


async def test_authenticated_client_rejects_identity_mismatch(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"
    cipher = create_cipher()

    save_linked_session(
        path,
        cipher,
        telegram_user_id=100,
        supabase_user_id="expected-user",
        refresh_token="refresh-token",
        now=1_000,
    )

    _, factory = create_fake_client(
        auth_response(
            user_id="different-user",
            refresh_token="new-token",
        )
    )

    manager = SupabaseSessionManager(
        supabase_url="http://127.0.0.1:54321",
        publishable_key="sb_publishable_test",
        database_path=path,
        cipher=cipher,
        client_factory=factory,
    )

    with pytest.raises(
        SessionIdentityMismatch,
        match="does not match",
    ):
        await manager.authenticated_client(telegram_user_id=100)

    assert (
        load_linked_session(
            path,
            cipher,
            telegram_user_id=100,
        )
        is None
    )


async def test_authenticated_client_reuses_user_client(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"
    cipher = create_cipher()

    save_linked_session(
        path,
        cipher,
        telegram_user_id=100,
        supabase_user_id="user-1",
        refresh_token="first-token",
        now=1_000,
    )

    client, factory = create_fake_client(
        auth_response(
            user_id="user-1",
            refresh_token="rotated-token",
        )
    )

    manager = SupabaseSessionManager(
        supabase_url="http://127.0.0.1:54321",
        publishable_key="sb_publishable_test",
        database_path=path,
        cipher=cipher,
        client_factory=factory,
    )

    first = await manager.authenticated_client(telegram_user_id=100)
    second = await manager.authenticated_client(telegram_user_id=100)

    assert first is client
    assert second is client
    assert factory.await_count == 1
    assert client.auth.refresh_session.await_count == 2


async def test_unlink_removes_session(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"
    cipher = create_cipher()

    save_linked_session(
        path,
        cipher,
        telegram_user_id=100,
        supabase_user_id="user-1",
        refresh_token="refresh-token",
        now=1_000,
    )

    manager = SupabaseSessionManager(
        supabase_url="http://127.0.0.1:54321",
        publishable_key="sb_publishable_test",
        database_path=path,
        cipher=cipher,
        client_factory=AsyncMock(),
    )

    assert await manager.unlink(telegram_user_id=100)
    assert (
        load_linked_session(
            path,
            cipher,
            telegram_user_id=100,
        )
        is None
    )
