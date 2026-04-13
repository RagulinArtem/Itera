"""Achievements handler: view all achievements."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot import database as db
from bot.keyboards.main_menu import back_to_menu_kb
from bot.services.achievements import (
    format_achievements_list,
    format_level_progress,
    get_user_achievements,
)

router = Router()


@router.callback_query(F.data == "menu:achievements")
async def cb_achievements(callback: CallbackQuery) -> None:
    user = await db.get_or_create_user(callback.from_user.id)
    xp = user["xp"] or 0
    unlocked = await get_user_achievements(user["id"])

    level_text = format_level_progress(xp)
    ach_text = format_achievements_list(unlocked)

    text = f"{level_text}\n\n{ach_text}"
    await callback.message.edit_text(
        text,
        reply_markup=back_to_menu_kb(),
        parse_mode="Markdown",
    )
    await callback.answer()
