from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace

from aiohttp import ClientSession
from aiohttp.test_utils import (
    TestClient,
    TestServer,
)

from notes_bot.http_server import (
    HttpServer,
    create_http_app,
)
from notes_bot.linking import (
    TelegramIdentity,
    create_link_challenge,
)
from notes_bot.otp_state import (
    ChallengeEmailMismatch,
    InvalidLinkChallenge,
    OtpAttemptsExceeded,
    OtpNotRequested,
    OtpRequestTooSoon,
)
from notes_bot.sessions import (
    LinkCompletionError,
    SessionAlreadyLinked,
)
from notes_bot.supabase_otp import (
    InvalidOtpCode,
    OtpDeliveryError,
    OtpVerificationError,
)

VALID_TOKEN = "A" * 43
REQUEST_OTP_ERROR = {
    "ok": False,
    "error": "Unable to request an authentication code.",
}
VERIFY_OTP_ERROR = {
    "ok": False,
    "error": "Unable to verify the authentication code.",
}


class FakeOtpService:
    def __init__(
        self,
        side_effect: Exception | None = None,
        *,
        verify_side_effect: Exception | None = None,
        verify_result: object | None = None,
    ) -> None:
        self.side_effect = side_effect
        self.verify_side_effect = verify_side_effect
        self.verify_result = (
            TelegramIdentity(
                user_id=100,
                chat_id=200,
            )
            if verify_result is None
            else verify_result
        )
        self.requests: list[dict[str, str]] = []
        self.verifications: list[dict[str, str]] = []

    async def request_code(
        self,
        *,
        token: str,
        email: str,
    ) -> object:
        self.requests.append(
            {
                "token": token,
                "email": email,
            }
        )

        if self.side_effect is not None:
            raise self.side_effect

        return object()

    async def verify_code(
        self,
        *,
        token: str,
        email: str,
        code: str,
    ) -> object:
        self.verifications.append(
            {
                "token": token,
                "email": email,
                "code": code,
            }
        )

        if self.verify_side_effect is not None:
            raise self.verify_side_effect

        return self.verify_result


@asynccontextmanager
async def http_test_client(
    database_path: Path,
    *,
    otp_service: FakeOtpService | None = None,
) -> AsyncIterator[TestClient]:
    server = TestServer(
        create_http_app(
            database_path=database_path,
            otp_service=otp_service,
        )
    )
    client = TestClient(server)

    await client.start_server()

    try:
        yield client
    finally:
        await client.close()


async def test_health_endpoint(
    tmp_path: Path,
) -> None:
    async with http_test_client(tmp_path / "bot.sqlite3") as client:
        response = await client.get("/health")

        assert response.status == 200
        assert await response.json() == {"status": "ok"}
        assert response.headers["Cache-Control"] == "no-store"


async def test_link_page_has_security_headers(
    tmp_path: Path,
) -> None:
    async with http_test_client(tmp_path / "bot.sqlite3") as client:
        response = await client.get("/link")
        text = await response.text()

        assert response.status == 200
        assert "Link Notes account" in text
        assert response.headers["Referrer-Policy"] == "no-referrer"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert "default-src 'none'" in (response.headers["Content-Security-Policy"])


async def test_link_page_contains_accessible_email_and_otp_forms(
    tmp_path: Path,
) -> None:
    async with http_test_client(tmp_path / "bot.sqlite3") as client:
        response = await client.get("/link")
        text = await response.text()

    assert response.status == 200
    assert 'id="email-form"' in text
    assert 'for="email-input"' in text
    assert 'id="email-input"' in text
    assert 'type="email"' in text
    assert 'autocomplete="email"' in text
    assert 'id="otp-form"' in text
    assert 'for="otp-input"' in text
    assert 'id="otp-input"' in text
    assert 'inputmode="numeric"' in text
    assert 'autocomplete="one-time-code"' in text
    assert 'maxlength="6"' in text
    assert 'pattern="[0-9]{6}"' in text
    assert 'aria-live="polite"' in text
    assert 'role="status"' in text


