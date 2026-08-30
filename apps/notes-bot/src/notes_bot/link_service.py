import asyncio
from pathlib import Path
from urllib.parse import urlencode

from notes_bot.linking import (
    create_link_challenge,
)


class LinkingService:
    def __init__(
        self,
        *,
        database_path: Path,
        base_url: str,
    ) -> None:
        self._database_path = database_path
        self._base_url = base_url.rstrip("/")

    async def issue_url(
        self,
        *,
        telegram_user_id: int,
        telegram_chat_id: int,
    ) -> str:
        challenge = await asyncio.to_thread(
            create_link_challenge,
            self._database_path,
            telegram_user_id=telegram_user_id,
            telegram_chat_id=telegram_chat_id,
        )

        fragment = urlencode(
            {
                "token": challenge.token,
            }
        )

        return f"{self._base_url}/link#{fragment}"
