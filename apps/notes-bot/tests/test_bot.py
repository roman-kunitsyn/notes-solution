from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.enums import ChatType

from notes_bot.bot import (
    build_notes_message,
    build_start_message,
    create_dispatcher,
    display_note_title,
    handle_notes,
    handle_start,
    main,
)
from notes_bot.notes import NoteSummary
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
