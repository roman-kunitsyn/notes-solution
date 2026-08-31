from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from notes_bot.notes import (
    DEFAULT_LIST_LIMIT,
    NOTE_COLUMNS,
    NOTE_DETAIL_COLUMNS,
    create_note,
    delete_note,
    get_note,
    list_notes,
    update_note,
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


class FakeDetailQuery:
    def __init__(self, data: list[dict[str, str]] | None) -> None:
        self.data = data

    def select_columns(self, columns: str):
        assert columns == NOTE_DETAIL_COLUMNS
        return self

    def eq(self, column: str, value: str):
        assert column == "id"
        assert value == "123e4567-e89b-12d3-a456-426614174000"
        return self

    def limit(self, value: int):
        assert value == 1
        return self

    async def execute(self):
        return SimpleNamespace(data=self.data)


async def test_get_note_uses_linked_user_session_and_rls_scoped_query() -> None:
    query = FakeDetailQuery(
        [
            {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "Private note",
                "content": "Only the owner can read this.",
                "created_at": "2026-09-01T09:00:00+00:00",
                "updated_at": "2026-09-01T10:00:00+00:00",
            }
        ]
    )
    query.select = query.select_columns
    client = SimpleNamespace(table=Mock(return_value=query))
    session_manager = SimpleNamespace(
        authenticated_client=AsyncMock(return_value=client)
    )

    note = await get_note(
        session_manager,
        telegram_user_id=100,
        note_id="123e4567-e89b-12d3-a456-426614174000",
    )

    session_manager.authenticated_client.assert_awaited_once_with(telegram_user_id=100)
    client.table.assert_called_once_with("notes")
    assert note is not None
    assert note.title == "Private note"
    assert note.content == "Only the owner can read this."


async def test_get_note_returns_none_when_rls_hides_or_omits_note() -> None:
    query = FakeDetailQuery([])
    query.select = query.select_columns
    client = SimpleNamespace(table=Mock(return_value=query))
    session_manager = SimpleNamespace(
        authenticated_client=AsyncMock(return_value=client)
    )

    note = await get_note(
        session_manager,
        telegram_user_id=100,
        note_id="123e4567-e89b-12d3-a456-426614174000",
    )

    assert note is None


class FakeCreateQuery:
    def __init__(self) -> None:
        self.data = [
            {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "New note",
                "content": "Created privately.",
                "created_at": "2026-09-01T09:00:00+00:00",
                "updated_at": "2026-09-01T09:00:00+00:00",
            }
        ]

    def insert(self, values: dict[str, str]):
        assert values == {
            "title": "New note",
            "content": "Created privately.",
        }
        assert "user_id" not in values
        return self

    def select_columns(self, columns: str):
        assert columns == NOTE_DETAIL_COLUMNS
        return self

    async def execute(self):
        return SimpleNamespace(data=self.data)


async def test_create_note_uses_linked_user_session_and_rls_owned_insert() -> None:
    query = FakeCreateQuery()
    query.select = query.select_columns
    client = SimpleNamespace(table=Mock(return_value=query))
    session_manager = SimpleNamespace(
        authenticated_client=AsyncMock(return_value=client)
    )

    note = await create_note(
        session_manager,
        telegram_user_id=100,
        title="New note",
        content="Created privately.",
    )

    session_manager.authenticated_client.assert_awaited_once_with(telegram_user_id=100)
    client.table.assert_called_once_with("notes")
    assert note.title == "New note"
    assert note.content == "Created privately."


class FakeUpdateQuery:
    def __init__(self, data: list[dict[str, str]] | None) -> None:
        self.data = data

    def update(self, values: dict[str, str]):
        assert values == {
            "title": "Updated note",
            "content": "Updated privately.",
        }
        assert "user_id" not in values
        return self

    def eq(self, column: str, value: str):
        assert column == "id"
        assert value == "123e4567-e89b-12d3-a456-426614174000"
        return self

    def select_columns(self, columns: str):
        assert columns == NOTE_DETAIL_COLUMNS
        return self

    async def execute(self):
        return SimpleNamespace(data=self.data)


async def test_update_note_uses_linked_user_session_and_rls_scoped_update() -> None:
    query = FakeUpdateQuery(
        [
            {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "Updated note",
                "content": "Updated privately.",
                "created_at": "2026-09-01T09:00:00+00:00",
                "updated_at": "2026-09-01T11:00:00+00:00",
            }
        ]
    )
    query.select = query.select_columns
    client = SimpleNamespace(table=Mock(return_value=query))
    session_manager = SimpleNamespace(
        authenticated_client=AsyncMock(return_value=client)
    )

    note = await update_note(
        session_manager,
        telegram_user_id=100,
        note_id="123e4567-e89b-12d3-a456-426614174000",
        title="Updated note",
        content="Updated privately.",
    )

    session_manager.authenticated_client.assert_awaited_once_with(telegram_user_id=100)
    client.table.assert_called_once_with("notes")
    assert note is not None
    assert note.title == "Updated note"
    assert note.content == "Updated privately."


async def test_update_note_returns_none_when_rls_hides_or_omits_note() -> None:
    query = FakeUpdateQuery([])
    query.select = query.select_columns
    client = SimpleNamespace(table=Mock(return_value=query))
    session_manager = SimpleNamespace(
        authenticated_client=AsyncMock(return_value=client)
    )

    note = await update_note(
        session_manager,
        telegram_user_id=100,
        note_id="123e4567-e89b-12d3-a456-426614174000",
        title="Updated note",
        content="Updated privately.",
    )

    assert note is None


class FakeDeleteQuery:
    def __init__(self, data: list[dict[str, str]] | None) -> None:
        self.data = data

    def delete(self):
        return self

    def eq(self, column: str, value: str):
        assert column == "id"
        assert value == "123e4567-e89b-12d3-a456-426614174000"
        return self

    def select_columns(self, columns: str):
        assert columns == NOTE_DETAIL_COLUMNS
        return self

    async def execute(self):
        return SimpleNamespace(data=self.data)


async def test_delete_note_uses_linked_user_session_and_rls_scoped_delete() -> None:
    query = FakeDeleteQuery(
        [
            {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "Deleted note",
                "content": "Deleted privately.",
                "created_at": "2026-09-01T09:00:00+00:00",
                "updated_at": "2026-09-01T11:00:00+00:00",
            }
        ]
    )
    query.select = query.select_columns
    client = SimpleNamespace(table=Mock(return_value=query))
    session_manager = SimpleNamespace(
        authenticated_client=AsyncMock(return_value=client)
    )

    note = await delete_note(
        session_manager,
        telegram_user_id=100,
        note_id="123e4567-e89b-12d3-a456-426614174000",
    )

    session_manager.authenticated_client.assert_awaited_once_with(telegram_user_id=100)
    client.table.assert_called_once_with("notes")
    assert note is not None
    assert note.title == "Deleted note"


async def test_delete_note_returns_none_when_rls_hides_or_omits_note() -> None:
    query = FakeDeleteQuery([])
    query.select = query.select_columns
    client = SimpleNamespace(table=Mock(return_value=query))
    session_manager = SimpleNamespace(
        authenticated_client=AsyncMock(return_value=client)
    )

    note = await delete_note(
        session_manager,
        telegram_user_id=100,
        note_id="123e4567-e89b-12d3-a456-426614174000",
    )

    assert note is None
