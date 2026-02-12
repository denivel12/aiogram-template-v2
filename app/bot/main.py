from __future__ import annotations

import asyncio
import logging
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING

import msgspec
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import PRODUCTION, TEST
from aiogram.fsm.storage.base import DefaultKeyBuilder
from aiogram.fsm.storage.memory import SimpleEventIsolation
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.webhook.aiohttp_server import (
    SimpleRequestHandler,
    ip_filter_middleware,
    setup_application,
)
from aiogram.webhook.security import DEFAULT_TELEGRAM_NETWORKS, IPFilter
from aiogram_i18n import I18nMiddleware
from aiogram_i18n.cores import FluentRuntimeCore
from aiohttp import web
from redis.asyncio import Redis

from errors import get_errors_router
from handlers import get_handlers_router
from middlewares.check_chat_middleware import CheckChatMiddleware
from middlewares.check_user_middleware import CheckUserMiddleware
from middlewares.database_middleware import DatabaseMiddleware
from middlewares.throttling_middleware import ThrottlingMiddleware
from settings import Settings
from storages.psql.base import create_db_pool
from utils.fsm_manager import FSMManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def on_startup(dispatcher: Dispatcher, bot: Bot, settings: Settings) -> None:
    if settings.webhooks:
        await bot.set_webhook(
            url=settings.webhook_url.get_secret_value(),
            allowed_updates=dispatcher.resolve_used_update_types(),
            secret_token=settings.webhook_secret_token.get_secret_value(),
            drop_pending_updates=True,
        )
    else:
        await bot.delete_webhook(drop_pending_updates=True)

    logger.info("Bot started")


async def on_shutdown(dispatcher: Dispatcher, bot: Bot) -> None:
    logger.info("Stopping bot...")
    await bot.session.close()
    await dispatcher.storage.close()
    logger.info("Bot stopped")


async def main() -> None:
    settings = Settings()

    api = TEST if settings.test_server is True else PRODUCTION

    bot = Bot(
        token=settings.bot_token.get_secret_value(),
        session=AiohttpSession(api=api),
        default=DefaultBotProperties(parse_mode="HTML"),
    )

    redis = Redis.from_url(settings.redis_dsn())
    storage = RedisStorage(
        redis=redis,
        key_builder=DefaultKeyBuilder(with_bot_id=True, with_destiny=True),
        json_loads=msgspec.json.decode,
        json_dumps=partial(lambda obj: str(msgspec.json.encode(obj), encoding="utf-8")),
    )

    engine, session_pool = await create_db_pool(settings)

    dp = Dispatcher(
        storage=storage,
        events_isolation=SimpleEventIsolation(),
        settings=settings,
    )

    # Register routers
    dp.include_router(get_handlers_router())
    dp.include_router(get_errors_router())

    # Register middlewares
    dp.update.outer_middleware(DatabaseMiddleware(session_pool=session_pool))
    dp.update.outer_middleware(CheckChatMiddleware())
    dp.update.outer_middleware(CheckUserMiddleware())

    dp.message.middleware(ThrottlingMiddleware(redis))
    dp.callback_query.middleware(ThrottlingMiddleware(redis))

    i18n_middleware = I18nMiddleware(
        core=FluentRuntimeCore(path=Path(__file__).parent / "locales" / "{locale}"),
        manager=FSMManager(),
    )
    i18n_middleware.setup(dispatcher=dispatcher)
    await i18n_middleware.core.startup()

    # Register startup/shutdown hooks
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    if settings.webhooks:
        app = web.Application(
            middlewares=[ip_filter_middleware(IPFilter(DEFAULT_TELEGRAM_NETWORKS))],
        )

        SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
            secret_token=settings.webhook_secret_token.get_secret_value(),
        ).register(app, "/webhook")
        setup_application(app, dp, bot=bot)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host="0.0.0.0", port=8080)
        await site.start()
        await asyncio.Event().wait()

    else:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.error("Bot stopped!")
