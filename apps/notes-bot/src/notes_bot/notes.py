from dataclasses import dataclass
from typing import Any

from notes_bot.supabase_session import SupabaseSessionManager

NOTE_COLUMNS = "id,title,updated_at"
DEFAULT_LIST_LIMIT = 20


@dataclass(frozen=True)
class NoteSummary:
    id: str
    title: str
    updated_at: str

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> NoteSummary:
        return cls(
            id=str(row["id"]),
            title=str(row["title"]),
            updated_at=str(row["updated_at"]),
        )


async def list_notes(
    session_manager: SupabaseSessionManager,
    *,
    telegram_user_id: int,
    limit: int = DEFAULT_LIST_LIMIT,
) -> list[NoteSummary]:
    client = await session_manager.authenticated_client(
        telegram_user_id=telegram_user_id,
    )

    response = await (
        client.table("notes")
        .select(NOTE_COLUMNS)
        .order("updated_at", desc=True)
        .limit(limit)
        .execute()
    )

    return [NoteSummary.from_row(row) for row in response.data or []]
