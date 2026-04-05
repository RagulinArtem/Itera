"""Settings handler: reminders on/off."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from bot import database as db
from bot.keyboards.main_menu import back_to_menu_kb

router = Router()


def _settings_kb(reminder_enabled: bool) -> InlineKeyboardMarkup:
    if reminder_enabled:
        btn = InlineKeyboardButton(text="🔕 Выключить напоминания", callback_data="settings:reminder:off")
    else:
        btn = InlineKeyboardButton(text="🔔 Включить напоминания", callback_data="settings:reminder:on")
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn],
        [InlineKeyboardButton(text="🏠 Меню", callback_data="menu:home")],
    ])


@router.callback_query(F.data == "menu:settings")
async def cb_settings(callback: CallbackQuery) -> None:
    user = await db.get_or_create_user(callback.from_user.id)
    enabled = user["reminder_enabled"]
    status = "🔔 Включены" if enabled else "🔕 Выключены"
    await callback.message.edit_text(
        f"⚙️ *Настройки*\n\nНапоминания (21:00 MSK): {status}",
        reply_markup=_settings_kb(enabled),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "settings:reminder:on")
async def cb_reminder_on(callback: CallbackQuery) -> None:
    await db.update_reminder_enabled(callback.from_user.id, True)
    await callback.message.edit_text(
        "🔔 Напоминания включены! Буду писать в 21:00 MSK если не было check-in'а.",
        reply_markup=back_to_menu_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "settings:reminder:off")
async def cb_reminder_off(callback: CallbackQuery) -> None:
    await db.update_reminder_enabled(callback.from_user.id, False)
    await callback.message.edit_text(
        "🔕 Напоминания выключены.",
        reply_markup=back_to_menu_kb(),
    )
    await callback.answer()
