import argparse
import asyncio
import logging
import sys
from collections.abc import Sequence

from aiogram import Bot, Dispatcher, Router
from aiogram.enums import ChatType
from aiogram.exceptions import (
    TelegramNetworkError,
    TelegramUnauthorizedError,
)
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from aiogram.utils.token import TokenValidationError

from notes_bot.config import (
    ConfigurationError,
    load_settings,
)
from notes_bot.http_server import (
    HttpServer,
    create_http_app,
)
from notes_bot.link_service import LinkingService
from notes_bot.notes import (
    DEFAULT_LIST_LIMIT,
    NoteSummary,
    list_notes,
)
from notes_bot.sessions import TokenCipher
from notes_bot.supabase_otp import SupabaseOtpService
from notes_bot.supabase_session import (
    SessionExpired,
    SessionIdentityMismatch,
    SessionNotLinked,
    SupabaseSessionManager,
)

router = Router(name=__name__)

NOTE_TITLE_DISPLAY_LIMIT = 120


def build_start_message(
    first_name: str | None,
) -> str:
    greeting = f"Hello, {first_name}!" if first_name else "Hello!"

    return (
        f"{greeting}\n\n"
        "I can help you manage your private notes.\n\n"
        "To continue, securely link your "
        "Supabase account."
    )


@router.message(CommandStart())
async def handle_start(
    message: Message,
    linking_service: LinkingService,
) -> None:
    if message.chat.type != ChatType.PRIVATE:
        await message.answer("Account linking is available only in a private chat.")
        return

    if message.from_user is None:
        await message.answer("Telegram did not provide your user identity.")
        return

    linking_url = await linking_service.issue_url(
        telegram_user_id=message.from_user.id,
        telegram_chat_id=message.chat.id,
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Link Supabase account",
                    url=linking_url,
                )
            ]
        ]
    )

    await message.answer(
        build_start_message(message.from_user.first_name),
        reply_markup=keyboard,
    )


def display_note_title(title: str) -> str:
    normalized = " ".join(title.split())

    if len(normalized) <= NOTE_TITLE_DISPLAY_LIMIT:
        return normalized

    return f"{normalized[: NOTE_TITLE_DISPLAY_LIMIT - 3]}..."


def build_notes_message(notes: list[NoteSummary]) -> str:
    if not notes:
        return "You do not have any notes yet."

    entries = [
        f"{note.id}\n{note.updated_at}  {display_note_title(note.title)}"
        for note in notes
    ]

    return "Your latest notes:\n\n" + "\n\n".join(entries)


@router.message(Command("notes"))
async def handle_notes(
    message: Message,
    session_manager: SupabaseSessionManager,
) -> None:
    if message.chat.type != ChatType.PRIVATE:
        await message.answer("Notes are available only in a private chat.")
        return

    if message.from_user is None:
        await message.answer("Telegram did not provide your user identity.")
        return

    try:
        notes = await list_notes(
            session_manager,
            telegram_user_id=message.from_user.id,
            limit=DEFAULT_LIST_LIMIT,
        )
    except SessionNotLinked:
        await message.answer("Link your account first using /start.")
        return
    except SessionExpired, SessionIdentityMismatch:
        await message.answer("Your account link has expired. Use /start to link again.")
        return
    except Exception:  # noqa: BLE001 - Telegram responses must not leak backend errors.
        await message.answer("I could not load your notes right now. Please try again.")
        return

    await message.answer(build_notes_message(notes))


def create_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    return dispatcher


async def run() -> None:
    settings = load_settings()
    linking_service = LinkingService(
        database_path=settings.database_path,
        base_url=settings.bot_base_url,
    )
    cipher = TokenCipher(settings.encryption_key)
    otp_service = SupabaseOtpService(
        supabase_url=settings.supabase_url,
        publishable_key=settings.supabase_publishable_key,
        database_path=settings.database_path,
        cipher=cipher,
    )
    session_manager = SupabaseSessionManager(
        supabase_url=settings.supabase_url,
        publishable_key=settings.supabase_publishable_key,
        database_path=settings.database_path,
        cipher=cipher,
    )
    dispatcher = create_dispatcher()

    http_server = HttpServer(
        application=create_http_app(
            database_path=settings.database_path,
            otp_service=otp_service,
        ),
        host=settings.http_host,
        port=settings.http_port,
    )

    await http_server.start()

    try:
        async with Bot(
            token=settings.telegram_bot_token,
        ) as bot:
            await dispatcher.start_polling(
                bot,
                allowed_updates=(dispatcher.resolve_used_update_types()),
                linking_service=linking_service,
                session_manager=session_manager,
            )
    finally:
        await http_server.stop()


def parse_arguments(
    arguments: Sequence[str] | None = None,
) -> None:
    parser = argparse.ArgumentParser(
        description="Run the Notes Telegram bot using long polling.",
    )

    parser.parse_args(arguments)


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format=("%(asctime)s %(levelname)s %(name)s: %(message)s"),
    )


def main(
    arguments: Sequence[str] | None = None,
) -> None:
    parse_arguments(arguments)
    configure_logging()

    try:
        asyncio.run(run())
    except ConfigurationError as error:
        print(
            f"Configuration error: {error}",
            file=sys.stderr,
        )
        raise SystemExit(2) from error
    except TokenValidationError as error:
        print(
            "Configuration error: TELEGRAM_BOT_TOKEN has an invalid format",
            file=sys.stderr,
        )
        raise SystemExit(2) from error
    except TelegramUnauthorizedError as error:
        print(
            "Telegram rejected TELEGRAM_BOT_TOKEN",
            file=sys.stderr,
        )
        raise SystemExit(3) from error
    except TelegramNetworkError as error:
        print(
            "Could not connect to Telegram",
            file=sys.stderr,
        )
        raise SystemExit(4) from error
    except KeyboardInterrupt:
        logging.getLogger(__name__).info(
            "Bot stopped by user",
        )
