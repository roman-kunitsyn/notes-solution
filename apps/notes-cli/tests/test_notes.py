from notes_cli.notes import Note


def test_note_from_row() -> None:
    note = Note.from_row(
        {
            "id": "123",
            "title": "Test note",
            "content": "Hello",
            "created_at": "2026-08-29T00:00:00+00:00",
            "updated_at": "2026-08-29T01:00:00+00:00",
        }
    )

    assert note.id == "123"
    assert note.title == "Test note"
    assert note.content == "Hello"
    assert note.updated_at == "2026-08-29T01:00:00+00:00"
