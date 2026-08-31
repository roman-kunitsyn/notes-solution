from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from notes_bot.notes import (
    DEFAULT_LIST_LIMIT,
    NOTE_COLUMNS,
    list_notes,
)


class FakeQuery:
    def __init__(self) -> None:
        self.data = [
            {
                "id": "note-1",
                "title": "Latest note",
                "updated_at": "2026-09-01T10:00:00+00:00",
            }
        ]

    def select_columns(self, columns: str):
        assert columns == NOTE_COLUMNS
        return self

    def order(self, column: str, *, desc: bool):
        assert column == "updated_at"
        assert desc is True
        return self

    def limit(self, value: int):
        assert value == DEFAULT_LIST_LIMIT
        return self

    async def execute(self):
        return SimpleNamespace(data=self.data)


async def test_list_notes_uses_linked_user_session_and_recent_first_query() -> None:
    query = FakeQuery()
    query.select = query.select_columns
    client = SimpleNamespace(table=Mock(return_value=query))
    session_manager = SimpleNamespace(
        authenticated_client=AsyncMock(return_value=client)
    )

    notes = await list_notes(
        session_manager,
        telegram_user_id=100,
    )

    session_manager.authenticated_client.assert_awaited_once_with(telegram_user_id=100)
    client.table.assert_called_once_with("notes")
    assert [(note.id, note.title, note.updated_at) for note in notes] == [
        ("note-1", "Latest note", "2026-09-01T10:00:00+00:00")
    ]
