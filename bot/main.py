"""Entry point: webhook server (production) or polling (development)."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import settings
from bot import database as db
from bot.fsm.db_storage import PostgresStateStorage
from bot.utils.idempotency import IdempotencyMiddleware

# Handlers
from bot.handlers import start, checkin, goals, reports, profile, mode, achievements, share, ask, export
from bot.handlers import settings as settings_handler
from bot.handlers import feedback

# Scheduler
from bot.services.scheduler import setup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _create_bot() -> Bot:
    return Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )


def _create_dispatcher() -> Dispatcher:
    storage = PostgresStateStorage()
    dp = Dispatcher(storage=storage)

    # Register idempotency middleware
    dp.update.outer_middleware(IdempotencyMiddleware())

    # Register routers
    dp.include_router(start.router)
    dp.include_router(checkin.router)
    dp.include_router(goals.router)
    dp.include_router(reports.router)
    dp.include_router(profile.router)
    dp.include_router(mode.router)
    dp.include_router(achievements.router)
    dp.include_router(share.router)
    dp.include_router(ask.router)
    dp.include_router(export.router)
    dp.include_router(settings_handler.router)
    dp.include_router(feedback.router)

    return dp


async def _run_webhook() -> None:
    """Production: webhook via aiohttp."""
    from aiohttp import web
    from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

    bot = _create_bot()
    dp = _create_dispatcher()

    await db.create_pool()
    sched = setup_scheduler(bot)

    app = web.Application()

    # Mini App API + static files
    from bot.api.routes import setup_api_routes
    setup_api_routes(app)

    import pathlib
    webapp_dist = pathlib.Path(__file__).resolve().parent.parent / "webapp" / "dist"
    if webapp_dist.exists():
        app.router.add_static("/app/", webapp_dist, show_index=True)

    webhook_path = settings.webhook_path
    handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    handler.register(app, path=webhook_path)
    setup_application(app, dp, bot=bot)

    async def on_startup(_app: web.Application) -> None:
        await bot.set_webhook(
            settings.webhook_url,
            drop_pending_updates=True,
        )
        sched.start()
        logger.info("Webhook set: %s", settings.webhook_url)

    async def on_shutdown(_app: web.Application) -> None:
        sched.shutdown(wait=False)
        await bot.delete_webhook()
        await db.close_pool()
        await bot.session.close()
        logger.info("Shutdown complete")

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=settings.port)
    await site.start()
    logger.info("Server started on port %d", settings.port)

    # Keep running
    try:
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()


async def _run_polling() -> None:
    """Development: long polling + aiohttp for Mini App API."""
    from aiohttp import web
    import pathlib

    bot = _create_bot()
    dp = _create_dispatcher()

    await db.create_pool()
    sched = setup_scheduler(bot)
    sched.start()

    # Start API server for Mini App
    app = web.Application()
    from bot.api.routes import setup_api_routes
    setup_api_routes(app)

    webapp_dist = pathlib.Path(__file__).resolve().parent.parent / "webapp" / "dist"
    if webapp_dist.exists():
        app.router.add_static("/app/", webapp_dist, show_index=True)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=settings.port)
    await site.start()
    logger.info("Mini App server started on port %d", settings.port)

    logger.info("Starting polling mode (development)...")
    try:
        await dp.start_polling(bot, drop_pending_updates=True)
    finally:
        sched.shutdown(wait=False)
        await runner.cleanup()
        await db.close_pool()
        await bot.session.close()


def main() -> None:
    if settings.is_production:
        logger.info("Mode: PRODUCTION (webhook)")
        asyncio.run(_run_webhook())
    else:
        logger.info("Mode: DEVELOPMENT (polling)")
        asyncio.run(_run_polling())


if __name__ == "__main__":
    main()
