from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.enums import ChatType

from notes_bot.bot import (
    build_note_message,
    build_notes_message,
    build_start_message,
    create_dispatcher,
    display_note_title,
    handle_create,
    handle_delete,
    handle_edit,
    handle_note,
    handle_notes,
    handle_start,
    main,
    parse_note_creation,
    parse_note_edit,
    parse_note_id,
)
from notes_bot.notes import Note, NoteSummary
from notes_bot.supabase_session import (
    SessionExpired,
    SessionIdentityMismatch,
    SessionNotLinked,
)


def test_build_start_message_uses_first_name() -> None:
    text = build_start_message("Roman")

    assert "Hello, Roman!" in text
    assert "securely link your Supabase account" in text


def test_build_start_message_handles_missing_user() -> None:
    text = build_start_message(None)

    assert text.startswith("Hello!")
    assert "securely link your Supabase account" in text


def test_create_dispatcher_registers_router() -> None:
    dispatcher = create_dispatcher()

    assert dispatcher.sub_routers


async def test_handle_start_answers_user() -> None:
    linking_service = SimpleNamespace(
        issue_url=AsyncMock(return_value=("http://127.0.0.1:8080/link#token=test"))
    )

    message = SimpleNamespace(
        from_user=SimpleNamespace(
            id=100,
            first_name="Roman",
        ),
        chat=SimpleNamespace(
            id=100,
            type=ChatType.PRIVATE,
        ),
        answer=AsyncMock(),
    )

    await handle_start(
        message,
        linking_service,
    )

    linking_service.issue_url.assert_awaited_once_with(
        telegram_user_id=100,
        telegram_chat_id=100,
    )
    message.answer.assert_awaited_once()

    arguments = message.answer.await_args

    assert "Hello, Roman!" in arguments.args[0]

    keyboard = arguments.kwargs["reply_markup"]

    button = keyboard.inline_keyboard[0][0]

    assert button.text == "Link Supabase account"
    assert button.url is not None
    assert button.url.startswith("http://127.0.0.1:8080/link#")


