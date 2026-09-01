import argparse
import asyncio
import logging
import sys
from collections.abc import Sequence
from uuid import UUID

from aiogram import Bot, Dispatcher, Router
from aiogram.enums import ChatType
from aiogram.exceptions import (
    TelegramNetworkError,
    TelegramUnauthorizedError,
)
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import (
    BufferedInputFile,
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
    AttachmentSummary,
    AttachmentTooLargeError,
    Note,
    NoteSummary,
    create_note,
    delete_note,
    download_attachment,
    get_note,
    list_attachments,
    list_notes,
    update_note,
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


def build_note_message(note: Note) -> str:
    return (
        f"ID: {note.id}\n"
        f"Title: {note.title}\n"
        f"Updated: {note.updated_at}\n\n"
        f"{note.content or ''}"
    )


def build_attachments_message(
    attachments: list[AttachmentSummary],
) -> str:
    if not attachments:
        return "That note has no attachments."

    entries = [
        f"{attachment.size} bytes  {attachment.created_at}  {attachment.name}"
        for attachment in attachments
    ]

    return "Attachments:\n\n" + "\n".join(entries)


def parse_note_id(arguments: str | None) -> str | None:
    if arguments is None:
        return None

    parts = arguments.split()

    if len(parts) != 1:
        return None

    try:
        return str(UUID(parts[0]))
    except ValueError:
        return None


def parse_note_creation(arguments: str | None) -> tuple[str, str] | None:
    if arguments is None:
        return None

    title, separator, content = arguments.partition("\n")
    normalized_title = title.strip()

    if not normalized_title:
        return None

    return normalized_title, content if separator else ""


def parse_note_edit(arguments: str | None) -> tuple[str, str, str] | None:
    if arguments is None:
        return None

    note_id, separator, draft_arguments = arguments.partition("\n")

    if not separator:
        return None

    parsed_note_id = parse_note_id(note_id)
    draft = parse_note_creation(draft_arguments)

    if parsed_note_id is None or draft is None:
        return None

    title, content = draft
    return parsed_note_id, title, content


def parse_attachment_download(arguments: str | None) -> tuple[str, str] | None:
    if arguments is None:
        return None

    note_id, separator, filename = arguments.strip().partition(" ")
    parsed_note_id = parse_note_id(note_id)
    normalized_filename = filename.strip() if separator else ""

    if parsed_note_id is None or not normalized_filename:
        return None

    return parsed_note_id, normalized_filename


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


@router.message(Command("note"))
async def handle_note(
    message: Message,
    command: CommandObject,
    session_manager: SupabaseSessionManager,
) -> None:
    if message.chat.type != ChatType.PRIVATE:
        await message.answer("Notes are available only in a private chat.")
        return

    if message.from_user is None:
        await message.answer("Telegram did not provide your user identity.")
        return

    note_id = parse_note_id(command.args)

    if note_id is None:
        await message.answer("Usage: /note NOTE_ID")
        return

    try:
        note = await get_note(
            session_manager,
            telegram_user_id=message.from_user.id,
            note_id=note_id,
        )
    except SessionNotLinked:
        await message.answer("Link your account first using /start.")
        return
    except SessionExpired, SessionIdentityMismatch:
        await message.answer("Your account link has expired. Use /start to link again.")
        return
    except Exception:  # noqa: BLE001 - Telegram responses must not leak backend errors.
        await message.answer("I could not load that note right now. Please try again.")
        return

    if note is None:
        await message.answer("Note not found.")
        return

    await message.answer(build_note_message(note))


@router.message(Command("attachments"))
async def handle_attachments(
    message: Message,
    command: CommandObject,
    session_manager: SupabaseSessionManager,
) -> None:
    if message.chat.type != ChatType.PRIVATE:
        await message.answer("Notes are available only in a private chat.")
        return

    if message.from_user is None:
        await message.answer("Telegram did not provide your user identity.")
        return

    note_id = parse_note_id(command.args)

    if note_id is None:
        await message.answer("Usage: /attachments NOTE_ID")
        return

    try:
        attachments = await list_attachments(
            session_manager,
            telegram_user_id=message.from_user.id,
            note_id=note_id,
        )
    except SessionNotLinked:
        await message.answer("Link your account first using /start.")
        return
    except SessionExpired, SessionIdentityMismatch:
        await message.answer("Your account link has expired. Use /start to link again.")
        return
    except Exception:  # noqa: BLE001 - Telegram responses must not leak backend errors.
        await message.answer(
            "I could not load that note's attachments right now. Please try again."
        )
        return

    if attachments is None:
        await message.answer("Note not found.")
        return

    await message.answer(build_attachments_message(attachments))


@router.message(Command("download"))
async def handle_download(
    message: Message,
    command: CommandObject,
    session_manager: SupabaseSessionManager,
) -> None:
    if message.chat.type != ChatType.PRIVATE:
        await message.answer("Notes are available only in a private chat.")
        return

    if message.from_user is None:
        await message.answer("Telegram did not provide your user identity.")
        return

    request = parse_attachment_download(command.args)

    if request is None:
        await message.answer("Usage: /download NOTE_ID FILENAME")
        return

    note_id, filename = request

    try:
        attachment = await download_attachment(
            session_manager,
            telegram_user_id=message.from_user.id,
            note_id=note_id,
            filename=filename,
        )
    except SessionNotLinked:
        await message.answer("Link your account first using /start.")
        return
    except SessionExpired, SessionIdentityMismatch:
        await message.answer("Your account link has expired. Use /start to link again.")
        return
    except AttachmentTooLargeError:
        await message.answer("That attachment is too large to deliver.")
        return
    except ValueError:
        await message.answer("Usage: /download NOTE_ID FILENAME")
        return
    except Exception:  # noqa: BLE001 - Telegram responses must not leak backend errors.
        await message.answer(
            "I could not load that attachment right now. Please try again."
        )
        return

    if attachment is None:
        await message.answer("Attachment not found.")
        return

    try:
        await message.answer_document(
            document=BufferedInputFile(attachment.data, filename=attachment.name),
        )
    except Exception:  # noqa: BLE001 - Telegram responses must not leak delivery errors.
        await message.answer(
            "I could not deliver that attachment right now. Please try again."
        )


@router.message(Command("create"))
async def handle_create(
    message: Message,
    command: CommandObject,
    session_manager: SupabaseSessionManager,
) -> None:
    if message.chat.type != ChatType.PRIVATE:
        await message.answer("Notes are available only in a private chat.")
        return

    if message.from_user is None:
        await message.answer("Telegram did not provide your user identity.")
        return

    draft = parse_note_creation(command.args)

    if draft is None:
        await message.answer("Usage: /create TITLE\\nCONTENT")
        return

    title, content = draft

    try:
        note = await create_note(
            session_manager,
            telegram_user_id=message.from_user.id,
            title=title,
            content=content,
        )
    except SessionNotLinked:
        await message.answer("Link your account first using /start.")
        return
    except SessionExpired, SessionIdentityMismatch:
        await message.answer("Your account link has expired. Use /start to link again.")
        return
    except Exception:  # noqa: BLE001 - Telegram responses must not leak backend errors.
        await message.answer(
            "I could not create that note right now. Please try again."
        )
        return

    await message.answer("Note created.\n\n" + build_note_message(note))


@router.message(Command("edit"))
async def handle_edit(
    message: Message,
    command: CommandObject,
    session_manager: SupabaseSessionManager,
) -> None:
    if message.chat.type != ChatType.PRIVATE:
        await message.answer("Notes are available only in a private chat.")
        return

    if message.from_user is None:
        await message.answer("Telegram did not provide your user identity.")
        return

    draft = parse_note_edit(command.args)

    if draft is None:
        await message.answer("Usage: /edit NOTE_ID\\nTITLE\\nCONTENT")
        return

    note_id, title, content = draft

    try:
        note = await update_note(
            session_manager,
            telegram_user_id=message.from_user.id,
            note_id=note_id,
            title=title,
            content=content,
        )
    except SessionNotLinked:
        await message.answer("Link your account first using /start.")
        return
    except SessionExpired, SessionIdentityMismatch:
        await message.answer("Your account link has expired. Use /start to link again.")
        return
    except Exception:  # noqa: BLE001 - Telegram responses must not leak backend errors.
        await message.answer(
            "I could not update that note right now. Please try again."
        )
        return

    if note is None:
        await message.answer("Note not found.")
        return

    await message.answer("Note updated.\n\n" + build_note_message(note))


@router.message(Command("delete"))
async def handle_delete(
    message: Message,
    command: CommandObject,
    session_manager: SupabaseSessionManager,
) -> None:
    if message.chat.type != ChatType.PRIVATE:
        await message.answer("Notes are available only in a private chat.")
        return

    if message.from_user is None:
        await message.answer("Telegram did not provide your user identity.")
        return

    note_id = parse_note_id(command.args)

    if note_id is None:
        await message.answer("Usage: /delete NOTE_ID")
        return

    try:
        note = await delete_note(
            session_manager,
            telegram_user_id=message.from_user.id,
            note_id=note_id,
        )
    except SessionNotLinked:
        await message.answer("Link your account first using /start.")
        return
    except SessionExpired, SessionIdentityMismatch:
        await message.answer("Your account link has expired. Use /start to link again.")
        return
    except Exception:  # noqa: BLE001 - Telegram responses must not leak backend errors.
        await message.answer(
            "I could not delete that note right now. Please try again."
        )
        return

    if note is None:
        await message.answer("Note not found.")
        return

    await message.answer(f"Deleted: {note.title}")


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
