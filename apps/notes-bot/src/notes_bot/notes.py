from dataclasses import dataclass
from typing import Any

from notes_bot.supabase_session import SupabaseSessionManager

NOTE_COLUMNS = "id,title,updated_at"
NOTE_DETAIL_COLUMNS = "id,title,content,created_at,updated_at"
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


@dataclass(frozen=True)
class Note:
    id: str
    title: str
    content: str | None
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> Note:
        return cls(
            id=str(row["id"]),
            title=str(row["title"]),
            content=row.get("content"),
            created_at=str(row["created_at"]),
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


async def get_note(
    session_manager: SupabaseSessionManager,
    *,
    telegram_user_id: int,
    note_id: str,
) -> Note | None:
    client = await session_manager.authenticated_client(
        telegram_user_id=telegram_user_id,
    )

    response = await (
        client.table("notes")
        .select(NOTE_DETAIL_COLUMNS)
        .eq("id", note_id)
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    return Note.from_row(response.data[0])
