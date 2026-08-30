from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from cryptography.fernet import Fernet

from notes_bot.linking import create_link_challenge
from notes_bot.otp_state import (
    OtpNotRequested,
    get_otp_verification,
    reserve_otp_request,
)
from notes_bot.sessions import (
    TokenCipher,
    load_linked_session,
)
from notes_bot.supabase_otp import (
    InvalidOtpCode,
    OtpDeliveryError,
    OtpVerificationError,
    SupabaseOtpService,
)


def create_cipher() -> TokenCipher:
    return TokenCipher(Fernet.generate_key().decode("ascii"))


def create_fake_client():
    client = SimpleNamespace(
        auth=SimpleNamespace(
            sign_in_with_otp=AsyncMock(),
        )
    )
    factory = AsyncMock(return_value=client)

    return client, factory


async def test_request_code_sends_otp(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"

    challenge = create_link_challenge(
        path,
        telegram_user_id=100,
        telegram_chat_id=200,
    )

    client, factory = create_fake_client()

    service = SupabaseOtpService(
        supabase_url="http://127.0.0.1:54321",
        publishable_key="sb_publishable_test",
        database_path=path,
        cipher=create_cipher(),
        client_factory=factory,
    )

    request = await service.request_code(
        token=challenge.token,
        email="  USER@Example.COM ",
    )

    assert request.email == "user@example.com"

    factory.assert_awaited_once_with(
        "http://127.0.0.1:54321",
        "sb_publishable_test",
    )

    client.auth.sign_in_with_otp.assert_awaited_once_with(
        {
            "email": "user@example.com",
            "options": {
                "should_create_user": False,
            },
        }
    )


async def test_request_code_reserves_verification_state(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"

    challenge = create_link_challenge(
        path,
        telegram_user_id=100,
        telegram_chat_id=200,
    )

    _, factory = create_fake_client()

    service = SupabaseOtpService(
        supabase_url="http://127.0.0.1:54321",
        publishable_key="sb_publishable_test",
        database_path=path,
        cipher=create_cipher(),
        client_factory=factory,
    )

    await service.request_code(
        token=challenge.token,
        email="user@example.com",
    )

    verification = get_otp_verification(path, challenge.token, "user@example.com")

    assert verification.email == "user@example.com"
    assert verification.identity.user_id == 100
    assert verification.identity.chat_id == 200


async def test_request_code_releases_failed_reservation(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"

    challenge = create_link_challenge(
        path,
        telegram_user_id=100,
        telegram_chat_id=200,
    )

    client, factory = create_fake_client()
    client.auth.sign_in_with_otp.side_effect = OSError("network unavailable")

    service = SupabaseOtpService(
        supabase_url="http://127.0.0.1:54321",
        publishable_key="sb_publishable_test",
        database_path=path,
        cipher=create_cipher(),
        client_factory=factory,
    )

    with pytest.raises(
        OtpDeliveryError,
        match="Unable to send",
    ):
        await service.request_code(
            token=challenge.token,
            email="user@example.com",
        )

    with pytest.raises(
        OtpNotRequested,
        match="Request an OTP",
    ):
        get_otp_verification(
            path,
            challenge.token,
            "user@example.com",
        )

    client.auth.sign_in_with_otp.reset_mock(
        side_effect=True,
    )

    await service.request_code(
        token=challenge.token,
        email="user@example.com",
    )

    client.auth.sign_in_with_otp.assert_awaited_once()


async def test_verify_code_stores_linked_session(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"
    cipher = create_cipher()

    challenge = create_link_challenge(
        path,
        telegram_user_id=100,
        telegram_chat_id=200,
    )

    reserve_otp_request(
        path,
        challenge.token,
        "user@example.com",
    )

    client = SimpleNamespace(
        auth=SimpleNamespace(
            verify_otp=AsyncMock(
                return_value=SimpleNamespace(
                    user=SimpleNamespace(
                        id="supabase-user-1",
                        email="user@example.com",
                    ),
                    session=SimpleNamespace(
                        refresh_token="refresh-token",
                    ),
                )
            )
        )
    )
    factory = AsyncMock(return_value=client)

    service = SupabaseOtpService(
        supabase_url="http://127.0.0.1:54321",
        publishable_key="sb_publishable_test",
        database_path=path,
        cipher=cipher,
        client_factory=factory,
    )

    identity = await service.verify_code(
        token=challenge.token,
        email="user@example.com",
        code="123456",
    )

    assert identity.user_id == 100
    assert identity.chat_id == 200

    client.auth.verify_otp.assert_awaited_once_with(
        {
            "email": "user@example.com",
            "token": "123456",
            "type": "email",
        }
    )

    stored = load_linked_session(
        path,
        cipher,
        telegram_user_id=100,
    )

    assert stored is not None
    assert stored.supabase_user_id == "supabase-user-1"
    assert stored.refresh_token == "refresh-token"


async def test_verify_code_rejects_malformed_code(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"

    challenge = create_link_challenge(
        path,
        telegram_user_id=100,
        telegram_chat_id=200,
    )

    reserve_otp_request(
        path,
        challenge.token,
        "user@example.com",
    )

    _, factory = create_fake_client()

    service = SupabaseOtpService(
        supabase_url="http://127.0.0.1:54321",
        publishable_key="sb_publishable_test",
        database_path=path,
        cipher=create_cipher(),
        client_factory=factory,
    )

    with pytest.raises(
        InvalidOtpCode,
        match="invalid or expired",
    ):
        await service.verify_code(
            token=challenge.token,
            email="user@example.com",
            code="12ab",
        )

    factory.assert_not_awaited()

    verification = get_otp_verification(
        path,
        challenge.token,
        "user@example.com",
    )

    assert verification.failed_attempts == 1


async def test_verify_code_does_not_count_network_failure(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"

    challenge = create_link_challenge(
        path,
        telegram_user_id=100,
        telegram_chat_id=200,
    )

    reserve_otp_request(
        path,
        challenge.token,
        "user@example.com",
    )

    client = SimpleNamespace(
        auth=SimpleNamespace(
            verify_otp=AsyncMock(side_effect=OSError("network unavailable"))
        )
    )
    factory = AsyncMock(return_value=client)

    service = SupabaseOtpService(
        supabase_url="http://127.0.0.1:54321",
        publishable_key="sb_publishable_test",
        database_path=path,
        cipher=create_cipher(),
        client_factory=factory,
    )

    with pytest.raises(
        OtpVerificationError,
        match="temporarily unavailable",
    ):
        await service.verify_code(
            token=challenge.token,
            email="user@example.com",
            code="123456",
        )

    verification = get_otp_verification(
        path,
        challenge.token,
        "user@example.com",
    )

    assert verification.failed_attempts == 0
