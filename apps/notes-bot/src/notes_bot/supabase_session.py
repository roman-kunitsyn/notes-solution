import asyncio
from collections.abc import (
    Awaitable,
    Callable,
)
from pathlib import Path

from supabase import (
    AsyncClient,
    acreate_client,
)
from supabase_auth.errors import AuthApiError

from notes_bot.sessions import (
    TokenCipher,
    delete_linked_session,
    load_linked_session,
    replace_refresh_token,
)


class SessionNotLinked(RuntimeError):
    """Raised when a Telegram user has no linked account."""


class SessionExpired(RuntimeError):
    """Raised when Supabase rejects the stored session."""


class SessionIdentityMismatch(RuntimeError):
    """Raised when the refreshed user differs from the linked user."""


ClientFactory = Callable[
    [str, str],
    Awaitable[AsyncClient],
]


class SupabaseSessionManager:
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

        self._locks: dict[int, asyncio.Lock] = {}
        self._clients: dict[int, AsyncClient] = {}

    def _lock_for(
        self,
        telegram_user_id: int,
    ) -> asyncio.Lock:
        lock = self._locks.get(telegram_user_id)

        if lock is None:
            lock = asyncio.Lock()
            self._locks[telegram_user_id] = lock

        return lock

    async def _load_session(
        self,
        telegram_user_id: int,
    ):
        return await asyncio.to_thread(
            load_linked_session,
            self._database_path,
            self._cipher,
            telegram_user_id=telegram_user_id,
        )

    async def _delete_session(
        self,
        telegram_user_id: int,
    ) -> None:
        await asyncio.to_thread(
            delete_linked_session,
            self._database_path,
            telegram_user_id=telegram_user_id,
        )

        self._clients.pop(
            telegram_user_id,
            None,
        )

    async def _client_for(
        self,
        telegram_user_id: int,
    ) -> AsyncClient:
        client = self._clients.get(telegram_user_id)

        if client is None:
            client = await self._client_factory(
                self._supabase_url,
                self._publishable_key,
            )
            self._clients[telegram_user_id] = client

        return client

    async def authenticated_client(
        self,
        *,
        telegram_user_id: int,
    ) -> AsyncClient:
        lock = self._lock_for(telegram_user_id)

        async with lock:
            stored = await self._load_session(telegram_user_id)

            if stored is None:
                raise SessionNotLinked("Telegram account is not linked")

            client = await self._client_for(telegram_user_id)

            try:
                response = await client.auth.refresh_session(stored.refresh_token)
            except AuthApiError as error:
                await self._delete_session(telegram_user_id)

                raise SessionExpired(
                    "Supabase session expired; link the account again"
                ) from error

            if response.session is None or response.user is None:
                await self._delete_session(telegram_user_id)

                raise SessionExpired("Supabase did not return an authenticated session")

            returned_user_id = str(response.user.id)

            if returned_user_id != stored.supabase_user_id:
                await self._delete_session(telegram_user_id)

                raise SessionIdentityMismatch(
                    "Supabase session identity does not match the linked account"
                )

            replaced = await asyncio.to_thread(
                replace_refresh_token,
                self._database_path,
                self._cipher,
                telegram_user_id=telegram_user_id,
                refresh_token=(response.session.refresh_token),
            )

            if not replaced:
                self._clients.pop(
                    telegram_user_id,
                    None,
                )

                raise SessionNotLinked("Linked session disappeared during refresh")

            return client

    async def unlink(
        self,
        *,
        telegram_user_id: int,
    ) -> bool:
        lock = self._lock_for(telegram_user_id)

        async with lock:
            deleted = await asyncio.to_thread(
                delete_linked_session,
                self._database_path,
                telegram_user_id=telegram_user_id,
            )

            self._clients.pop(
                telegram_user_id,
                None,
            )

            return deleted
