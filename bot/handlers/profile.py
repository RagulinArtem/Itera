"""Profile handler: view, set nickname, set email."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot import database as db
from bot.fsm.states import IteraStates
from bot.keyboards.main_menu import back_to_menu_kb, cancel_kb

router = Router()


def _profile_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Имя", callback_data="auth:set_name"),
            InlineKeyboardButton(text="📧 Email", callback_data="auth:set_email"),
        ],
        [InlineKeyboardButton(text="🏠 Меню", callback_data="menu:home")],
    ])


@router.callback_query(F.data == "menu:profile")
async def cb_profile(callback: CallbackQuery) -> None:
    user = await db.get_or_create_user(callback.from_user.id)
    nickname = user["nickname"] or "—"
    email = user["email"] or "—"
    xp = user["xp"] or 0
    streak = user["streak"] or 0
    created = user["created_at"].strftime("%d.%m.%Y") if user["created_at"] else "—"

    text = (
        f"👤 *Профиль*\n\n"
        f"Имя: {nickname}\n"
        f"Email: {email}\n"
        f"XP: {xp}\n"
        f"Streak: {streak} дн.\n"
        f"Зарегистрирован: {created}"
    )
    await callback.message.edit_text(text, reply_markup=_profile_kb(), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "auth:set_name")
async def cb_set_name(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(IteraStates.awaiting_nickname)
    await callback.message.edit_text("✏️ Введи своё имя/никнейм:", reply_markup=cancel_kb())
    await callback.answer()


@router.message(IteraStates.awaiting_nickname)
async def process_nickname(message: Message, state: FSMContext) -> None:
    nickname = (message.text or "").strip()
    if not nickname:
        await message.answer("Отправь текстовое имя.", reply_markup=cancel_kb())
        return
    await db.update_nickname(message.from_user.id, nickname)
    await state.clear()
    await db.update_user_state(message.from_user.id, None)
    await message.answer(
        f"✅ Имя обновлено: {nickname}",
        reply_markup=back_to_menu_kb(),
    )


@router.callback_query(F.data == "auth:set_email")
async def cb_set_email(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(IteraStates.awaiting_email)
    await callback.message.edit_text("📧 Введи email:", reply_markup=cancel_kb())
    await callback.answer()


@router.message(IteraStates.awaiting_email)
async def process_email(message: Message, state: FSMContext) -> None:
    email = (message.text or "").strip()
    if not email or "@" not in email:
        await message.answer("Введи корректный email.", reply_markup=cancel_kb())
        return
    await db.update_email(message.from_user.id, email)
    await state.clear()
    await db.update_user_state(message.from_user.id, None)
    await message.answer(
        f"✅ Email обновлён: {email}",
        reply_markup=back_to_menu_kb(),
    )
