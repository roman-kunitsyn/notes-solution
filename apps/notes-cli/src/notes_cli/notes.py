from dataclasses import dataclass
from typing import Any

from notes_cli.client import authenticated_client

NOTE_COLUMNS = "id,title,content,created_at,updated_at"


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


def list_notes(limit: int = 50) -> list[Note]:
    client = authenticated_client()

    response = (
        client.table("notes")
        .select(NOTE_COLUMNS)
        .order("updated_at", desc=True)
        .limit(limit)
        .execute()
    )

    return [Note.from_row(row) for row in response.data or []]


def get_note(note_id: str) -> Note | None:
    client = authenticated_client()

    response = (
        client.table("notes")
        .select(NOTE_COLUMNS)
        .eq("id", note_id)
        .maybe_single()
        .execute()
    )

    if response.data is None:
        return None

    return Note.from_row(response.data)


def create_note(title: str, content: str) -> Note:
    client = authenticated_client()

    # Do not send user_id. PostgreSQL defaults ownership to auth.uid(),
    # and RLS remains responsible for enforcing that ownership.
    response = (
        client.table("notes")
        .insert(
            {
                "title": title,
                "content": content,
            }
        )
        .select(NOTE_COLUMNS)
        .execute()
    )

    if not response.data:
        raise RuntimeError("Supabase did not return the created note")

    return Note.from_row(response.data[0])
