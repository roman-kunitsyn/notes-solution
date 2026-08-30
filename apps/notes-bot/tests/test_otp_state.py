from pathlib import Path

import pytest

from notes_bot.linking import (
    create_link_challenge,
)
from notes_bot.otp_state import (
    MAX_OTP_ATTEMPTS,
    ChallengeEmailMismatch,
    InvalidLinkChallenge,
    OtpNotRequested,
    OtpRequestTooSoon,
    get_otp_verification,
    record_failed_otp_attempt,
    release_otp_request,
    reserve_otp_request,
)


def create_challenge(
    path: Path,
    *,
    now: int = 1_000,
) -> str:
    return create_link_challenge(
        path,
        telegram_user_id=100,
        telegram_chat_id=100,
        now=now,
    ).token


def test_reserve_otp_request_binds_email(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"
    token = create_challenge(path)

    request = reserve_otp_request(
        path,
        token,
        " Roman@Example.com ",
        now=1_001,
    )

    assert request.email == "roman@example.com"
    assert request.identity.user_id == 100
    assert request.requested_at == 1_001


def test_challenge_rejects_email_change(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"
    token = create_challenge(path)

    reserve_otp_request(
        path,
        token,
        "first@example.com",
        now=1_001,
    )

    with pytest.raises(
        ChallengeEmailMismatch,
        match="another email",
    ):
        reserve_otp_request(
            path,
            token,
            "second@example.com",
            now=1_100,
        )


def test_otp_request_has_cooldown(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"
    token = create_challenge(path)

    reserve_otp_request(
        path,
        token,
        "roman@example.com",
        now=1_001,
    )

    with pytest.raises(OtpRequestTooSoon) as error:
        reserve_otp_request(
            path,
            token,
            "roman@example.com",
            now=1_030,
        )

    assert error.value.retry_after == 31


def test_release_allows_immediate_retry(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"
    token = create_challenge(path)

    request = reserve_otp_request(
        path,
        token,
        "roman@example.com",
        now=1_001,
    )

    assert release_otp_request(
        path,
        token,
        requested_at=request.requested_at,
    )

    retry = reserve_otp_request(
        path,
        token,
        "roman@example.com",
        now=1_002,
    )

    assert retry.requested_at == 1_002


def test_verification_requires_bound_email(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"
    token = create_challenge(path)

    with pytest.raises(ChallengeEmailMismatch):
        get_otp_verification(
            path,
            token,
            "roman@example.com",
            now=1_001,
        )


def test_released_request_cannot_be_verified(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"
    token = create_challenge(path)

    request = reserve_otp_request(
        path,
        token,
        "roman@example.com",
        now=1_001,
    )
    release_otp_request(
        path,
        token,
        requested_at=request.requested_at,
    )

    with pytest.raises(
        OtpNotRequested,
        match="Request an OTP",
    ):
        get_otp_verification(
            path,
            token,
            "roman@example.com",
            now=1_002,
        )


def test_verification_returns_identity(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"
    token = create_challenge(path)

    reserve_otp_request(
        path,
        token,
        "roman@example.com",
        now=1_001,
    )

    verification = get_otp_verification(
        path,
        token,
        "roman@example.com",
        now=1_002,
    )

    assert verification.identity.user_id == 100
    assert verification.identity.chat_id == 100
    assert verification.attempts_remaining == (MAX_OTP_ATTEMPTS)


def test_failed_attempts_eventually_consume_link(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"
    token = create_challenge(path)

    reserve_otp_request(
        path,
        token,
        "roman@example.com",
        now=1_001,
    )

    for attempt in range(MAX_OTP_ATTEMPTS):
        remaining = record_failed_otp_attempt(
            path,
            token,
            now=1_002 + attempt,
        )

    assert remaining == 0

    with pytest.raises(InvalidLinkChallenge):
        get_otp_verification(
            path,
            token,
            "roman@example.com",
            now=1_100,
        )


@pytest.mark.parametrize(
    "email",
    [
        "",
        "not-an-email",
        "has space@example.com",
    ],
)
def test_invalid_email_is_rejected(
    tmp_path: Path,
    email: str,
) -> None:
    path = tmp_path / "bot.sqlite3"
    token = create_challenge(path)

    with pytest.raises(
        ValueError,
        match="Invalid email",
    ):
        reserve_otp_request(
            path,
            token,
            email,
            now=1_001,
        )