def test_main_reports_missing_configuration(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv(
        "TELEGRAM_BOT_TOKEN",
        raising=False,
    )

    with pytest.raises(SystemExit) as error:
        main([])

    assert error.value.code == 2

    captured = capsys.readouterr()

    assert "Missing configuration" in captured.err
    assert "TELEGRAM_BOT_TOKEN" in captured.err


def test_main_help_does_not_require_configuration(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv(
        "TELEGRAM_BOT_TOKEN",
        raising=False,
    )

    with pytest.raises(SystemExit) as error:
        main(["--help"])

    assert error.value.code == 0

    captured = capsys.readouterr()

    assert "Notes Telegram bot" in captured.out


async def test_handle_start_rejects_group_chat() -> None:
    linking_service = SimpleNamespace(issue_url=AsyncMock())

    message = SimpleNamespace(
        from_user=SimpleNamespace(
            id=100,
            first_name="Roman",
        ),
        chat=SimpleNamespace(
            id=-100,
            type=ChatType.GROUP,
        ),
        answer=AsyncMock(),
    )

    await handle_start(
        message,
        linking_service,
    )

    linking_service.issue_url.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "Account linking is available only in a private chat."
    )


def test_display_note_title_collapses_whitespace_and_truncates() -> None:
    assert display_note_title("  A\n\n note  ") == "A note"
    assert display_note_title("x" * 121) == ("x" * 117) + "..."


def test_build_notes_message_shows_note_summaries() -> None:
    text = build_notes_message(
        [
            NoteSummary(
                id="note-1",
                title="First note",
                updated_at="2026-09-01T10:00:00+00:00",
            )
        ]
    )

    assert "Your latest notes:" in text
    assert "note-1" in text
    assert "First note" in text


def test_build_notes_message_has_empty_state() -> None:
    assert build_notes_message([]) == "You do not have any notes yet."


def test_build_note_message_shows_full_note() -> None:
    text = build_note_message(
        Note(
            id="123e4567-e89b-12d3-a456-426614174000",
            title="First note",
            content="The complete note content.",
            created_at="2026-09-01T09:00:00+00:00",
            updated_at="2026-09-01T10:00:00+00:00",
        )
    )

    assert "ID: 123e4567-e89b-12d3-a456-426614174000" in text
    assert "Title: First note" in text
    assert "Updated: 2026-09-01T10:00:00+00:00" in text
    assert text.endswith("The complete note content.")


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        (
            "123e4567-e89b-12d3-a456-426614174000",
            "123e4567-e89b-12d3-a456-426614174000",
        ),
        (None, None),
        ("", None),
        ("not-a-note-id", None),
        ("123e4567-e89b-12d3-a456-426614174000 extra", None),
    ],
)
def test_parse_note_id_requires_one_uuid(
    arguments: str | None, expected: str | None
) -> None:
    assert parse_note_id(arguments) == expected


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        ("New note", ("New note", "")),
        ("  New note  \nContent", ("New note", "Content")),
        ("New note\n\nContent", ("New note", "\nContent")),
        (None, None),
        ("   \nContent", None),
    ],
)
def test_parse_note_creation_uses_first_line_as_required_title(
    arguments: str | None, expected: tuple[str, str] | None
) -> None:
    assert parse_note_creation(arguments) == expected


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        (
            "123e4567-e89b-12d3-a456-426614174000\nUpdated note\nContent",
            (
                "123e4567-e89b-12d3-a456-426614174000",
                "Updated note",
                "Content",
            ),
        ),
        (
            "123e4567-e89b-12d3-a456-426614174000\nUpdated note",
            (
                "123e4567-e89b-12d3-a456-426614174000",
                "Updated note",
                "",
            ),
        ),
        (None, None),
        ("not-a-note-id\nUpdated note", None),
        ("123e4567-e89b-12d3-a456-426614174000", None),
        ("123e4567-e89b-12d3-a456-426614174000\n  \nContent", None),
    ],
)
def test_parse_note_edit_requires_a_note_id_and_nonempty_title(
    arguments: str | None, expected: tuple[str, str, str] | None
) -> None:
    assert parse_note_edit(arguments) == expected


async def test_handle_notes_answers_with_linked_users_notes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_manager = SimpleNamespace()
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=100),
        chat=SimpleNamespace(id=100, type=ChatType.PRIVATE),
        answer=AsyncMock(),
    )

    list_notes_mock = AsyncMock(
        return_value=[
            NoteSummary(
                id="note-1",
                title="First note",
                updated_at="2026-09-01T10:00:00+00:00",
            )
        ]
    )

    monkeypatch.setattr("notes_bot.bot.list_notes", list_notes_mock)

    await handle_notes(message, session_manager)

    assert "First note" in message.answer.await_args.args[0]
    list_notes_mock.assert_awaited_once_with(
        session_manager,
        telegram_user_id=100,
        limit=20,
    )


async def test_handle_notes_rejects_group_chat_without_loading_notes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_manager = SimpleNamespace()
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=100),
        chat=SimpleNamespace(id=-100, type=ChatType.GROUP),
        answer=AsyncMock(),
    )
    list_notes_mock = AsyncMock()

    monkeypatch.setattr("notes_bot.bot.list_notes", list_notes_mock)

    await handle_notes(message, session_manager)

    list_notes_mock.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "Notes are available only in a private chat."
    )


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (SessionNotLinked("missing"), "Link your account first using /start."),
        (
            SessionExpired("expired"),
            "Your account link has expired. Use /start to link again.",
        ),
        (
            SessionIdentityMismatch("mismatch"),
            "Your account link has expired. Use /start to link again.",
        ),
    ],
)
async def test_handle_notes_maps_session_failures_to_safe_messages(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    expected: str,
) -> None:
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=100),
        chat=SimpleNamespace(id=100, type=ChatType.PRIVATE),
        answer=AsyncMock(),
    )
    session_manager = SimpleNamespace()

    monkeypatch.setattr(
        "notes_bot.bot.list_notes",
        AsyncMock(side_effect=error),
    )

    await handle_notes(message, session_manager)

    message.answer.assert_awaited_once_with(expected)