async def test_link_page_uses_external_script_without_inline_handlers(
    tmp_path: Path,
) -> None:
    async with http_test_client(tmp_path / "bot.sqlite3") as client:
        response = await client.get("/link")
        text = await response.text()

    lowered = text.lower()

    assert response.status == 200
    assert '<script src="/assets/link.js"></script>' in text
    assert lowered.count("<script") == 1
    assert "onclick=" not in lowered
    assert "onsubmit=" not in lowered
    assert "onchange=" not in lowered
    assert "oninput=" not in lowered


async def test_link_script_references_otp_endpoints_after_fragment_removal(
    tmp_path: Path,
) -> None:
    async with http_test_client(tmp_path / "bot.sqlite3") as client:
        response = await client.get("/assets/link.js")
        text = await response.text()

    replace_index = text.index("history.replaceState")

    assert response.status == 200
    assert "/link/validate" in text
    assert "/link/request-otp" in text
    assert "/link/verify-otp" in text
    assert replace_index < text.index("/link/validate")
    assert replace_index < text.index("/link/request-otp")
    assert replace_index < text.index("/link/verify-otp")


async def test_link_script_avoids_browser_storage_html_injection_and_logging(
    tmp_path: Path,
) -> None:
    async with http_test_client(tmp_path / "bot.sqlite3") as client:
        response = await client.get("/assets/link.js")
        text = await response.text()

    assert response.status == 200
    assert "localStorage" not in text
    assert "sessionStorage" not in text
    assert "indexedDB" not in text
    assert "document.cookie" not in text
    assert "console." not in text
    assert "innerHTML" not in text
    assert ".textContent" in text


