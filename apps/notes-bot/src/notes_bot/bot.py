import argparse
import asyncio
import logging
import sys
from collections.abc import Sequence

from aiogram import Bot, Dispatcher, Router
from aiogram.exceptions import (
    TelegramNetworkError,
    TelegramUnauthorizedError,
)
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.utils.token import TokenValidationError

from notes_bot.config import (
    ConfigurationError,
    load_settings,
)

router = Router(name=__name__)


def build_start_message(first_name: str | None) -> str:
    greeting = f"Hello, {first_name}!" if first_name else "Hello!"

    return (
        f"{greeting}\n\n"
        "I can help you manage your private notes.\n\n"
        "Your Supabase account is not linked yet. "
        "Secure account linking will be added in the next stage."
    )


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    first_name = message.from_user.first_name if message.from_user is not None else None

    await message.answer(
        build_start_message(first_name),
    )


def create_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    return dispatcher


async def run() -> None:
    settings = load_settings()
    dispatcher = create_dispatcher()

    async with Bot(
        token=settings.telegram_bot_token,
    ) as bot:
        await dispatcher.start_polling(
            bot,
            allowed_updates=dispatcher.resolve_used_update_types(),
        )


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