async def test_handle_notes_hides_unexpected_error_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=100),
        chat=SimpleNamespace(id=100, type=ChatType.PRIVATE),
        answer=AsyncMock(),
    )
    session_manager = SimpleNamespace()

    monkeypatch.setattr(
        "notes_bot.bot.list_notes",
        AsyncMock(side_effect=RuntimeError("access token leaked")),
    )

    await handle_notes(message, session_manager)

    message.answer.assert_awaited_once_with(
        "I could not load your notes right now. Please try again."
    )


async def test_handle_note_answers_with_the_linked_users_note(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_manager = SimpleNamespace()
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=100),
        chat=SimpleNamespace(id=100, type=ChatType.PRIVATE),
        answer=AsyncMock(),
    )
    note_id = "123e4567-e89b-12d3-a456-426614174000"
    get_note_mock = AsyncMock(
        return_value=Note(
            id=note_id,
            title="First note",
            content="Private content",
            created_at="2026-09-01T09:00:00+00:00",
            updated_at="2026-09-01T10:00:00+00:00",
        )
    )
    monkeypatch.setattr("notes_bot.bot.get_note", get_note_mock)

    await handle_note(
        message,
        SimpleNamespace(args=note_id),
        session_manager,
    )

    get_note_mock.assert_awaited_once_with(
        session_manager,
        telegram_user_id=100,
        note_id=note_id,
    )
    assert "Private content" in message.answer.await_args.args[0]


async def test_handle_note_rejects_group_chat_without_loading_note(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=100),
        chat=SimpleNamespace(id=-100, type=ChatType.GROUP),
        answer=AsyncMock(),
    )
    get_note_mock = AsyncMock()
    monkeypatch.setattr("notes_bot.bot.get_note", get_note_mock)

    await handle_note(
        message,
        SimpleNamespace(args="123e4567-e89b-12d3-a456-426614174000"),
        SimpleNamespace(),
    )

    get_note_mock.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "Notes are available only in a private chat."
    )


async def test_handle_note_requires_one_note_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=100),
        chat=SimpleNamespace(id=100, type=ChatType.PRIVATE),
        answer=AsyncMock(),
    )
    get_note_mock = AsyncMock()
    monkeypatch.setattr("notes_bot.bot.get_note", get_note_mock)

    await handle_note(message, SimpleNamespace(args="not-a-note-id"), SimpleNamespace())

    get_note_mock.assert_not_awaited()
    message.answer.assert_awaited_once_with("Usage: /note NOTE_ID")


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (SessionNotLinked("missing"), "Link your account first using /start."),
        (
            SessionExpired("expired"),
            "Your account link has expired. Use /start to link again.",
        ),
        (
            SessionIdentityMismatch("mismatch"),
            "Your account link has expired. Use /start to link again.",
        ),
    ],
)
async def test_handle_note_maps_session_failures_to_safe_messages(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    expected: str,
) -> None:
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=100),
        chat=SimpleNamespace(id=100, type=ChatType.PRIVATE),
        answer=AsyncMock(),
    )
    monkeypatch.setattr("notes_bot.bot.get_note", AsyncMock(side_effect=error))

    await handle_note(
        message,
        SimpleNamespace(args="123e4567-e89b-12d3-a456-426614174000"),
        SimpleNamespace(),
    )

    message.answer.assert_awaited_once_with(expected)


async def test_handle_note_reports_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=100),
        chat=SimpleNamespace(id=100, type=ChatType.PRIVATE),
        answer=AsyncMock(),
    )
    monkeypatch.setattr("notes_bot.bot.get_note", AsyncMock(return_value=None))

    await handle_note(
        message,
        SimpleNamespace(args="123e4567-e89b-12d3-a456-426614174000"),
        SimpleNamespace(),
    )

    message.answer.assert_awaited_once_with("Note not found.")


