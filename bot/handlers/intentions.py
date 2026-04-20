"""Morning intentions handler: plan 3 things for the day."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot import database as db
from bot.fsm.states import IteraStates
from bot.keyboards.main_menu import back_to_menu_kb, cancel_kb

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "menu:intentions")
async def cb_start_intentions(callback: CallbackQuery, state: FSMContext) -> None:
    tg_id = callback.from_user.id
    user = await db.get_or_create_user(tg_id)

    # Check if already set today
    existing = await db.get_today_intentions(user["id"])
    if existing:
        items_text = "\n".join(f"  {i+1}. {item}" for i, item in enumerate(existing))
        await callback.message.edit_text(
            f"🌅 Твои намерения на сегодня:\n\n{items_text}\n\n"
            "Намерения уже записаны! Вернись вечером для check-in.",
            reply_markup=back_to_menu_kb(),
        )
        await callback.answer()
        return

    await state.set_state(IteraStates.awaiting_intentions)
    await callback.message.edit_text(
        "🌅 *Утренние намерения*\n\n"
        "Напиши 1–3 вещи, которые хочешь сделать сегодня.\n"
        "Каждое намерение с новой строки.\n\n"
        "_Пример:_\n"
        "Закончить отчёт\n"
        "30 минут спорта\n"
        "Позвонить партнёру",
        reply_markup=cancel_kb(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.message(IteraStates.awaiting_intentions)
async def process_intentions(message: Message, state: FSMContext) -> None:
    tg_id = message.from_user.id
    text = message.text
    if not text:
        await message.answer("Отправь текстовое сообщение.", reply_markup=cancel_kb())
        return

    user = await db.get_or_create_user(tg_id)

    # Parse lines — take up to 3 non-empty
    items = [line.strip().lstrip("0123456789.-) ") for line in text.strip().split("\n") if line.strip()]
    items = [i for i in items if i][:3]

    if not items:
        await message.answer(
            "Не удалось распознать намерения. Напиши каждое с новой строки.",
            reply_markup=cancel_kb(),
        )
        return

    await db.save_intentions(user["id"], items)

    await state.clear()
    await db.update_user_state(tg_id, None)

    items_text = "\n".join(f"  {i+1}. {item}" for i, item in enumerate(items))
    await message.answer(
        f"🌅 *Намерения на сегодня записаны!*\n\n{items_text}\n\n"
        "Вечером при check-in ИИ сравнит план с результатом.",
        reply_markup=back_to_menu_kb(),
        parse_mode="Markdown",
    )