async def test_validate_link_accepts_valid_challenge(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"

    challenge = create_link_challenge(
        path,
        telegram_user_id=100,
        telegram_chat_id=100,
    )

    async with http_test_client(path) as client:
        response = await client.post(
            "/link/validate",
            json={"token": challenge.token},
        )

        assert response.status == 200
        assert await response.json() == {"valid": True}


async def test_validate_link_rejects_unknown_token(
    tmp_path: Path,
) -> None:
    async with http_test_client(tmp_path / "bot.sqlite3") as client:
        response = await client.post(
            "/link/validate",
            json={"token": "x" * 43},
        )

        assert response.status == 404


async def test_validate_link_rejects_bad_format(
    tmp_path: Path,
) -> None:
    async with http_test_client(tmp_path / "bot.sqlite3") as client:
        response = await client.post(
            "/link/validate",
            json={"token": "invalid"},
        )

        assert response.status == 400


async def test_validation_does_not_consume_link(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot.sqlite3"

    challenge = create_link_challenge(
        path,
        telegram_user_id=100,
        telegram_chat_id=100,
    )

    async with http_test_client(path) as client:
        first = await client.post(
            "/link/validate",
            json={"token": challenge.token},
        )
        second = await client.post(
            "/link/validate",
            json={"token": challenge.token},
        )

        assert first.status == 200
        assert second.status == 200


async def test_request_otp_accepts_valid_request(
    tmp_path: Path,
) -> None:
    service = FakeOtpService()

    async with http_test_client(
        tmp_path / "bot.sqlite3",
        otp_service=service,
    ) as client:
        response = await client.post(
            "/link/request-otp",
            json={
                "token": VALID_TOKEN,
                "email": "user@example.com",
            },
        )
        body = await response.json()

    assert response.status == 202
    assert body == {
        "ok": True,
        "message": "If the account can be authenticated, a code has been sent.",
    }
    assert service.requests == [
        {
            "token": VALID_TOKEN,
            "email": "user@example.com",
        }
    ]


async def test_request_otp_rejects_malformed_json(
    tmp_path: Path,
) -> None:
    service = FakeOtpService()

    async with http_test_client(
        tmp_path / "bot.sqlite3",
        otp_service=service,
    ) as client:
        response = await client.post(
            "/link/request-otp",
            data="{",
            headers={"Content-Type": "application/json"},
        )
        body = await response.json()

    assert response.status == 400
    assert body == REQUEST_OTP_ERROR
    assert service.requests == []


async def test_request_otp_rejects_missing_json_content_type(
    tmp_path: Path,
) -> None:
    service = FakeOtpService()

    async with http_test_client(
        tmp_path / "bot.sqlite3",
        otp_service=service,
    ) as client:
        response = await client.post(
            "/link/request-otp",
            data="not json",
        )
        body = await response.json()

    assert response.status == 400
    assert body == REQUEST_OTP_ERROR
    assert service.requests == []


async def test_request_otp_rejects_incorrect_field_types(
    tmp_path: Path,
) -> None:
    service = FakeOtpService()

    async with http_test_client(
        tmp_path / "bot.sqlite3",
        otp_service=service,
    ) as client:
        response = await client.post(
            "/link/request-otp",
            json={
                "token": VALID_TOKEN,
                "email": 100,
            },
        )
        body = await response.json()

    assert response.status == 400
    assert body == REQUEST_OTP_ERROR
    assert service.requests == []


async def test_request_otp_rejects_missing_fields(
    tmp_path: Path,
) -> None:
    service = FakeOtpService()

    async with http_test_client(
        tmp_path / "bot.sqlite3",
        otp_service=service,
    ) as client:
        response = await client.post(
            "/link/request-otp",
            json={"token": VALID_TOKEN},
        )
        body = await response.json()

    assert response.status == 400
    assert body == REQUEST_OTP_ERROR
    assert service.requests == []


async def test_request_otp_rejects_empty_fields(
    tmp_path: Path,
) -> None:
    service = FakeOtpService()

    async with http_test_client(
        tmp_path / "bot.sqlite3",
        otp_service=service,
    ) as client:
        response = await client.post(
            "/link/request-otp",
            json={
                "token": "",
                "email": "user@example.com",
            },
        )
        body = await response.json()

    assert response.status == 400
    assert body == REQUEST_OTP_ERROR
    assert service.requests == []


async def test_request_otp_rejects_malformed_token(
    tmp_path: Path,
) -> None:
    service = FakeOtpService()

    async with http_test_client(
        tmp_path / "bot.sqlite3",
        otp_service=service,
    ) as client:
        response = await client.post(
            "/link/request-otp",
            json={
                "token": "invalid",
                "email": "user@example.com",
            },
        )
        body = await response.json()

    assert response.status == 400
    assert body == REQUEST_OTP_ERROR
    assert service.requests == []


async def test_request_otp_maps_invalid_challenge_to_safe_error(
    tmp_path: Path,
) -> None:
    service = FakeOtpService(
        InvalidLinkChallenge("raw token expired for user@example.com")
    )

    async with http_test_client(
        tmp_path / "bot.sqlite3",
        otp_service=service,
    ) as client:
        response = await client.post(
            "/link/request-otp",
            json={
                "token": VALID_TOKEN,
                "email": "user@example.com",
            },
        )
        text = await response.text()
        body = await response.json()

    assert response.status == 400
    assert body == REQUEST_OTP_ERROR
    assert "user@example.com" not in text
    assert VALID_TOKEN not in text
    assert "raw token expired" not in text


async def test_request_otp_maps_email_mismatch_to_safe_error(
    tmp_path: Path,
) -> None:
    service = FakeOtpService(ChallengeEmailMismatch("bound to other@example.com"))

    async with http_test_client(
        tmp_path / "bot.sqlite3",
        otp_service=service,
    ) as client:
        response = await client.post(
            "/link/request-otp",
            json={
                "token": VALID_TOKEN,
                "email": "user@example.com",
            },
        )
        body = await response.json()

    assert response.status == 400
    assert body == REQUEST_OTP_ERROR


async def test_request_otp_maps_cooldown_to_retry_after(
    tmp_path: Path,
) -> None:
    service = FakeOtpService(OtpRequestTooSoon(retry_after=42))

    async with http_test_client(
        tmp_path / "bot.sqlite3",
        otp_service=service,
    ) as client:
        response = await client.post(
            "/link/request-otp",
            json={
                "token": VALID_TOKEN,
                "email": "user@example.com",
            },
        )
        body = await response.json()

    assert response.status == 429
    assert response.headers["Retry-After"] == "42"
    assert body == REQUEST_OTP_ERROR


async def test_request_otp_maps_delivery_failure_to_unavailable(
    tmp_path: Path,
) -> None:
    service = FakeOtpService(OtpDeliveryError("network failed for user@example.com"))

    async with http_test_client(
        tmp_path / "bot.sqlite3",
        otp_service=service,
    ) as client:
        response = await client.post(
            "/link/request-otp",
            json={
                "token": VALID_TOKEN,
                "email": "user@example.com",
            },
        )
        text = await response.text()
        body = await response.json()

    assert response.status == 503
    assert body == {
        "ok": False,
        "error": "Authentication is temporarily unavailable.",
    }
    assert "user@example.com" not in text
    assert VALID_TOKEN not in text
    assert "network failed" not in text


async def test_verify_otp_accepts_valid_request(
    tmp_path: Path,
) -> None:
    service = FakeOtpService()

    async with http_test_client(
        tmp_path / "bot.sqlite3",
        otp_service=service,
    ) as client:
        response = await client.post(
            "/link/verify-otp",
            json={
                "token": VALID_TOKEN,
                "email": "user@example.com",
                "code": "123456",
            },
        )
        body = await response.json()

    assert response.status == 200
    assert body == {
        "ok": True,
        "message": "Your account has been linked successfully.",
    }
    assert service.verifications == [
        {
            "token": VALID_TOKEN,
            "email": "user@example.com",
            "code": "123456",
        }
    ]
    assert service.requests == []


async def test_verify_otp_response_hides_returned_identity(
    tmp_path: Path,
) -> None:
    service = FakeOtpService(
        verify_result=SimpleNamespace(
            user_id=987654,
            chat_id=123456,
            supabase_user_id="supabase-user-1",
            refresh_token="refresh-token",
        )
    )

    async with http_test_client(
        tmp_path / "bot.sqlite3",
        otp_service=service,
    ) as client:
        response = await client.post(
            "/link/verify-otp",
            json={
                "token": VALID_TOKEN,
                "email": "user@example.com",
                "code": "123456",
            },
        )
        text = await response.text()

    assert response.status == 200
    assert "987654" not in text
    assert "123456" not in text
    assert "supabase-user-1" not in text
    assert "refresh-token" not in text


async def test_verify_otp_rejects_missing_fields(
    tmp_path: Path,
) -> None:
    service = FakeOtpService()

    async with http_test_client(
        tmp_path / "bot.sqlite3",
        otp_service=service,
    ) as client:
        response = await client.post(
            "/link/verify-otp",
            json={
                "token": VALID_TOKEN,
                "email": "user@example.com",
            },
        )
        body = await response.json()

    assert response.status == 400
    assert body == VERIFY_OTP_ERROR
    assert service.verifications == []


async def test_verify_otp_rejects_incorrect_field_types(
    tmp_path: Path,
) -> None:
    service = FakeOtpService()

    async with http_test_client(
        tmp_path / "bot.sqlite3",
        otp_service=service,
    ) as client:
        response = await client.post(
            "/link/verify-otp",
            json={
                "token": VALID_TOKEN,
                "email": "user@example.com",
                "code": 123456,
            },
        )
        body = await response.json()

    assert response.status == 400
    assert body == VERIFY_OTP_ERROR
    assert service.verifications == []


async def test_verify_otp_rejects_empty_fields(
    tmp_path: Path,
) -> None:
    service = FakeOtpService()

    async with http_test_client(
        tmp_path / "bot.sqlite3",
        otp_service=service,
    ) as client:
        response = await client.post(
            "/link/verify-otp",
            json={
                "token": VALID_TOKEN,
                "email": "user@example.com",
                "code": "",
            },
        )
        body = await response.json()

    assert response.status == 400
    assert body == VERIFY_OTP_ERROR
    assert service.verifications == []


async def test_verify_otp_rejects_malformed_json(
    tmp_path: Path,
) -> None:
    service = FakeOtpService()

    async with http_test_client(
        tmp_path / "bot.sqlite3",
        otp_service=service,
    ) as client:
        response = await client.post(
            "/link/verify-otp",
            data="{",
            headers={"Content-Type": "application/json"},
        )
        body = await response.json()

    assert response.status == 400
    assert body == VERIFY_OTP_ERROR
    assert service.verifications == []


async def test_verify_otp_maps_invalid_challenge_to_safe_error(
    tmp_path: Path,
) -> None:
    service = FakeOtpService(
        verify_side_effect=InvalidLinkChallenge("expired token for user@example.com")
    )

    async with http_test_client(
        tmp_path / "bot.sqlite3",
        otp_service=service,
    ) as client:
        response = await client.post(
            "/link/verify-otp",
            json={
                "token": VALID_TOKEN,
                "email": "user@example.com",
                "code": "123456",
            },
        )
        text = await response.text()
        body = await response.json()

    assert response.status == 400
    assert body == VERIFY_OTP_ERROR
    assert "user@example.com" not in text
    assert VALID_TOKEN not in text
    assert "123456" not in text
    assert "expired token" not in text


async def test_verify_otp_maps_email_mismatch_to_safe_error(
    tmp_path: Path,
) -> None:
    service = FakeOtpService(
        verify_side_effect=ChallengeEmailMismatch("bound to other@example.com")
    )

    async with http_test_client(
        tmp_path / "bot.sqlite3",
        otp_service=service,
    ) as client:
        response = await client.post(
            "/link/verify-otp",
            json={
                "token": VALID_TOKEN,
                "email": "user@example.com",
                "code": "123456",
            },
        )
        body = await response.json()

    assert response.status == 400
    assert body == VERIFY_OTP_ERROR


async def test_verify_otp_maps_not_requested_to_safe_error(
    tmp_path: Path,
) -> None:
    service = FakeOtpService(
        verify_side_effect=OtpNotRequested("Request an OTP before verification")
    )

    async with http_test_client(
        tmp_path / "bot.sqlite3",
        otp_service=service,
    ) as client:
        response = await client.post(
            "/link/verify-otp",
            json={
                "token": VALID_TOKEN,
                "email": "user@example.com",
                "code": "123456",
            },
        )
        body = await response.json()

    assert response.status == 400
    assert body == VERIFY_OTP_ERROR


async def test_verify_otp_maps_invalid_code_to_safe_error(
    tmp_path: Path,
) -> None:
    service = FakeOtpService(
        verify_side_effect=InvalidOtpCode(
            "The authentication code 123456 is invalid for user@example.com"
        )
    )

    async with http_test_client(
        tmp_path / "bot.sqlite3",
        otp_service=service,
    ) as client:
        response = await client.post(
            "/link/verify-otp",
            json={
                "token": VALID_TOKEN,
                "email": "user@example.com",
                "code": "123456",
            },
        )
        text = await response.text()
        body = await response.json()

    assert response.status == 400
    assert body == {
        "ok": False,
        "error": "The authentication code is invalid or expired.",
    }
    assert "user@example.com" not in text
    assert VALID_TOKEN not in text
    assert "123456" not in text


async def test_verify_otp_maps_attempt_exhaustion_to_too_many_requests(
    tmp_path: Path,
) -> None:
    service = FakeOtpService(
        verify_side_effect=OtpAttemptsExceeded("too many attempts")
    )

    async with http_test_client(
        tmp_path / "bot.sqlite3",
        otp_service=service,
    ) as client:
        response = await client.post(
            "/link/verify-otp",
            json={
                "token": VALID_TOKEN,
                "email": "user@example.com",
                "code": "123456",
            },
        )
        body = await response.json()

    assert response.status == 429
    assert body == {
        "ok": False,
        "error": "Too many unsuccessful verification attempts.",
    }


async def test_verify_otp_maps_link_conflict_to_conflict(
    tmp_path: Path,
) -> None:
    service = FakeOtpService(
        verify_side_effect=SessionAlreadyLinked(
            "refresh-token already linked to supabase-user-1"
        )
    )

    async with http_test_client(
        tmp_path / "bot.sqlite3",
        otp_service=service,
    ) as client:
        response = await client.post(
            "/link/verify-otp",
            json={
                "token": VALID_TOKEN,
                "email": "user@example.com",
                "code": "123456",
            },
        )
        text = await response.text()
        body = await response.json()

    assert response.status == 409
    assert body == {
        "ok": False,
        "error": "This account cannot be linked.",
    }
    assert "refresh-token" not in text
    assert "supabase-user-1" not in text


async def test_verify_otp_maps_temporary_failure_to_unavailable(
    tmp_path: Path,
) -> None:
    service = FakeOtpService(
        verify_side_effect=OtpVerificationError(
            "network failed for refresh-token and user@example.com"
        )
    )

    async with http_test_client(
        tmp_path / "bot.sqlite3",
        otp_service=service,
    ) as client:
        response = await client.post(
            "/link/verify-otp",
            json={
                "token": VALID_TOKEN,
                "email": "user@example.com",
                "code": "123456",
            },
        )
        text = await response.text()
        body = await response.json()

    assert response.status == 503
    assert body == {
        "ok": False,
        "error": "Authentication is temporarily unavailable.",
    }
    assert "user@example.com" not in text
    assert VALID_TOKEN not in text
    assert "123456" not in text
    assert "refresh-token" not in text
    assert "network failed" not in text


async def test_verify_otp_maps_completion_failure_to_safe_error(
    tmp_path: Path,
) -> None:
    service = FakeOtpService(
        verify_side_effect=LinkCompletionError("link consumed concurrently")
    )

    async with http_test_client(
        tmp_path / "bot.sqlite3",
        otp_service=service,
    ) as client:
        response = await client.post(
            "/link/verify-otp",
            json={
                "token": VALID_TOKEN,
                "email": "user@example.com",
                "code": "123456",
            },
        )
        body = await response.json()

    assert response.status == 400
    assert body == VERIFY_OTP_ERROR


async def test_http_server_start_and_stop(
    tmp_path: Path,
    unused_tcp_port: int,
) -> None:
    server = HttpServer(
        application=create_http_app(database_path=(tmp_path / "bot.sqlite3")),
        host="127.0.0.1",
        port=unused_tcp_port,
    )

    assert server.started is False

    await server.start()

    try:
        assert server.started is True

        async with ClientSession() as client:
            response = await client.get(f"http://127.0.0.1:{unused_tcp_port}/health")

            assert response.status == 200
            assert await response.json() == {"status": "ok"}
    finally:
        await server.stop()

    assert server.started is False


async def test_http_server_stop_before_start(
    tmp_path: Path,
) -> None:
    server = HttpServer(
        application=create_http_app(database_path=(tmp_path / "bot.sqlite3")),
        host="127.0.0.1",
        port=8080,
    )

    await server.stop()

    assert server.started is False
