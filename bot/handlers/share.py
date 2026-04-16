"""Share progress card handler."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from bot import database as db
from bot.keyboards.main_menu import back_to_menu_kb
from bot.services.achievements import ACHIEVEMENT_DEFS, get_level, get_user_achievements
from bot.services.share_card import CardData, generate_card

router = Router()


@router.callback_query(F.data == "menu:share")
async def cb_share(callback: CallbackQuery) -> None:
    user = await db.get_or_create_user(callback.from_user.id)
    xp = user["xp"] or 0
    streak = user["streak"] or 0
    level = get_level(xp)

    unlocked = await get_user_achievements(user["id"])

    # Count completed goals
    completed_goals = await db._get_pool().fetchval(
        'SELECT COUNT(*) FROM "Goals" WHERE user_id = $1 AND status = \'completed\'',
        user["id"],
    )

    # Count total checkins
    total_checkins = await db._get_pool().fetchval(
        "SELECT COUNT(*) FROM journal_entries WHERE user_id = $1",
        user["id"],
    )

    data = CardData(
        nickname=user["nickname"] or callback.from_user.first_name or "",
        level_name=level.name,
        level_icon=level.icon,
        xp=xp,
        streak=streak,
        achievements_unlocked=len(unlocked & set(ACHIEVEMENT_DEFS.keys())),
        achievements_total=len(ACHIEVEMENT_DEFS),
        goals_completed=completed_goals or 0,
        checkins_total=total_checkins or 0,
    )

    img_bytes = generate_card(data)
    photo = BufferedInputFile(img_bytes, filename="itera-progress.png")

    await callback.message.delete()
    await callback.message.answer_photo(
        photo=photo,
        caption="📊 Мой прогресс в Itera\n\nПрисоединяйся: @Itera_diary_bot",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Меню", callback_data="menu:home")],
        ]),
    )
    await callback.answer()
