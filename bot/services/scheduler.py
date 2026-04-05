"""APScheduler: daily reminders at 21:00 MSK."""
from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from bot import database as db

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

REMINDER_TEXT = (
    "Привет! Как ты? Сегодня ты еще не делился своим днем.\n"
    "Напиши короткий чек-ин для получения обратной связи\n"
    "и продления стрика (1–3 предложения — достаточно)"
)


async def send_reminders(bot) -> None:
    """Send reminder to all users who haven't checked in today."""
    try:
        users = await db.get_users_for_reminder()
        logger.info("Sending reminders to %d users", len(users))
        for user in users:
            try:
                await bot.send_message(chat_id=user["telegram_id"], text=REMINDER_TEXT)
                await db.update_last_reminder_date(user["id"])
            except Exception:
                logger.warning(
                    "Failed to send reminder to telegram_id=%d",
                    user["telegram_id"],
                    exc_info=True,
                )
    except Exception:
        logger.exception("Reminder job failed")


async def cleanup_updates() -> None:
    """Clean up old processed_updates entries."""
    try:
        await db.cleanup_old_updates(days=7)
    except Exception:
        logger.exception("Cleanup job failed")


def setup_scheduler(bot) -> AsyncIOScheduler:
    """Configure and return scheduler with reminder job."""
    # 21:00 Europe/Moscow every day
    scheduler.add_job(
        send_reminders,
        CronTrigger(hour=21, minute=0, timezone="Europe/Moscow"),
        args=[bot],
        id="daily_reminders",
        replace_existing=True,
    )
    # Cleanup old updates daily at 04:00 MSK
    scheduler.add_job(
        cleanup_updates,
        CronTrigger(hour=4, minute=0, timezone="Europe/Moscow"),
        id="cleanup_updates",
        replace_existing=True,
    )
    return scheduler
