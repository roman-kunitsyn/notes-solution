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
from aiogram.filters import CommandStart
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

router = Router(name=__name__)


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
    dispatcher = create_dispatcher()

    http_server = HttpServer(
        application=create_http_app(
            database_path=settings.database_path,
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
