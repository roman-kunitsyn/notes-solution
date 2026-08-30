from collections.abc import Awaitable, Callable
from pathlib import Path

from supabase import AsyncClient, acreate_client
from supabase_auth.errors import AuthApiError

from notes_bot.linking import TelegramIdentity
from notes_bot.otp_state import (
    OtpRequest,
    get_otp_verification,
    record_failed_otp_attempt,
    release_otp_request,
    reserve_otp_request,
)
from notes_bot.sessions import (
    TokenCipher,
    complete_linked_session,
)

ClientFactory = Callable[
    [str, str],
    Awaitable[AsyncClient],
]


class OtpDeliveryError(RuntimeError):
    """Raised when Supabase cannot deliver an OTP."""


class InvalidOtpCode(RuntimeError):
    """Raised when the supplied OTP is invalid or expired."""


class OtpVerificationError(RuntimeError):
    """Raised when OTP verification cannot be completed safely."""


class SupabaseOtpService:
    def __init__(
        self,
        *,
        supabase_url: str,
        publishable_key: str,
        database_path: Path,
        cipher: TokenCipher,
        client_factory: ClientFactory = acreate_client,
    ) -> None:
        self._supabase_url = supabase_url
        self._publishable_key = publishable_key
        self._database_path = database_path
        self._cipher = cipher
        self._client_factory = client_factory

    async def request_code(
        self,
        *,
        token: str,
        email: str,
    ) -> OtpRequest:
        request = reserve_otp_request(
            self._database_path,
            token,
            email,
        )

        try:
            client = await self._client_factory(
                self._supabase_url,
                self._publishable_key,
            )

            await client.auth.sign_in_with_otp(
                {
                    "email": request.email,
                    "options": {
                        "should_create_user": False,
                    },
                }
            )
        except Exception as error:
            release_otp_request(
                self._database_path,
                token,
                requested_at=request.requested_at,
            )

            raise OtpDeliveryError("Unable to send the authentication code") from error

        return request

    async def verify_code(
        self,
        *,
        token: str,
        email: str,
        code: str,
    ) -> TelegramIdentity:
        verification = get_otp_verification(
            self._database_path,
            token,
            email,
        )

        try:
            normalized_code = normalize_otp(code)
        except ValueError as error:
            record_failed_otp_attempt(
                self._database_path,
                token,
            )

            raise InvalidOtpCode(
                "The authentication code is invalid or expired"
            ) from error

        try:
            client = await self._client_factory(
                self._supabase_url,
                self._publishable_key,
            )

            response = await client.auth.verify_otp(
                {
                    "email": verification.email,
                    "token": normalized_code,
                    "type": "email",
                }
            )
        except AuthApiError as error:
            record_failed_otp_attempt(
                self._database_path,
                token,
            )

            raise InvalidOtpCode(
                "The authentication code is invalid or expired"
            ) from error
        except Exception as error:
            raise OtpVerificationError(
                "Authentication is temporarily unavailable"
            ) from error

        user = response.user
        session = response.session

        if user is None or session is None or not user.id or not session.refresh_token:
            raise OtpVerificationError(
                "Supabase returned an incomplete authentication session"
            )

        response_email = getattr(user, "email", None)

        if (
            response_email is not None
            and response_email.strip().lower() != verification.email
        ):
            raise OtpVerificationError(
                "Supabase returned an unexpected authenticated identity"
            )

        return complete_linked_session(
            self._database_path,
            self._cipher,
            challenge_token=token,
            email=verification.email,
            supabase_user_id=str(user.id),
            refresh_token=session.refresh_token,
        )


def normalize_otp(code: str) -> str:
    normalized = code.strip()

    if len(normalized) != 6 or not normalized.isascii() or not normalized.isdigit():
        raise ValueError("OTP must contain exactly six digits")

    return normalized
