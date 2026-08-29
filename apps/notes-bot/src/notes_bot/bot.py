import asyncio

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from notes_bot.config import load_settings

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


def main() -> None:
    asyncio.run(run())