async def test_handle_note_hides_unexpected_error_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=100),
        chat=SimpleNamespace(id=100, type=ChatType.PRIVATE),
        answer=AsyncMock(),
    )
    monkeypatch.setattr(
        "notes_bot.bot.get_note",
        AsyncMock(side_effect=RuntimeError("access token leaked")),
    )

    await handle_note(
        message,
        SimpleNamespace(args="123e4567-e89b-12d3-a456-426614174000"),
        SimpleNamespace(),
    )

    message.answer.assert_awaited_once_with(
        "I could not load that note right now. Please try again."
    )


async def test_handle_create_creates_a_linked_users_note(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_manager = SimpleNamespace()
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=100),
        chat=SimpleNamespace(id=100, type=ChatType.PRIVATE),
        answer=AsyncMock(),
    )
    create_note_mock = AsyncMock(
        return_value=Note(
            id="123e4567-e89b-12d3-a456-426614174000",
            title="New note",
            content="Private content",
            created_at="2026-09-01T09:00:00+00:00",
            updated_at="2026-09-01T09:00:00+00:00",
        )
    )
    monkeypatch.setattr("notes_bot.bot.create_note", create_note_mock)

    await handle_create(
        message,
        SimpleNamespace(args="New note\nPrivate content"),
        session_manager,
    )

    create_note_mock.assert_awaited_once_with(
        session_manager,
        telegram_user_id=100,
        title="New note",
        content="Private content",
    )
    assert "Note created." in message.answer.await_args.args[0]
    assert "Private content" in message.answer.await_args.args[0]


async def test_handle_create_rejects_group_chat_without_creating_note(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=100),
        chat=SimpleNamespace(id=-100, type=ChatType.GROUP),
        answer=AsyncMock(),
    )
    create_note_mock = AsyncMock()
    monkeypatch.setattr("notes_bot.bot.create_note", create_note_mock)

    await handle_create(message, SimpleNamespace(args="New note"), SimpleNamespace())

    create_note_mock.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "Notes are available only in a private chat."
    )


async def test_handle_create_requires_a_nonempty_title(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=100),
        chat=SimpleNamespace(id=100, type=ChatType.PRIVATE),
        answer=AsyncMock(),
    )
    create_note_mock = AsyncMock()
    monkeypatch.setattr("notes_bot.bot.create_note", create_note_mock)

    await handle_create(message, SimpleNamespace(args="  \nContent"), SimpleNamespace())

    create_note_mock.assert_not_awaited()
    message.answer.assert_awaited_once_with("Usage: /create TITLE\\nCONTENT")


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (SessionNotLinked("missing"), "Link your account first using /start."),
        (
            SessionExpired("expired"),
            "Your account link has expired. Use /start to link again.",
        ),
        (
            SessionIdentityMismatch("mismatch"),
            "Your account link has expired. Use /start to link again.",
        ),
    ],
)
async def test_handle_create_maps_session_failures_to_safe_messages(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    expected: str,
) -> None:
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=100),
        chat=SimpleNamespace(id=100, type=ChatType.PRIVATE),
        answer=AsyncMock(),
    )
    monkeypatch.setattr(
        "notes_bot.bot.create_note",
        AsyncMock(side_effect=error),
    )

    await handle_create(message, SimpleNamespace(args="New note"), SimpleNamespace())

    message.answer.assert_awaited_once_with(expected)


async def test_handle_create_hides_unexpected_error_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=100),
        chat=SimpleNamespace(id=100, type=ChatType.PRIVATE),
        answer=AsyncMock(),
    )
    monkeypatch.setattr(
        "notes_bot.bot.create_note",
        AsyncMock(side_effect=RuntimeError("access token leaked")),
    )

    await handle_create(message, SimpleNamespace(args="New note"), SimpleNamespace())

    message.answer.assert_awaited_once_with(
        "I could not create that note right now. Please try again."
    )


