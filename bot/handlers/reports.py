"""Reports handler: 3/7/30 day reports."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot import database as db
from bot.keyboards.main_menu import back_to_menu_kb
from bot.keyboards.reports_kb import reports_kb
from bot.services.achievements import check_report_achievements, format_achievement_unlocked
from bot.services.report_ai import generate_report
from bot.utils.formatters import format_report_drilldown, format_report_panel

router = Router()
logger = logging.getLogger(__name__)

DAYS_MAP = {"report:3": 3, "report:7": 7, "report:30": 30}


@router.callback_query(F.data == "menu:reports")
async def cb_reports_menu(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "📊 *Отчёты*\nВыбери период:",
        reply_markup=reports_kb(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.in_(DAYS_MAP))
async def cb_report(callback: CallbackQuery) -> None:
    days = DAYS_MAP[callback.data]
    tg_id = callback.from_user.id
    user = await db.get_or_create_user(tg_id)

    await callback.message.edit_text("⏳ Генерирую отчёт...")
    await callback.answer()

    try:
        goals = await db.get_active_goals(user["id"])
        entries = await db.get_journal_entries(user["id"], limit=days)

        if not entries:
            await callback.message.edit_text(
                "📭 Нет записей за этот период. Сделай check-in!",
                reply_markup=back_to_menu_kb(),
            )
            return

        report_data = await generate_report(days, goals, entries)

        # Message 1: Panel
        panel = format_report_panel(report_data)
        await callback.message.edit_text(
            panel, reply_markup=None, parse_mode="Markdown"
        )

        # Message 2: Drilldown
        drilldown = format_report_drilldown(report_data)
        if drilldown.strip():
            await callback.message.answer(
                drilldown, reply_markup=back_to_menu_kb(), parse_mode="Markdown"
            )
        else:
            await callback.message.answer(
                "🏠 Вернуться в меню", reply_markup=back_to_menu_kb()
            )

        # Check achievements
        new_achievements = await check_report_achievements(user["id"])
        for ach in new_achievements:
            await callback.message.answer(
                format_achievement_unlocked(ach),
                parse_mode="Markdown",
            )

    except Exception:
        logger.exception("Report error for user %d", tg_id)
        await callback.message.edit_text(
            "⚠️ Сервис временно недоступен. Попробуй через минуту.",
            reply_markup=back_to_menu_kb(),
        )
