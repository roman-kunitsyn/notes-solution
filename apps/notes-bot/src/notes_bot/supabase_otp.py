from collections.abc import Awaitable, Callable
from pathlib import Path

from supabase import AsyncClient, acreate_client

from notes_bot.otp_state import (
    OtpRequest,
    release_otp_request,
    reserve_otp_request,
)

ClientFactory = Callable[
    [str, str],
    Awaitable[AsyncClient],
]


class OtpDeliveryError(RuntimeError):
    """Raised when Supabase cannot deliver an OTP."""


class SupabaseOtpService:
    def __init__(
        self,
        *,
        supabase_url: str,
        publishable_key: str,
        database_path: Path,
        client_factory: ClientFactory = acreate_client,
    ) -> None:
        self._supabase_url = supabase_url
        self._publishable_key = publishable_key
        self._database_path = database_path
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
