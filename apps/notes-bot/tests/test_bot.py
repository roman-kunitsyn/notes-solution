from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.enums import ChatType

from notes_bot.bot import (
    build_start_message,
    create_dispatcher,
    handle_start,
    main,
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
