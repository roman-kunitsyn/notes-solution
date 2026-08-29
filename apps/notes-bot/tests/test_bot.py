from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from notes_bot.bot import (
    build_start_message,
    create_dispatcher,
    handle_start,
    main,
)


def test_build_start_message_uses_first_name() -> None:
    text = build_start_message("Roman")

    assert "Hello, Roman!" in text
    assert "not linked yet" in text


def test_build_start_message_handles_missing_user() -> None:
    text = build_start_message(None)

    assert text.startswith("Hello!")
    assert "not linked yet" in text


def test_create_dispatcher_registers_router() -> None:
    dispatcher = create_dispatcher()

    assert dispatcher.sub_routers


async def test_handle_start_answers_user() -> None:
    message = SimpleNamespace(
        from_user=SimpleNamespace(
            first_name="Roman",
        ),
        answer=AsyncMock(),
    )

    await handle_start(message)

    message.answer.assert_awaited_once()

    response = message.answer.await_args.args[0]

    assert "Hello, Roman!" in response
    assert "not linked yet" in response


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
