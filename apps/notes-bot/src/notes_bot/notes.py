from dataclasses import dataclass
from typing import Any

from notes_bot.supabase_session import SupabaseSessionManager

NOTE_COLUMNS = "id,title,updated_at"
NOTE_DETAIL_COLUMNS = "id,title,content,created_at,updated_at"
DEFAULT_LIST_LIMIT = 20
ATTACHMENT_BUCKET = "note-attachments"
DEFAULT_ATTACHMENT_LIST_LIMIT = 100


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


@dataclass(frozen=True)
class AttachmentSummary:
    name: str
    size: int
    created_at: str

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> AttachmentSummary:
        metadata = row.get("metadata") or {}

        return cls(
            name=str(row["name"]),
            size=int(metadata.get("size") or 0),
            created_at=str(row.get("created_at") or ""),
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


async def list_attachments(
    session_manager: SupabaseSessionManager,
    *,
    telegram_user_id: int,
    note_id: str,
) -> list[AttachmentSummary] | None:
    client = await session_manager.authenticated_client(
        telegram_user_id=telegram_user_id,
    )

    # Confirm that the linked user can see the note before listing its objects.
    # The same authenticated client is then used for the Storage request, where
    # the bucket's RLS policy remains the authorization boundary.
    note_response = await (
        client.table("notes").select("id").eq("id", note_id).limit(1).execute()
    )

    if not note_response.data:
        return None

    user_response = await client.auth.get_user()

    if user_response.user is None:
        raise RuntimeError("Supabase session has no authenticated user")

    rows = await client.storage.from_(ATTACHMENT_BUCKET).list(
        f"{user_response.user.id}/{note_id}",
        {
            "limit": DEFAULT_ATTACHMENT_LIST_LIMIT,
            "offset": 0,
            "sortBy": {
                "column": "name",
                "order": "asc",
            },
        },
    )

    return [AttachmentSummary.from_row(row) for row in rows]


async def create_note(
    session_manager: SupabaseSessionManager,
    *,
    telegram_user_id: int,
    title: str,
    content: str,
) -> Note:
    client = await session_manager.authenticated_client(
        telegram_user_id=telegram_user_id,
    )

    # Do not send user_id. PostgreSQL derives ownership from auth.uid(), and
    # RLS enforces that the linked user can create only their own notes.
    response = await (
        client.table("notes")
        .insert(
            {
                "title": title,
                "content": content,
            }
        )
        .select(NOTE_DETAIL_COLUMNS)
        .execute()
    )

    if not response.data:
        raise RuntimeError("Supabase did not return the created note")

    return Note.from_row(response.data[0])


async def update_note(
    session_manager: SupabaseSessionManager,
    *,
    telegram_user_id: int,
    note_id: str,
    title: str,
    content: str,
) -> Note | None:
    client = await session_manager.authenticated_client(
        telegram_user_id=telegram_user_id,
    )

    # RLS restricts the update to notes owned by the linked user.
    response = await (
        client.table("notes")
        .update(
            {
                "title": title,
                "content": content,
            }
        )
        .eq("id", note_id)
        .select(NOTE_DETAIL_COLUMNS)
        .execute()
    )

    if not response.data:
        return None

    return Note.from_row(response.data[0])


async def delete_note(
    session_manager: SupabaseSessionManager,
    *,
    telegram_user_id: int,
    note_id: str,
) -> Note | None:
    client = await session_manager.authenticated_client(
        telegram_user_id=telegram_user_id,
    )

    # RLS restricts the deletion to notes owned by the linked user.
    response = await (
        client.table("notes")
        .delete()
        .eq("id", note_id)
        .select(NOTE_DETAIL_COLUMNS)
        .execute()
    )

    if not response.data:
        return None

    return Note.from_row(response.data[0])