async def test_handle_edit_updates_a_linked_users_note(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_manager = SimpleNamespace()
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=100),
        chat=SimpleNamespace(id=100, type=ChatType.PRIVATE),
        answer=AsyncMock(),
    )
    note_id = "123e4567-e89b-12d3-a456-426614174000"
    update_note_mock = AsyncMock(
        return_value=Note(
            id=note_id,
            title="Updated note",
            content="Updated content",
            created_at="2026-09-01T09:00:00+00:00",
            updated_at="2026-09-01T11:00:00+00:00",
        )
    )
    monkeypatch.setattr("notes_bot.bot.update_note", update_note_mock)

    await handle_edit(
        message,
        SimpleNamespace(args=f"{note_id}\nUpdated note\nUpdated content"),
        session_manager,
    )

    update_note_mock.assert_awaited_once_with(
        session_manager,
        telegram_user_id=100,
        note_id=note_id,
        title="Updated note",
        content="Updated content",
    )
    assert "Note updated." in message.answer.await_args.args[0]
    assert "Updated content" in message.answer.await_args.args[0]


async def test_handle_edit_rejects_group_chat_without_updating_note(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=100),
        chat=SimpleNamespace(id=-100, type=ChatType.GROUP),
        answer=AsyncMock(),
    )
    update_note_mock = AsyncMock()
    monkeypatch.setattr("notes_bot.bot.update_note", update_note_mock)

    await handle_edit(message, SimpleNamespace(args="unused"), SimpleNamespace())

    update_note_mock.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "Notes are available only in a private chat."
    )


async def test_handle_edit_requires_a_note_id_and_nonempty_title(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=100),
        chat=SimpleNamespace(id=100, type=ChatType.PRIVATE),
        answer=AsyncMock(),
    )
    update_note_mock = AsyncMock()
    monkeypatch.setattr("notes_bot.bot.update_note", update_note_mock)

    await handle_edit(
        message,
        SimpleNamespace(args="123e4567-e89b-12d3-a456-426614174000\n  \nContent"),
        SimpleNamespace(),
    )

    update_note_mock.assert_not_awaited()
    message.answer.assert_awaited_once_with("Usage: /edit NOTE_ID\\nTITLE\\nCONTENT")


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (SessionNotLinked("missing"), "Link your account first using /start."),
        (
            SessionExpired("expired"),
            "Your account link has expired. Use /start to link again.",
        ),
        (
            SessionIdentityMismatch("mismatch"),
            "Your account link has expired. Use /start to link again.",
        ),
    ],
)
async def test_handle_edit_maps_session_failures_to_safe_messages(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    expected: str,
) -> None:
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=100),
        chat=SimpleNamespace(id=100, type=ChatType.PRIVATE),
        answer=AsyncMock(),
    )
    monkeypatch.setattr("notes_bot.bot.update_note", AsyncMock(side_effect=error))

    await handle_edit(
        message,
        SimpleNamespace(args="123e4567-e89b-12d3-a456-426614174000\nUpdated note"),
        SimpleNamespace(),
    )

    message.answer.assert_awaited_once_with(expected)


async def test_handle_edit_reports_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=100),
        chat=SimpleNamespace(id=100, type=ChatType.PRIVATE),
        answer=AsyncMock(),
    )
    monkeypatch.setattr("notes_bot.bot.update_note", AsyncMock(return_value=None))

    await handle_edit(
        message,
        SimpleNamespace(args="123e4567-e89b-12d3-a456-426614174000\nUpdated note"),
        SimpleNamespace(),
    )

    message.answer.assert_awaited_once_with("Note not found.")


async def test_handle_edit_hides_unexpected_error_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=100),
        chat=SimpleNamespace(id=100, type=ChatType.PRIVATE),
        answer=AsyncMock(),
    )
    monkeypatch.setattr(
        "notes_bot.bot.update_note",
        AsyncMock(side_effect=RuntimeError("access token leaked")),
    )

    await handle_edit(
        message,
        SimpleNamespace(args="123e4567-e89b-12d3-a456-426614174000\nUpdated note"),
        SimpleNamespace(),
    )

    message.answer.assert_awaited_once_with(
        "I could not update that note right now. Please try again."
    )


