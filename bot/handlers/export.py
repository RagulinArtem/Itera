"""Export handler — generate PDF report for a period."""
from __future__ import annotations

import logging
from datetime import date, timedelta

from aiogram import F, Router
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from bot import database as db
from bot.keyboards.main_menu import back_to_menu_kb
from bot.services.achievements import ACHIEVEMENT_DEFS, get_level, get_user_achievements
from bot.services.export_pdf import ExportData, generate_pdf

router = Router()
logger = logging.getLogger(__name__)

PERIODS = {
    "week": ("Неделя", 7),
    "month": ("Месяц", 30),
    "quarter": ("Квартал", 90),
    "all": ("Всё время", 3650),
}


def _export_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 Неделя", callback_data="export:week"),
            InlineKeyboardButton(text="📅 Месяц", callback_data="export:month"),
        ],
        [
            InlineKeyboardButton(text="📅 Квартал", callback_data="export:quarter"),
            InlineKeyboardButton(text="📅 Всё время", callback_data="export:all"),
        ],
        [InlineKeyboardButton(text="🏠 Меню", callback_data="menu:home")],
    ])


@router.callback_query(F.data == "menu:export")
async def cb_export_menu(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "📄 *Экспорт в PDF*\n\nВыбери период для отчёта:",
        reply_markup=_export_kb(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("export:"))
async def cb_export_generate(callback: CallbackQuery) -> None:
    period_key = callback.data.split(":")[-1]
    if period_key not in PERIODS:
        await callback.answer("Неизвестный период", show_alert=True)
        return

    period_label, days = PERIODS[period_key]
    tg_id = callback.from_user.id
    user = await db.get_or_create_user(tg_id)

    wait_msg = await callback.message.edit_text("⏳ Генерирую PDF...")
    await callback.answer()

    try:
        date_from = date.today() - timedelta(days=days)
        date_to = date.today()

        # Fetch data
        entries = await db.get_journal_entries(user["id"], limit=500)
        # Filter by date
        checkins = [
            e for e in entries
            if e.get("entry_date") and e["entry_date"] >= date_from
        ]

        goals = await db.get_all_goals(user["id"])
        xp = user["xp"] or 0
        level = get_level(xp)
        unlocked = await get_user_achievements(user["id"])

        data = ExportData(
            nickname=user["nickname"] or callback.from_user.first_name or "",
            period_label=period_label,
            date_from=date_from,
            date_to=date_to,
            xp=xp,
            streak=user["streak"] or 0,
            level_name=level.name,
            checkins=checkins,
            goals=goals,
            achievements_unlocked=len(unlocked & set(ACHIEVEMENT_DEFS.keys())),
            achievements_total=len(ACHIEVEMENT_DEFS),
        )

        pdf_bytes = generate_pdf(data)
        doc = BufferedInputFile(pdf_bytes, filename=f"itera-{period_key}-{date_to}.pdf")

        await wait_msg.delete()
        await callback.message.answer_document(
            document=doc,
            caption=f"📄 Отчёт Itera: {period_label} ({date_from} — {date_to})",
            reply_markup=back_to_menu_kb(),
        )

    except Exception:
        logger.exception("PDF export error for user %d", tg_id)
        await wait_msg.delete()
        await callback.message.answer(
            "⚠️ Не удалось создать PDF. Попробуй позже.",
            reply_markup=back_to_menu_kb(),
        )
