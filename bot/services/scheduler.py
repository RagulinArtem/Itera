"""APScheduler: daily reminders, weekly digest."""
from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from bot import database as db
from bot.services.achievements import format_level_progress, get_level, get_user_achievements

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


async def send_weekly_digest(bot) -> None:
    """Send weekly digest to all active users on Sunday."""
    try:
        users = await db._get_pool().fetch(
            """
            SELECT p.id, p.telegram_id, p.nickname, p.xp, p.streak,
                   (SELECT COUNT(*) FROM journal_entries je
                    WHERE je.user_id = p.id
                      AND je.entry_date >= CURRENT_DATE - INTERVAL '7 days') as week_checkins,
                   (SELECT COUNT(*) FROM "Goals" g
                    WHERE g.user_id = p.id AND g.status = 'completed'
                      AND g.completed_at >= now() - INTERVAL '7 days') as week_goals_done
            FROM "Profiles" p
            WHERE p.telegram_id IS NOT NULL
              AND p.reminder_enabled = true
            """
        )
        logger.info("Sending weekly digest to %d users", len(users))
        for user in users:
            try:
                xp = user["xp"] or 0
                streak = user["streak"] or 0
                week_checkins = user["week_checkins"] or 0
                week_goals = user["week_goals_done"] or 0
                name = user["nickname"] or "друг"

                if week_checkins == 0:
                    text = (
                        f"📊 *Итоги недели*\n\n"
                        f"Привет, {name}! На этой неделе чекинов не было.\n"
                        f"Новая неделя — новый старт! 💪\n\n"
                        f"🔥 Streak: {streak} дн. | 🏅 XP: {xp}"
                    )
                else:
                    level = get_level(xp)
                    achievements = await get_user_achievements(user["id"])
                    text = (
                        f"📊 *Итоги недели*\n\n"
                        f"Привет, {name}! Вот твоя статистика:\n\n"
                        f"✅ Чекинов: {week_checkins}/7\n"
                        f"🎯 Целей завершено: {week_goals}\n"
                        f"🔥 Streak: {streak} дн.\n"
                        f"🏅 XP: {xp} ({level.icon} {level.name})\n"
                        f"🏅 Ачивок: {len(achievements)}\n\n"
                    )
                    if week_checkins >= 7:
                        text += "Идеальная неделя! Ты невероятен! 🌟"
                    elif week_checkins >= 5:
                        text += "Отличная неделя! Так держать! 💪"
                    elif week_checkins >= 3:
                        text += "Хороший старт! Попробуй на следующей неделе больше 🚀"
                    else:
                        text += "Каждый шаг считается! Продолжай 🌱"

                await bot.send_message(
                    chat_id=user["telegram_id"],
                    text=text,
                    parse_mode="Markdown",
                )
            except Exception:
                logger.warning(
                    "Failed to send digest to telegram_id=%d",
                    user["telegram_id"],
                    exc_info=True,
                )
    except Exception:
        logger.exception("Weekly digest job failed")


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
    # Weekly digest on Sundays at 20:00 MSK
    scheduler.add_job(
        send_weekly_digest,
        CronTrigger(day_of_week="sun", hour=20, minute=0, timezone="Europe/Moscow"),
        args=[bot],
        id="weekly_digest",
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