async def test_handle_delete_removes_a_linked_users_note(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_manager = SimpleNamespace()
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=100),
        chat=SimpleNamespace(id=100, type=ChatType.PRIVATE),
        answer=AsyncMock(),
    )
    note_id = "123e4567-e89b-12d3-a456-426614174000"
    delete_note_mock = AsyncMock(
        return_value=Note(
            id=note_id,
            title="Deleted note",
            content="Deleted content",
            created_at="2026-09-01T09:00:00+00:00",
            updated_at="2026-09-01T11:00:00+00:00",
        )
    )
    monkeypatch.setattr("notes_bot.bot.delete_note", delete_note_mock)

    await handle_delete(
        message,
        SimpleNamespace(args=note_id),
        session_manager,
    )

    delete_note_mock.assert_awaited_once_with(
        session_manager,
        telegram_user_id=100,
        note_id=note_id,
    )
    message.answer.assert_awaited_once_with("Deleted: Deleted note")


async def test_handle_delete_rejects_group_chat_without_deleting_note(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=100),
        chat=SimpleNamespace(id=-100, type=ChatType.GROUP),
        answer=AsyncMock(),
    )
    delete_note_mock = AsyncMock()
    monkeypatch.setattr("notes_bot.bot.delete_note", delete_note_mock)

    await handle_delete(message, SimpleNamespace(args="unused"), SimpleNamespace())

    delete_note_mock.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "Notes are available only in a private chat."
    )


async def test_handle_delete_requires_a_telegram_user_without_deleting_note(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = SimpleNamespace(
        from_user=None,
        chat=SimpleNamespace(id=100, type=ChatType.PRIVATE),
        answer=AsyncMock(),
    )
    delete_note_mock = AsyncMock()
    monkeypatch.setattr("notes_bot.bot.delete_note", delete_note_mock)

    await handle_delete(message, SimpleNamespace(args="unused"), SimpleNamespace())

    delete_note_mock.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "Telegram did not provide your user identity."
    )


async def test_handle_delete_requires_one_valid_note_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=100),
        chat=SimpleNamespace(id=100, type=ChatType.PRIVATE),
        answer=AsyncMock(),
    )
    delete_note_mock = AsyncMock()
    monkeypatch.setattr("notes_bot.bot.delete_note", delete_note_mock)

    await handle_delete(
        message,
        SimpleNamespace(args="not-a-note-id another-argument"),
        SimpleNamespace(),
    )

    delete_note_mock.assert_not_awaited()
    message.answer.assert_awaited_once_with("Usage: /delete NOTE_ID")


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (SessionNotLinked("missing"), "Link your account first using /start."),
        (
            SessionExpired("expired"),
            "Your account link has expired. Use /start to link again.",
        ),
        (
            SessionIdentityMismatch("mismatch"),
            "Your account link has expired. Use /start to link again.",
        ),
    ],
)
async def test_handle_delete_maps_session_failures_to_safe_messages(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    expected: str,
) -> None:
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=100),
        chat=SimpleNamespace(id=100, type=ChatType.PRIVATE),
        answer=AsyncMock(),
    )
    monkeypatch.setattr("notes_bot.bot.delete_note", AsyncMock(side_effect=error))

    await handle_delete(
        message,
        SimpleNamespace(args="123e4567-e89b-12d3-a456-426614174000"),
        SimpleNamespace(),
    )

    message.answer.assert_awaited_once_with(expected)


async def test_handle_delete_reports_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=100),
        chat=SimpleNamespace(id=100, type=ChatType.PRIVATE),
        answer=AsyncMock(),
    )
    monkeypatch.setattr("notes_bot.bot.delete_note", AsyncMock(return_value=None))

    await handle_delete(
        message,
        SimpleNamespace(args="123e4567-e89b-12d3-a456-426614174000"),
        SimpleNamespace(),
    )

    message.answer.assert_awaited_once_with("Note not found.")


async def test_handle_delete_hides_unexpected_error_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=100),
        chat=SimpleNamespace(id=100, type=ChatType.PRIVATE),
        answer=AsyncMock(),
    )
    monkeypatch.setattr(
        "notes_bot.bot.delete_note",
        AsyncMock(side_effect=RuntimeError("access token leaked")),
    )

    await handle_delete(
        message,
        SimpleNamespace(args="123e4567-e89b-12d3-a456-426614174000"),
        SimpleNamespace(),
    )

    message.answer.assert_awaited_once_with(
        "I could not delete that note right now. Please try again."
    )
