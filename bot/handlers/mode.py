"""AI mode switching handler."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from bot import database as db
from bot.keyboards.main_menu import MODE_LABELS, back_to_menu_kb
from bot.services.achievements import check_mode_achievement, format_achievement_unlocked

router = Router()

MODE_DESCRIPTIONS = {
    "focus": "Разбор результатов, приоритеты, аналитика дня",
    "support": "Мягкий отклик, валидация эмоций, микро-шаг",
    "coach": "Честное зеркало, вызов, провокационные вопросы",
    "reflection": "Минимум советов, максимум вопросов для самопознания",
}


def _mode_kb(current: str) -> InlineKeyboardMarkup:
    rows = []
    for mode, label in MODE_LABELS.items():
        prefix = "✅ " if mode == current else ""
        rows.append([
            InlineKeyboardButton(
                text=f"{prefix}{label}",
                callback_data=f"mode:set:{mode}",
            )
        ])
    rows.append([InlineKeyboardButton(text="🏠 Меню", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "menu:mode")
async def cb_mode_menu(callback: CallbackQuery) -> None:
    user = await db.get_or_create_user(callback.from_user.id)
    current = user["ai_mode"] or "focus"
    current_label = MODE_LABELS.get(current, current)

    lines = [
        f"🧠 *Режим AI*\n",
        f"Текущий: {current_label}\n",
        "Режим по умолчанию для чекинов.",
        "Можно переключить прямо перед чекином.\n",
    ]
    for mode, desc in MODE_DESCRIPTIONS.items():
        icon = MODE_LABELS[mode].split()[0]
        lines.append(f"{icon} *{mode.capitalize()}* — {desc}")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=_mode_kb(current),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("mode:set:"))
async def cb_set_mode(callback: CallbackQuery) -> None:
    mode = callback.data.split(":")[-1]
    if mode not in MODE_LABELS:
        await callback.answer("Неизвестный режим", show_alert=True)
        return
    await db.update_ai_mode(callback.from_user.id, mode)
    user = await db.get_or_create_user(callback.from_user.id)
    new_achievements = await check_mode_achievement(user["id"], mode)

    await callback.message.edit_text(
        f"✅ Режим по умолчанию: {MODE_LABELS[mode]}",
        reply_markup=back_to_menu_kb(),
    )
    await callback.answer()

    for ach in new_achievements:
        await callback.message.answer(
            format_achievement_unlocked(ach),
            parse_mode="Markdown",
        )
